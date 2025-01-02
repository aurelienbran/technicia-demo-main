#!/bin/bash

# Script d'installation pour Linux/MacOS

echo "Installation de TechnicIA Demo..."

# Vérification de Python
if ! command -v python3 &> /dev/null; then
    echo "Python n'est pas installé. Veuillez installer Python 3.10 ou supérieur."
    exit 1
fi

# Vérification de Node.js
if ! command -v node &> /dev/null; then
    echo "Node.js n'est pas installé. Veuillez installer Node.js."
    exit 1
fi

# Vérification de Docker
if ! command -v docker &> /dev/null; then
    echo "Docker n'est pas installé. Veuillez installer Docker."
    exit 1
fi

# Configuration du backend
cd backend
echo "Configuration de l'environnement Python..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..

# Configuration du frontend
cd frontend
echo "Installation des dépendances Node.js..."
npm install
cd ..

# Configuration de Docker
echo "Configuration de Qdrant..."
docker-compose up -d

echo "Installation terminée avec succès!"
