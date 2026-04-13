@echo off
title FluxKey - Build Windows EXE + Installer
color 05
cd /d "%~dp0"
cls

echo.
echo  =====================================================
echo    FluxKey  ^|  Build Windows EXE + Installer
echo  =====================================================
echo.

REM ── Find Python — try every known method ──────────────
set PYTHON=

REM 1. Windows py launcher
where py >nul 2>&1
if not errorlevel 1 (
    set PYTHON=py
    goto :found_python
)

REM 2. python3
where python3 >nul 2>&1
if not errorlevel 1 (
    set PYTHON=python3
    goto :found_python
)

REM 3. python on PATH (skip Store stub)
where python >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=*" %%x in ('where python 2^>nul') do (
        echo %%x | findstr /i "WindowsApps" >nul
        if errorlevel 1 (
            set PYTHON=%%x
            goto :found_python
        )
    )
)

REM 4. Common install folders
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python39\python.exe"
    "C:\Python313\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
    "C:\Python310\python.exe"
    "C:\Python39\python.exe"
    "%PROGRAMFILES%\Python313\python.exe"
    "%PROGRAMFILES%\Python312\python.exe"
    "%PROGRAMFILES%\Python311\python.exe"
) do (
    if exist %%P (
        set PYTHON=%%P
        goto :found_python
    )
)

echo  ERROR: Python not found.
echo  Install from https://python.org and tick "Add Python to PATH"
echo.
pause
exit /b 1

:found_python
echo  Python : %PYTHON%
%PYTHON% --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python found but won't run. Check your installation.
    pause & exit /b 1
)
echo  OK.
echo.

REM ── Install dependencies ───────────────────────────────
echo  [1/2] Installing dependencies...
%PYTHON% -m pip install -r requirements.txt --quiet --disable-pip-version-check
echo  Done.
echo.

REM ── Build EXE + Installer ──────────────────────────────
echo  [2/2] Building EXE + Installer...
echo  (Takes 2-4 minutes - do not close this window)
echo.
%PYTHON% main.py --build

if errorlevel 1 (
    echo.
    echo  =====================================================
    echo   Build FAILED - see errors above
    echo  =====================================================
    echo.
    pause
    exit /b 1
)

echo.
echo  =====================================================
echo   Build Complete!
echo  =====================================================
echo.
if exist "dist\FluxKey\FluxKey.exe"   echo   EXE       -^> dist\FluxKey\FluxKey.exe
if exist "dist\FluxKey_Installer.exe" echo   Installer -^> dist\FluxKey_Installer.exe
echo.
pause
