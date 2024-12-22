# install.bat (pour Windows)
@echo off
echo 📦 Installation de TechnicIA Demo...

REM Vérification des prérequis
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python 3 requis
    exit /b 1
)

node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Node.js requis
    exit /b 1
)

docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker requis
    exit /b 1
)

REM Configuration backend
echo 🐍 Configuration du backend...
cd backend
python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt
cd ..

REM Configuration frontend
echo ⚛️ Configuration du frontend...
cd frontend
call npm install
cd ..

echo ✅ Installation terminée !
echo 📝 N'oubliez pas de configurer votre fichier .env avec vos clés API