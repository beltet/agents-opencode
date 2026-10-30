@echo off
setlocal DisableDelayedExpansion
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if not errorlevel 1 goto run_py
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if not errorlevel 1 goto run_python
echo Python 3.10+ is required / Python 3.10+ kravs. 1>&2
exit /b 1
:run_py
py -3 "%~dp0install.py" %*
exit /b %errorlevel%
:run_python
python "%~dp0install.py" %*
exit /b %errorlevel%
