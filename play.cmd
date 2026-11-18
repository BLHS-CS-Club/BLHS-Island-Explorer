@echo off
rem plays your island the same way python play.py does, so in the terminal you type .\play
rem it uses the python that came in the download when there's a python folder next to it,
rem and the computer's own python when there isn't
setlocal
rem play.py reads this to know which command to tell you to type
set BLHS_PLAY_CMD=1
set py=python
if exist "%~dp0python\python.exe" set py="%~dp0python\python.exe"
%py% "%~dp0play.py" %*
