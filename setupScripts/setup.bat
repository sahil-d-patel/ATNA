@echo off
REM ATNA one-command setup (Windows): environment, dependencies, and optionally data.
REM
REM   setupScripts\setup.bat              interactive: installs everything, offers demo data
REM   setupScripts\setup.bat --demo       non-interactive: bootstrap synthetic demo snapshot
REM   setupScripts\setup.bat --data       full BTS download (Playwright) + real pipeline
REM   setupScripts\setup.bat --skip-data  environment only, no data bootstrap
REM   setupScripts\setup.bat -y           assume "yes" at prompts
setlocal enabledelayedexpansion

pushd "%~dp0.."
set "PY=.venv\Scripts\python.exe"

set DEMO=0
set DATA=0
set SKIP_DATA=0
set ASSUME_YES=0

REM Scan every argument, not just the first.
:parse_args
if "%~1"=="" goto args_done
if /i "%~1"=="--demo"      set DEMO=1& goto next_arg
if /i "%~1"=="--data"      set DATA=1& goto next_arg
if /i "%~1"=="--skip-data" set SKIP_DATA=1& goto next_arg
if /i "%~1"=="-y"          set ASSUME_YES=1& goto next_arg
if /i "%~1"=="--yes"       set ASSUME_YES=1& goto next_arg
if /i "%~1"=="-h"          goto show_help
if /i "%~1"=="--help"      goto show_help
echo error: unknown option: %~1 ^(see --help^)
goto fail
:next_arg
shift
goto parse_args
:args_done

if "%DEMO%%DATA%"=="11" (
    echo error: --demo and --data are mutually exclusive
    goto fail
)

echo ==^> Checking Python
where python >nul 2>nul
if errorlevel 1 (
    echo error: python not found - install Python 3.10+ from https://www.python.org/
    goto fail
)
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
    echo error: Python 3.10+ is required
    goto fail
)

if not exist "%PY%" (
    echo ==^> Creating virtual environment ^(.venv^)
    python -m venv .venv || goto fail
) else (
    echo ==^> Reusing existing virtual environment ^(.venv^)
)

echo ==^> Installing dependencies ^(requirements.txt^)
"%PY%" -m pip install --quiet --upgrade pip || goto fail
"%PY%" -m pip install --quiet -r requirements.txt || goto fail

for /f "delims=" %%s in ('"%PY%" -c "import yaml; print(yaml.safe_load(open('config/atna.yaml'))['snapshot_id'])"') do set "SNAPSHOT_ID=%%s"

if "%SKIP_DATA%"=="1" (
    echo ==^> Skipping data bootstrap ^(--skip-data^)
    goto sanity_check
)
if exist "data\processed\%SNAPSHOT_ID%\metrics.csv" (
    echo ==^> Artifacts already present for snapshot %SNAPSHOT_ID% - skipping data bootstrap
    goto sanity_check
)

if "%DATA%"=="1" (
    echo ==^> Installing Playwright Chromium for the BTS downloader
    "%PY%" -m playwright install chromium || goto fail
    echo ==^> Downloading BTS data ^(this can take a while; TranStats may throttle^)
    "%PY%" scripts\download\download_bts_data.py || goto fail
    for /f "tokens=1 delims=-" %%y in ("%SNAPSHOT_ID%") do "%PY%" scripts\download\verify_downloads.py --year %%y || goto fail
    goto run_pipeline
)

if "%DEMO%"=="0" if "%ASSUME_YES%"=="0" (
    echo.
    echo No processed artifacts found for snapshot %SNAPSHOT_ID%.
    set /p ANSWER="Generate a synthetic demo dataset so the app runs immediately? [Y/n] "
    if /i "!ANSWER!"=="n" goto no_data
)

echo ==^> Generating synthetic demo dataset ^(snapshot %SNAPSHOT_ID%^)
set PYTHONPATH=src
"%PY%" scripts\demo\generate_demo_data.py || goto fail

:run_pipeline
set PYTHONPATH=src
echo ==^> Running ETL pipeline
"%PY%" -m etl.run_pipeline || goto fail
echo ==^> Computing graph metrics and communities
"%PY%" -m metrics.run_metrics || goto fail
echo ==^> Running demo scenarios
"%PY%" -m scenarios.run_scenarios || goto fail
goto sanity_check

:no_data
echo warning: environment ready, but the app has no data. Re-run with --demo or --data later.

:sanity_check
echo ==^> Running self-contained test suite
set PYTHONPATH=src
"%PY%" -m pytest tests -q --no-header -x -k "not streamlit" >nul 2>nul
if errorlevel 1 (
    echo     warning: some tests did not pass - run "%PY%" -m pytest tests -q for details
) else (
    echo     tests passed
)

echo.
echo ==^> Setup complete
echo     Start the app:   setupScripts\start.bat
echo     Rebuild data:    setupScripts\pipeline.bat
echo     Run all tests:   set PYTHONPATH=src ^&^& .venv\Scripts\python.exe -m pytest tests -q
popd & endlocal & exit /b 0

:show_help
echo ATNA setup ^(Windows^)
echo   setup.bat              interactive: installs everything, offers demo data
echo   setup.bat --demo       non-interactive: bootstrap synthetic demo snapshot
echo   setup.bat --data       full BTS download ^(Playwright^) + real pipeline
echo   setup.bat --skip-data  environment only, no data bootstrap
echo   setup.bat -y           assume "yes" at prompts
popd & endlocal & exit /b 0

:fail
popd & endlocal & exit /b 1
