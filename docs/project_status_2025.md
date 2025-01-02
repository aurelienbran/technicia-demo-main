# État du Projet TechnicIA Demo - Janvier 2025

## Vue d'Ensemble

TechnicIA Demo est une application de démonstration permettant d'interagir avec de la documentation technique via une interface conversationnelle. L'application combine plusieurs technologies avancées pour offrir une expérience utilisateur fluide et efficace.

## 🚀 Fonctionnalités Principales

### 1. Gestion des Documents
- Upload de PDFs via interface web
- Dépôt direct dans le dossier `/backend/docs`
- Surveillance automatique et indexation des nouveaux fichiers
- Système de cache intelligent évitant les retraitements inutiles

### 2. Intelligence Artificielle
- Claude AI pour la génération de réponses contextuelles
- Voyage AI pour la création d'embeddings
- Recherche sémantique via Qdrant

### 3. Interface Utilisateur
- Design minimaliste et intuitif
- Interface de chat réactive
- Affichage des sources par réponse
- Support du drag & drop pour les PDFs

## 🏗️ Architecture Technique

### Backend (FastAPI)
```
backend/
├── app/
│   ├── services/
│   │   ├── watcher.py      # Surveillance automatique
│   │   ├── indexing.py     # Traitement des PDFs
│   │   ├── vector_store.py # Gestion Qdrant
│   │   ├── embedding.py    # Intégration Voyage AI
│   │   └── claude.py       # Intégration Claude
│   ├── core/
│   │   ├── config.py       # Configuration
│   │   └── logging.py      # Logs
│   └── api/
│       └── routes/
│           └── chat.py     # Endpoints API
└── docs/                   # Stockage des PDFs
```

### Frontend (React)
```
frontend/
├── src/
│   └── App.jsx            # Application React
└── public/
```

## 💡 Points Forts

1. **Robustesse**
   - Gestion asynchrone des opérations
   - Système de cache intelligent
   - Gestion efficace des erreurs
   - Logs détaillés

2. **Performance**
   - Evite les retraitements inutiles
   - Optimisation de la vectorisation
   - Cache des documents déjà traités

3. **Facilité d'Utilisation**
   - Interface intuitive
   - Multiple méthodes d'ajout de documents
   - Réponses contextualisées avec sources

## 🔧 Configuration Requise

### Prérequis
- Python 3.10+
- Node.js 18+
- Docker et Docker Compose

### Variables d'Environnement (.env)
```
ANTHROPIC_API_KEY=your_key
VOYAGE_API_KEY=your_key
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

## 🚦 Instructions de Démarrage

1. **Backend**
```bash
cd backend
# Activation de l'environnement virtuel
.\venv\Scripts\activate  # Windows
source venv/bin/activate # Linux/Mac

# Installation des dépendances
pip install -r requirements.txt

# Démarrage du serveur
uvicorn main:app
```

2. **Frontend**
```bash
cd frontend
# Installation des dépendances
npm install

# Démarrage du serveur de développement
npm run dev
```

3. **Services**
```bash
# Dans le dossier racine
docker-compose up -d
```

## 🎯 Points d'Amélioration Possibles

1. **Fonctionnalités**
   - Support de formats supplémentaires (Word, Excel...)
   - Historique des conversations
   - Export des conversations
   - Filtrage par document/date

2. **Technique**
   - Tests unitaires complets
   - Tests d'intégration
   - Documentation API Swagger
   - Monitoring des performances

3. **Interface**
   - Mode sombre
   - Personnalisation de l'interface
   - Gestion des préférences utilisateur
   - Visualisation des documents indexés

## 📝 Notes Techniques

### Système de Cache
Le système utilise un hash unique basé sur :
- Le nom du fichier
- La taille du fichier
- La date de modification

Ce hash permet d'éviter la revectorisation des fichiers non modifiés lors des redémarrages.

### Gestion Asynchrone
- Utilisation de FastAPI pour les opérations asynchrones
- Queue de traitement pour les nouveaux fichiers
- Gestion thread-safe des opérations de fichiers

### Sécurité
- Validation des types de fichiers
- Vérification des permissions
- Nettoyage des fichiers temporaires