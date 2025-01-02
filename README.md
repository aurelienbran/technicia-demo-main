# TechnicIA Demo - Guide d'Installation

## Prérequis

- Python 3.10 ou supérieur
- Node.js et npm
- Docker et Docker Compose

## Installation

### Windows
1. Double-cliquez sur `install.bat`
2. Attendez la fin de l'installation
3. Double-cliquez sur `start.bat` pour démarrer l'application

### Linux/MacOS
1. Ouvrez un terminal
2. Rendez les scripts exécutables :
   ```bash
   chmod +x install.sh start.sh
   ```
3. Lancez l'installation :
   ```bash
   ./install.sh
   ```
4. Démarrez l'application :
   ```bash
   ./start.sh
   ```

## Accès à l'Application

- Interface utilisateur : http://localhost:5173
- API Backend : http://localhost:8000

## Structure des Fichiers

```
technicia-demo/
├── install.bat     # Script d'installation Windows
├── install.sh      # Script d'installation Linux/MacOS
├── start.bat       # Script de démarrage Windows
├── start.sh        # Script de démarrage Linux/MacOS
└── README.md       # Documentation
```

## Problèmes Courants

1. Si Docker n'est pas démarré :
   - Windows : Démarrez Docker Desktop
   - Linux : `sudo systemctl start docker`

2. Si les ports sont déjà utilisés :
   - Vérifiez qu'aucune autre application n'utilise les ports 5173, 8000, ou 6333
   - Fermez les applications concernées

3. En cas d'erreur d'installation :
   - Vérifiez la connexion Internet
   - Vérifiez les versions des prérequis
   - Consultez les logs dans les dossiers backend et frontend
