@echo off
rem ============================================================
rem  LAN GASTGEBER - macht eine Runde auf
rem
rem  Startet eine Runde und wartet auf Mitspieler. Die Adresse,
rem  die anzusagen ist, steht danach im Fenster und im Spiel.
rem
rem  Mit goto statt verschachtelten Klammern gebaut: tiefe
rem  if-Bloecke sind in cmd eine verlaessliche Fehlerquelle.
rem ============================================================
setlocal
title DUSTFRONT - GASTGEBER

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
echo.
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
echo   DUSTFRONT - GASTGEBER
echo.
set "NAME="
set /p "NAME=  Dein Name (Enter = GASTGEBER): "
if "%NAME%"=="" set "NAME=GASTGEBER"

echo.
%PY% -m dustfront --host --name "%NAME%"
if not errorlevel 1 exit /b 0

echo.
echo   Beendet mit einem Fehler. Die Meldung darueber sagt, woran es lag.
echo.
pause
exit /b 1
