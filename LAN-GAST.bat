@echo off
rem ============================================================
rem  LAN GAST - verbindet sich mit einem Gastgeber
rem
rem  Fragt nach Name und Adresse des Gastgebers und verbindet
rem  sich. Die Adresse zeigt der Gastgeber in seinem Fenster.
rem
rem  Mit goto statt verschachtelten Klammern gebaut: tiefe
rem  if-Bloecke sind in cmd eine verlaessliche Fehlerquelle.
rem ============================================================
setlocal
title DUSTFRONT - GAST

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
echo   DUSTFRONT - GAST
echo.
set "NAME="
set /p "NAME=  Dein Name (Enter = GAST): "
if "%NAME%"=="" set "NAME=GAST"
set "WOHIN="
set /p "WOHIN=  Adresse des Gastgebers: "
if "%WOHIN%"=="" goto fragen
echo.
%PY% -m dustfront --join "%WOHIN%" --name "%NAME%"
if not errorlevel 1 exit /b 0

echo.
echo   Beendet mit einem Fehler. Die Meldung darueber sagt, woran es lag.
echo.
pause
exit /b 1
