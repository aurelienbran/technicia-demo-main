#!/bin/bash

# Script de démarrage pour Linux/MacOS

# Démarrage de Docker et Qdrant si nécessaire
docker-compose up -d

# Démarrage du backend dans un terminal
gnome-terminal --title="Backend TechnicIA" -- bash -c "cd backend && source venv/bin/activate && uvicorn main:app --reload" &

# Démarrage du frontend dans un autre terminal
gnome-terminal --title="Frontend TechnicIA" -- bash -c "cd frontend && npm run dev" &

echo "TechnicIA Demo est en cours de démarrage..."
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"
