@echo off
setlocal
set "PROJECT_DIR=%~dp0"
set "PY_LOCAL=%PROJECT_DIR%.venv\Scripts\python.exe"
set "PY_PARENT=%PROJECT_DIR%..\.venv\Scripts\python.exe"

if exist "%PY_LOCAL%" (
	set "PYTHON_EXE=%PY_LOCAL%"
) else if exist "%PY_PARENT%" (
	set "PYTHON_EXE=%PY_PARENT%"
) else (
	echo Could not find a virtual environment Python executable.
	echo Expected one of:
	echo   %PY_LOCAL%
	echo   %PY_PARENT%
	exit /b 1
)

"%PYTHON_EXE%" "%PROJECT_DIR%app.py"
