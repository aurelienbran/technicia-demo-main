# start.bat (pour Windows)
@echo off
echo 🚀 Démarrage de TechnicIA Demo...

REM Vérification du fichier .env
if not exist ".env" (
    echo ❌ Fichier .env manquant !
    exit /b 1
)

REM Démarrage de Qdrant
echo 📊 Démarrage de Qdrant...
docker-compose up -d

REM Attente du démarrage de Qdrant
echo ⏳ Attente du démarrage de Qdrant...
timeout /t 5 /nobreak > nul

REM Démarrage du backend
echo 🔧 Démarrage du backend...
start cmd /k "cd backend && call venv\Scripts\activate && uvicorn main:app --reload"

REM Démarrage du frontend
echo 🎨 Démarrage du frontend...
start cmd /k "cd frontend && npm run dev"

echo ✨ TechnicIA Demo est lancé !
echo 📱 Frontend: http://localhost:5173
echo 🔌 Backend: http://localhost:8000

echo Appuyez sur Ctrl+C dans les fenêtres de commande pour arrêter...
pause