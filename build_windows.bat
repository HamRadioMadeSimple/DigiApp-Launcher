@echo off
setlocal
cd /d "%~dp0"
title Building DigiApp Launcher
rem On GitHub (CI is set) never wait for a key or open Explorer
if defined CI (set "PAUSE=ver>nul") else (set "PAUSE=pause")

rem ---------------------------------------------------------------- Python
set PY=
python --version >nul 2>nul && set PY=python
if not defined PY py -3 --version >nul 2>nul && set PY=py -3
if not defined PY (
    echo  Python 3 is needed on THIS PC to build. Users of the program do NOT need it.
    echo  Get it from https://www.python.org/downloads/  - tick "Add python.exe to PATH".
    %PAUSE%
    exit /b 1
)
for /f "usebackq delims=" %%v in (`%PY% -c "import digiapp; print(digiapp.__version__)"`) do set VER=%%v
echo.
echo  === Building DigiApp Launcher %VER% for Windows ===
echo.

rem ---------------------------------------------------------------- tools + tests
echo  Getting build tools...
%PY% -m pip install --upgrade --quiet -r requirements.txt pyinstaller
if errorlevel 1 goto fail
echo  Running tests...
%PY% -m unittest discover -s tests -q
if errorlevel 1 goto fail

rem ---------------------------------------------------------------- the program
echo  Building DigiAppLauncher.exe - takes a minute...
if exist build\pyinstaller rmdir /s /q build\pyinstaller
if exist dist rmdir /s /q dist
%PY% -m PyInstaller --noconfirm --clean --log-level WARN --workpath build\pyinstaller --distpath dist DigiAppLauncher.spec
if errorlevel 1 goto fail

rem ---------------------------------------------------------------- portable zip
if not exist output mkdir output
set PORT=output\DigiApp-Launcher-%VER%-Windows-Portable
if exist "%PORT%" rmdir /s /q "%PORT%"
if exist "%PORT%.zip" del /q "%PORT%.zip"
if exist "%PORT%.zip.part" del /q "%PORT%.zip.part"
mkdir "%PORT%"
copy /y dist\DigiAppLauncher.exe "%PORT%\" >nul
copy /y dev\README-Windows.txt "%PORT%\README.txt" >nul
if exist docs\DigiApp-Launcher-Guide.pdf copy /y docs\DigiApp-Launcher-Guide.pdf "%PORT%\" >nul
%PY% tools\make_portable_zip.py "%PORT%"
if errorlevel 1 goto fail
rem the folder was only the zip's working copy - remove it so output\ holds just the two downloads
rmdir /s /q "%PORT%"

rem ---------------------------------------------------------------- installer (needs Inno Setup 6)
set ISCC=
where iscc >nul 2>nul && set ISCC=iscc
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if defined ISCC (
    echo  Building the installer...
    "%ISCC%" /Q /DMyAppVersion=%VER% DigiAppLauncher.iss
    if errorlevel 1 goto fail
) else (
    echo  Inno Setup 6 not found, so no Setup.exe this time - the portable zip is ready.
    echo  To also get an installer: install Inno Setup 6 from https://jrsoftware.org/isdl.php and run this again.
)

echo.
echo  Done!  In the output folder:
if exist "output\DigiAppLauncher-%VER%-Setup.exe" echo    DigiAppLauncher-%VER%-Setup.exe           - installer: send this to users
if exist "%PORT%.zip" echo    DigiApp-Launcher-%VER%-Windows-Portable.zip - no-install version
echo.
if not defined CI explorer output
%PAUSE%
exit /b 0

:fail
echo.
echo  Build failed - see the messages above.
%PAUSE%
exit /b 1
