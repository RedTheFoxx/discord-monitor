# Discord Monitor

Surveille Discord et Vencord, détecte les installations cassées, répare automatiquement et peut lancer Discord au démarrage de Windows.

## Installation

```powershell
uv sync
```

## Utilisation

| Commande | Description |
|----------|-------------|
| `uv run python main.py` | Affiche le statut Discord et Vencord |
| `uv run python main.py --startup` | Vérifie Vencord, répare si cassé, lance Discord |
| `uv run python main.py --startup --silent` | Idem, sans messages (pour démarrage automatique) |
| `uv run python main.py --repair` | Répare Vencord si cassé |
| `uv run python main.py --launch` | Lance Discord (avec vérification) |
| `uv run python main.py --install-startup` | Ajoute au démarrage Windows |
| `uv run python main.py --uninstall-startup` | Retire du démarrage Windows |

## Lancer au démarrage

### Option A : Avec l'exécutable (recommandé)

1. **Packagez** : `.\build.ps1 -NoConsole`
2. **Installez** : `.\dist\discord-monitor.exe --install-startup`
3. Au prochain démarrage, Discord sera lancé après vérification/réparation de Vencord

### Option B : En mode script

1. **Installez** : `uv run python main.py --install-startup`  
   (nécessite que le projet reste accessible et uv/Python installés)

## Build exécutable (PyInstaller)

```powershell
# Avec console (usage manuel, diagnostic)
.\build.ps1

# Sans console (démarrage silencieux, idéal pour --install-startup)
.\build.ps1 -NoConsole
```

L'exécutable sera dans `dist\discord-monitor.exe`. Le build `-NoConsole` évite toute fenêtre au démarrage.

---

## Distribution à vos amis

### Ce que vous partagez

Un seul fichier : **`discord-monitor.exe`** (construit avec `.\build.ps1 -NoConsole`).

Partagez-le par lien de téléchargement (Drive, Dropbox, GitHub Releases, etc.). Aucune installation ni Python requis.

### Prérequis pour vos amis

- **Windows** (10 ou 11)
- **Discord** installé (version classique)
- **Vencord** déjà installé sur Discord (le programme répare Vencord s’il est cassé, mais ne fait pas l’installation initiale)

### Utilisation pour vos amis

#### Première utilisation

1. Placer `discord-monitor.exe` où ils veulent (bureau, dossier, etc.)
2. Double-cliquer ou lancer en ligne de commande :
   ```
   discord-monitor.exe --startup
   ```
   → Vérifie Vencord, répare si cassé, lance Discord.

#### Lancer au démarrage Windows

1. Ouvrir une invite de commande ou PowerShell dans le dossier de l’exe
2. Exécuter :
   ```
   discord-monitor.exe --install-startup
   ```
3. Au prochain démarrage, Discord sera lancé automatiquement après vérification de Vencord.

#### Commandes utiles

| Commande | Usage |
|----------|--------|
| `discord-monitor.exe` | Voir le statut Discord et Vencord |
| `discord-monitor.exe --startup` | Lancer Discord (avec vérification) |
| `discord-monitor.exe --repair` | Réparer Vencord si cassé |
| `discord-monitor.exe --uninstall-startup` | Désactiver le lancement au démarrage |

### Si Vencord n’est pas encore installé

Le script ne peut pas faire la première installation de Vencord. Vos amis doivent :

1. Aller sur [vencord.dev](https://vencord.dev)
2. Télécharger et lancer l’installateur Vencord
3. Choisir Discord et installer
4. Après cela, `discord-monitor.exe` pourra surveiller et réparer automatiquement
