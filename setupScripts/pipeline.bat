@echo off
REM Rebuild all processed artifacts (Windows): ETL -> metrics -> scenarios.
pushd "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
    echo error: .venv not found - run setupScripts\setup.bat first
    popd & exit /b 1
)

set PYTHONPATH=src
".venv\Scripts\python.exe" -m etl.run_pipeline %* || (popd & exit /b 1)
".venv\Scripts\python.exe" -m metrics.run_metrics || (popd & exit /b 1)
".venv\Scripts\python.exe" -m scenarios.run_scenarios || (popd & exit /b 1)
popd
