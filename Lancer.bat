@echo off
rem Lance l'application de planning du materiel topo.
rem Double-cliquez sur ce fichier. Laissez la fenetre noire ouverte pendant l'utilisation.
cd /d "%~dp0"
title Planning materiel topo

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY goto pas_de_python

if not exist ".venv\Scripts\python.exe" (
    echo Premier lancement : preparation de l'application, 1 a 2 minutes...
    %PY% -m venv .venv
    if errorlevel 1 goto pas_de_python
)

rem Installe ou met a jour les composants si la liste a change depuis la derniere fois.
fc /b requirements.txt ".venv\installe.txt" >nul 2>nul
if errorlevel 1 (
    echo Installation des composants necessaires, connexion Internet requise...
    ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
    if errorlevel 1 goto erreur_installation
    copy /y requirements.txt ".venv\installe.txt" >nul
)

".venv\Scripts\python.exe" app\serveur.py
if errorlevel 1 pause
exit /b 0

:pas_de_python
echo.
echo Python n'est pas installe (ou pas trouve).
echo Installez-le depuis https://www.python.org/downloads/ puis relancez ce fichier.
echo Voir le fichier README.md, etape 1.
echo.
pause
exit /b 1

:erreur_installation
echo.
echo L'installation des composants a echoue. Verifiez la connexion Internet
echo puis relancez ce fichier.
echo.
pause
exit /b 1
