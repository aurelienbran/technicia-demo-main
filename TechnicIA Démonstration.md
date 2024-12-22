# TechnicIA Démonstration

## Vue d'ensemble
TechnicIA est un chatbot technique utilisant l'IA pour répondre aux questions basées sur une documentation technique. Il combine :
- Claude AI pour la génération de réponses
- Voyage AI pour les embeddings
- Qdrant pour la recherche sémantique
- Une interface utilisateur simple et élégante

## Structure du Projet
```
technicia-demo/
├── .env                    # Configuration des clés API
├── docker-compose.yml      # Configuration Qdrant
├── backend/
│   ├── main.py            # API FastAPI
│   ├── requirements.txt    # Dépendances Python
│   └── docs/              # Dossier pour les PDFs
└── frontend/
    ├── package.json
    └── src/
        └── App.jsx        # Interface utilisateur
```

## Configuration requise
- Python 3.10+
- Node.js 18+
- Docker et Docker Compose
- Clés API :
  * Anthropic (Claude AI)
  * Voyage AI

## Dépendances

### Backend (requirements.txt)
```
fastapi
uvicorn
python-dotenv
anthropic
aiohttp
qdrant-client
watchdog
PyMuPDF
```

### Frontend (package.json)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "lucide-react": "^0.263.1",
    "@radix-ui/react-scroll-area": "^1.0.5"
  }
}
```

## Configuration (.env)
```
ANTHROPIC_API_KEY=votre_clé_claude
VOYAGE_API_KEY=votre_clé_voyage
```

## Fonctionnalités
1. **Indexation Automatique**
   - Surveillance du dossier `docs/`
   - Indexation automatique des PDFs
   - Vectorisation avec Voyage AI

2. **Recherche Sémantique**
   - Base vectorielle Qdrant
   - Recherche par similarité
   - Récupération du contexte pertinent

3. **Interface Utilisateur**
   - Chat intuitif
   - Indicateurs de chargement
   - Design responsive

## Utilisation
1. Placez vos PDFs dans le dossier `docs/`
2. Posez vos questions dans l'interface
3. Le système :
   - Cherche le contenu pertinent
   - Génère une réponse contextualisée
   - Affiche la réponse dans l'interface

## Limitations de la Demo
- Pas d'authentification
- Pas de persistance des conversations
- Support uniquement des PDFs

# Première utilisation
./install.bat

# Configurer le .env avec vos clés API

# Lancer la démo
./start.bat 