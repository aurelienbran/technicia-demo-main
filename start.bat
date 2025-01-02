@echo off
REM Script de démarrage pour Windows

REM Démarrage de Docker et Qdrant si nécessaire
docker-compose up -d

REM Démarrage du backend
start cmd /k "cd backend && .\venv\Scripts\activate && uvicorn main:app --reload"

REM Démarrage du frontend
start cmd /k "cd frontend && npm run dev"

echo TechnicIA Demo est en cours de démarrage...
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
