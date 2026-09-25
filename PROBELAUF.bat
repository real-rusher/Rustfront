@echo off
rem ============================================================
rem  PROBELAUF - den Wandler laufen sehen und selbst fahren.
rem
rem  Zeigt die Laufmaschine von aussen: Beine, Gang, Schaden.
rem  Wer das Spiel selbst will, nimmt DUSTFRONT.bat daneben.
rem
rem  Mit goto statt verschachtelten Klammern gebaut: tiefe
rem  if-Bloecke sind in cmd eine verlaessliche Fehlerquelle.
rem ============================================================
setlocal
title DUSTFRONT - PROBELAUF

rem In den Ordner dieser Datei wechseln. Ohne das sucht Python
rem die Spieldateien im falschen Verzeichnis.
cd /d "%~dp0"

rem --- Python suchen -----------------------------------------
rem Erst der Launcher py: python.exe ist auf Windows oft nur ein
rem Platzhalter, der den Store oeffnet statt Python zu starten.
set "PY="
py -3 --version >/dev/null 2>&1
if not errorlevel 1 set "PY=py -3"
if defined PY goto habe_python

python --version >/dev/null 2>&1
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
%PY% -c "import pygame" >/dev/null 2>&1
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
echo.
echo   DUSTFRONT - Probelauf
echo.
echo   W S Schub, A D Kurs, Shift Ueberlast
echo   H Autopilot, Tab Ansicht naeher oder weiter
echo   1 2 3 Warhound, Reaver, Imperator
echo   4 ein Bein ausfallen lassen, 5 alle richten
echo   F3 Zahlen, Esc zurueck
echo.
%PY% -m dustfront --probe %*
if not errorlevel 1 exit /b 0

echo.
echo   Der Probelauf wurde mit einem Fehler beendet.
echo   Die Meldung darueber sagt, woran es lag.
echo.
pause
exit /b 1
