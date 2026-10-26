@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto try_python
call py -3.13 -c "import sys" >nul 2>nul
if errorlevel 1 goto try312
call py -3.13 scripts\bootstrap.py %*
set "setup_result=%errorlevel%"
goto finished
:try312
call py -3.12 -c "import sys" >nul 2>nul
if errorlevel 1 goto try314
call py -3.12 scripts\bootstrap.py %*
set "setup_result=%errorlevel%"
goto finished
:try314
call py -3.14 -c "import sys" >nul 2>nul
if errorlevel 1 goto try311
call py -3.14 scripts\bootstrap.py %*
set "setup_result=%errorlevel%"
goto finished
:try311
call py -3.11 -c "import sys" >nul 2>nul
if errorlevel 1 goto try_python
call py -3.11 scripts\bootstrap.py %*
set "setup_result=%errorlevel%"
goto finished
:try_python
call python -c "import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] < (3,15) else 1)" >nul 2>nul
if errorlevel 1 goto missing
call python scripts\bootstrap.py %*
set "setup_result=%errorlevel%"
goto finished
:missing
echo A supported Python runtime was not found.
echo If you have Python Install Manager, run: py install 3.13
echo Otherwise install Python 3.13 from https://www.python.org/downloads/
echo Then rerun SETUP_WINDOWS.bat. No application data was deleted.
if not defined FRAMEWORK_NONINTERACTIVE pause
exit /b 1
:finished
if not "%setup_result%"=="0" echo Setup stopped. Read the error above. Keep your settings and database.
if not defined FRAMEWORK_NONINTERACTIVE pause
exit /b %setup_result%
