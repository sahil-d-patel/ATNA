@echo off
REM Launch the ATNA Streamlit app (Windows). Run setupScripts\setup.bat first.
setlocal
pushd "%~dp0.."

set "PY=.venv\Scripts\python.exe"

if not exist "%PY%" (
    echo error: .venv not found - run setupScripts\setup.bat first
    popd & endlocal & exit /b 1
)

for /f "delims=" %%s in ('"%PY%" -c "import yaml; print(yaml.safe_load(open('config/atna.yaml'))['snapshot_id'])"') do set "SNAPSHOT_ID=%%s"

if not exist "data\processed\%SNAPSHOT_ID%\metrics.csv" (
    echo error: no artifacts for snapshot %SNAPSHOT_ID% - run setupScripts\setup.bat --demo ^(or --data^) first
    popd & endlocal & exit /b 1
)

set PYTHONPATH=src
".venv\Scripts\streamlit.exe" run src\app\streamlit_app.py
popd
endlocal
