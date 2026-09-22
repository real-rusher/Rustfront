@echo off
rem ============================================================
rem  DUSTFRONT starten - einfach doppelklicken.
rem
rem  Sucht Python, prueft ob pygame-ce da ist, installiert es
rem  notfalls und startet das Hauptmenue.
rem
rem  Geht etwas schief, bleibt das Fenster offen und sagt warum.
rem  Bewusst mit goto statt verschachtelter Klammern gebaut:
rem  tiefe if-Bloecke sind in cmd eine verlaessliche Fehlerquelle.
rem ============================================================
setlocal
title DUSTFRONT

rem In den Ordner dieser Datei wechseln. Ohne das sucht Python
rem die Spieldateien im falschen Verzeichnis.
cd /d "%~dp0"

rem --- Python suchen -----------------------------------------
rem Erst der Launcher py: python.exe ist auf Windows oft nur ein
rem Platzhalter, der den Store oeffnet statt Python zu starten.
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
echo   Beim Installieren den Haken bei "Add Python to PATH"
echo   setzen, sonst findet Windows es spaeter nicht.
echo.
pause
exit /b 1

:habe_python
rem --- pygame-ce pruefen -------------------------------------
%PY% -c "import pygame" >nul 2>&1
if not errorlevel 1 goto starten

echo.
echo   pygame-ce fehlt. Wird jetzt installiert, das dauert
echo   einmalig etwa eine Minute.
echo.
%PY% -m pip install pygame-ce
if not errorlevel 1 goto starten

echo.
echo   Die Installation ist fehlgeschlagen. Die Meldung
echo   darueber sagt, woran es lag.
echo.
pause
exit /b 1

:starten
rem Argumente werden durchgereicht: eine Verknuepfung kann also
rem --nosplash mitgeben und das Intro ueberspringen.
%PY% rustfront_menu.py %*
if not errorlevel 1 exit /b 0

echo.
echo   DUSTFRONT wurde mit einem Fehler beendet.
echo   Die Meldung darueber sagt, woran es lag.
echo.
pause
exit /b 1
