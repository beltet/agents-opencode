@echo off
setlocal DisableDelayedExpansion
set "ENGINE=%~dp0lib\manager.py"
if exist "%ENGINE%" goto engine_found
if not defined LOCALAPPDATA set "LOCALAPPDATA=%USERPROFILE%\AppData\Local"
set "ENGINE=%LOCALAPPDATA%\agents-opencode\lib\manager.py"
if exist "%ENGINE%" goto engine_found
echo Missing manager.py; reinstall agents-opencode / Installera om agents-opencode. 1>&2
exit /b 1
:engine_found
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if not errorlevel 1 goto run_py
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if not errorlevel 1 goto run_python
echo Python 3.10+ is required / Python 3.10+ kravs. 1>&2
exit /b 1
:run_py
py -3 "%ENGINE%" %*
exit /b %errorlevel%
:run_python
python "%ENGINE%" %*
exit /b %errorlevel%
