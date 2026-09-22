@echo off
rem ============================================================
rem  DUSTFRONT - LAN GAST
rem  Verbindet sich mit einem Gastgeber.
rem ============================================================
setlocal
title DUSTFRONT - LAN GAST
cd /d "%~dp0"

set "PY="
py -3 --version >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if defined PY goto habe_python
python --version >nul 2>&1
if not errorlevel 1 set "PY=python"
if defined PY goto habe_python
echo.
echo   Python wurde nicht gefunden.
echo   Hol es dir von https://www.python.org/downloads/
echo   Beim Installieren den Haken bei "Add Python to PATH" setzen.
echo.
pause
exit /b 1

:habe_python
%PY% -c "import pygame" >nul 2>&1
if not errorlevel 1 goto fragen
echo.
echo   pygame-ce fehlt. Wird jetzt installiert.
echo.
%PY% -m pip install pygame-ce
if not errorlevel 1 goto fragen
echo.
echo   Die Installation ist fehlgeschlagen.
echo.
pause
exit /b 1

:fragen
echo.
echo   DUSTFRONT - LAN GAST
echo.
set "NAME="
set /p "NAME=  Dein Name (Enter = GAST): "
if "%NAME%"=="" set "NAME=GAST"

echo.
echo   Die Spielart bestimmt der Gastgeber.
echo.
echo   In welche Mannschaft willst du, falls mit Mannschaften gespielt wird?
echo     1  ROT
echo     2  BLAU
echo     3  egal, teil mich ein
echo.
set "TEAM=auto"
set "WAHL="
set /p "WAHL=  Welche (Enter = 3): "
if "%WAHL%"=="1" set "TEAM=rot"
if "%WAHL%"=="2" set "TEAM=blau"

echo.
set "WOHIN="
set /p "WOHIN=  Adresse des Gastgebers: "
if "%WOHIN%"=="" goto fragen
echo.
%PY% -m dustfront --join "%WOHIN%" --name "%NAME%" --team %TEAM%
if not errorlevel 1 exit /b 0
echo.
echo   Beendet mit einem Fehler. Die Meldung darueber sagt, woran es lag.
echo.
pause
exit /b 1
