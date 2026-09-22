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
echo   Wer soll mitspielen koennen?
echo     1  nur im eigenen Netz (LAN)
echo     2  auch ueber das Internet
echo.
set "ONLINE="
set "PASSWORT="
set "WAHL="
set /p "WAHL=  Welche (Enter = 1): "
if not "%WAHL%"=="2" goto spielart
set "ONLINE=--online"
echo.
echo   Das Spiel versucht, den Port im Router selbst freizugeben.
echo   Klappt das nicht, sagt es gleich, was einzutragen ist.
echo   Wer die Adresse kennt, kann mitspielen - darum ein Kennwort:
set /p "PASSWORT=  Kennwort (Enter = keins): "

:spielart

echo.
echo   Spielart:
echo     1  PVP     jeder gegen jeden
echo     2  PVE     alle zusammen gegen Wellen, mit Aufhelfen
echo     3  PVPVE   Wellen, und dabei jeder gegen jeden
echo     4  TEAM    zwei Mannschaften, Abschuesse zaehlen fuer das Team
echo     5  VERSUS  zwei Mannschaften, ein Leben je Runde, mit Aufhelfen
echo     6  HUEGEL  zwei Mannschaften, haltet den Kreis in der Mitte
echo.
set "MODUS=pvp"
set "WAHL="
set /p "WAHL=  Welche (Enter = 1): "
if "%WAHL%"=="2" set "MODUS=pve"
if "%WAHL%"=="3" set "MODUS=pvpve"
if "%WAHL%"=="4" set "MODUS=team"
if "%WAHL%"=="5" set "MODUS=versus"
if "%WAHL%"=="6" set "MODUS=huegel"

set "ENDE=zeit"
set "WERT=0"
if "%MODUS%"=="pve" goto muni
rem versus und huegel enden von selbst. Die Zeit ist nur die Notbremse.
if "%MODUS%"=="versus" goto hoechstdauer
if "%MODUS%"=="huegel" goto hoechstdauer

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
if "%MODUS%"=="team" goto wieviele_team
set /p "WERT=  Abschuesse bis Schluss (Enter = 20): "
if "%WERT%"=="" set "WERT=20"
goto muni

:wieviele_team
set /p "WERT=  Teamabschuesse bis Schluss (Enter = 30): "
if "%WERT%"=="" set "WERT=30"
goto muni

:hoechstdauer
set "WERT="
set /p "WERT=  Hoechstdauer in Minuten (Enter = 10): "
if "%WERT%"=="" set "WERT=10"
set /a WERT=%WERT%*60

:muni
set "RUNDEN=3"
if not "%MODUS%"=="versus" goto teamwahl
echo.
set /p "RUNDEN=  Rundensiege bis zum Schluss (1-9, Enter = 3): "
if "%RUNDEN%"=="" set "RUNDEN=3"

:teamwahl
set "TEAM=auto"
if "%MODUS%"=="pvp" goto munition
if "%MODUS%"=="pve" goto munition
if "%MODUS%"=="pvpve" goto munition
echo.
echo   In welche Mannschaft willst du?
echo     1  ROT
echo     2  BLAU
echo     3  egal, teil mich ein
echo.
set "WAHL="
set /p "WAHL=  Welche (Enter = 3): "
if "%WAHL%"=="1" set "TEAM=rot"
if "%WAHL%"=="2" set "TEAM=blau"

:munition
set "KNAPP="
if "%MODUS%"=="pvp" goto schutz
echo.
set "WAHL="
set /p "WAHL=  Munition begrenzen, mit Nachschubkisten? (j/N): "
if /i "%WAHL%"=="j" set "KNAPP=--knapp"

:schutz
echo.
set "SCHUTZ="
set "WAHL="
set /p "WAHL=  Einstiegsschutz, 2 Sekunden unverwundbar? (J/n): "
if /i "%WAHL%"=="n" set "SCHUTZ=--kein-schutz"

echo.
set "MEDKITS="
set /p "MEDKITS=  Medkits beim Einstieg (Enter = 1): "
if "%MEDKITS%"=="" set "MEDKITS=1"

set "MEDSPAWN="
set "WAHL="
set /p "WAHL=  Medkits immer wieder auf der Karte? (J/n): "
if /i "%WAHL%"=="n" set "MEDSPAWN=--keine-medkits"

:los
echo.
%PY% -m dustfront --host --name "%NAME%" --modus %MODUS% --ende %ENDE% --wert %WERT% --medkits %MEDKITS% --runden %RUNDEN% --team %TEAM% --passwort "%PASSWORT%" %KNAPP% %SCHUTZ% %MEDSPAWN% %ONLINE%
if not errorlevel 1 exit /b 0
echo.
echo   Beendet mit einem Fehler. Die Meldung darueber sagt, woran es lag.
echo.
pause
exit /b 1
