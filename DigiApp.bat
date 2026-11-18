@echo off
rem Run DigiApp Launcher straight from this source folder (needs Python 3 on this PC).
rem   DigiApp.bat           editor
rem   DigiApp.bat --run     launch the default profile
cd /d "%~dp0"
where pythonw >nul 2>nul && (start "" pythonw run_digiapp.py %*) || (python run_digiapp.py %*)
