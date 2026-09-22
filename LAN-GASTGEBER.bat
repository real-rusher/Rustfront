@echo off
rem ============================================================
rem  DUSTFRONT - LAN GASTGEBER
rem  Macht eine Runde auf und waehlt die Spielart.
rem ============================================================
setlocal
title DUSTFRONT - LAN GASTGEBER
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
echo   DUSTFRONT - LAN GASTGEBER
echo.
set "NAME="
set /p "NAME=  Dein Name (Enter = GASTGEBER): "
if "%NAME%"=="" set "NAME=GASTGEBER"

echo.
echo   Spielart:
echo     1  PVP     jeder gegen jeden
echo     2  PVE     alle zusammen gegen Wellen, mit Aufhelfen
echo     3  PVPVE   Wellen, und dabei jeder gegen jeden
echo.
set "MODUS=pvp"
set "WAHL="
set /p "WAHL=  Welche (Enter = 1): "
if "%WAHL%"=="2" set "MODUS=pve"
if "%WAHL%"=="3" set "MODUS=pvpve"

set "ENDE=zeit"
set "WERT=0"
if "%MODUS%"=="pve" goto muni

echo.
echo   Wann endet die Runde?
echo     1  nach Zeit
echo     2  nach Abschuessen
echo.
set "WAHL="
set /p "WAHL=  Welche (Enter = 1): "
if "%WAHL%"=="2" set "ENDE=abschuesse"
if "%ENDE%"=="abschuesse" goto wieviele
set "WERT="
set /p "WERT=  Minuten (Enter = 5): "
if "%WERT%"=="" set "WERT=5"
set /a WERT=%WERT%*60
goto muni

:wieviele
set "WERT="
set /p "WERT=  Abschuesse bis Schluss (Enter = 20): "
if "%WERT%"=="" set "WERT=20"

:muni
set "KNAPP="
if "%MODUS%"=="pvp" goto los
echo.
set "WAHL="
set /p "WAHL=  Munition begrenzen, mit Nachschubkisten? (j/N): "
if /i "%WAHL%"=="j" set "KNAPP=--knapp"

:los
echo.
%PY% -m dustfront --host --name "%NAME%" --modus %MODUS% --ende %ENDE% --wert %WERT% %KNAPP%
if not errorlevel 1 exit /b 0
echo.
echo   Beendet mit einem Fehler. Die Meldung darueber sagt, woran es lag.
echo.
pause
exit /b 1
