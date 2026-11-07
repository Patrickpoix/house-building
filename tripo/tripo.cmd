@echo off
call "%~dp0node_modules\.bin\tripo.cmd" %*
exit /b %ERRORLEVEL%
