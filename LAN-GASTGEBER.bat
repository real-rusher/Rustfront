@echo off
rem ============================================================
rem  DUSTFRONT - LAN GASTGEBER
rem  Macht eine Runde auf. Die Spielart und alles andere stellst
rem  du danach im Spiel ein, in der Lobby (Taste P).
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
echo   Wer soll mitspielen koennen?
echo     1  nur im eigenen Netz (LAN)
echo     2  auch ueber das Internet
echo.
set "ONLINE="
set "PASSWORT="
set "WAHL="
set /p "WAHL=  Welche (Enter = 1): "
if not "%WAHL%"=="2" goto los
set "ONLINE=--online"
echo.
echo   Das Spiel versucht, den Port im Router selbst freizugeben.
echo   Klappt das nicht, sagt es gleich, was einzutragen ist.
echo   Wer die Adresse kennt, kann mitspielen - darum ein Kennwort:
set /p "PASSWORT=  Kennwort (Enter = keins): "

rem Mehr wird hier nicht gefragt. Spielart, Karte, Runden und alles
rem andere stellst du im Spiel ein: es geht zuerst in die Lobby, dort
rem oeffnet P die Tafel dafuer.

:los
echo.
%PY% -m dustfront --host --name "%NAME%" --passwort "%PASSWORT%" %ONLINE%
if not errorlevel 1 exit /b 0
echo.
echo   Beendet mit einem Fehler. Die Meldung darueber sagt, woran es lag.
echo.
pause
exit /b 1
