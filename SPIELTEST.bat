@echo off
rem ============================================================
rem  SPIELTEST - direkt ins Spiel, ohne Menue und ohne Intro.
rem
rem  Zum Ausprobieren der Spielmechanik. Wer das ganze Spiel mit
rem  Menue will, nimmt DUSTFRONT.bat daneben.
rem
rem  Mit goto statt verschachtelten Klammern gebaut: tiefe
rem  if-Bloecke sind in cmd eine verlaessliche Fehlerquelle.
rem ============================================================
setlocal
title DUSTFRONT - SPIELTEST

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
echo   DUSTFRONT - Spieltest
echo.
echo   W A S D laufen, Maus zielen, links schiessen
echo   1 bis 6 Waffe, R nachladen, H Medkit
echo   E Treppe, Mausrad Ebene ansehen, Tab Inventar
echo   T Ziellinie, Esc Pause
echo.
%PY% -m dustfront %*
if not errorlevel 1 exit /b 0

echo.
echo   Der Spieltest wurde mit einem Fehler beendet.
echo   Die Meldung darueber sagt, woran es lag.
echo.
pause
exit /b 1
