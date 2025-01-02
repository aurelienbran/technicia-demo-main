@echo off
REM Script d'installation pour Windows

echo Installation de TechnicIA Demo...

REM Vérification de Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python n'est pas installé. Veuillez installer Python 3.10 ou supérieur.
    exit /b 1
)

REM Vérification de Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Node.js n'est pas installé. Veuillez installer Node.js.
    exit /b 1
)

REM Vérification de Docker
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Docker n'est pas installé. Veuillez installer Docker Desktop.
    exit /b 1
)

REM Configuration du backend
cd backend
echo Configuration de l'environnement Python...
python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt
cd ..

REM Configuration du frontend
cd frontend
echo Installation des dépendances Node.js...
npm install
cd ..

REM Configuration de Docker
echo Configuration de Qdrant...
docker-compose up -d

echo Installation terminée avec succès!
