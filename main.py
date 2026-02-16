import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

import click
import psutil
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# Chemins Windows par défaut pour Discord
DISCORD_PATHS = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Discord",
    Path(os.environ.get("APPDATA", "")) / "Discord",
]

# Vencord Installer CLI
VENCORD_INSTALLER_URL = "https://github.com/Vencord/Installer/releases/latest/download/VencordInstallerCli.exe"
VENCORD_INSTALLER_FILENAME = "VencordInstallerCli.exe"


def get_vencord_installer_path() -> Path:
    """Chemin du cache pour l'installateur Vencord (dossier discord-monitor dans LOCALAPPDATA)."""
    localappdata = os.environ.get("LOCALAPPDATA", "")
    if not localappdata:
        localappdata = Path.home() / "AppData" / "Local"
    return Path(localappdata) / "discord-monitor" / VENCORD_INSTALLER_FILENAME


def download_vencord_installer(silent: bool = False) -> Path | None:
    """
    Télécharge VencordInstallerCli.exe si nécessaire.
    Retourne le chemin de l'exécutable ou None en cas d'échec.
    """
    installer_path = get_vencord_installer_path()
    installer_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if not silent:
            console.print("[dim]Téléchargement de l'installateur Vencord...[/dim]")
        urllib.request.urlretrieve(VENCORD_INSTALLER_URL, installer_path)
        return installer_path
    except OSError as e:
        if not silent:
            console.print(f"[red]Échec du téléchargement : {e}[/red]")
        return None


def kill_discord_processes() -> bool:
    """Arrête tous les processus Discord. Retourne True si au moins un a été tué."""
    killed = False
    for proc in psutil.process_iter(attrs=["pid", "name"]):
        try:
            if proc.info["name"] and proc.info["name"].lower() == "discord.exe":
                proc.kill()
                proc.wait(timeout=5)
                killed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
            pass
    return killed


def repair_vencord(silent: bool = False) -> bool:
    """
    Répare Vencord : télécharge l'installateur si besoin, tue Discord, exécute --repair.
    Retourne True si la réparation a réussi.
    """
    installer_path = get_vencord_installer_path()
    if not installer_path.exists():
        installer_path = download_vencord_installer(silent=silent)
        if not installer_path:
            return False

    if kill_discord_processes() and not silent:
        console.print("[dim]Discord arrêté.[/dim]")

    if not silent:
        console.print("[dim]Exécution de la réparation Vencord...[/dim]")
    try:
        result = subprocess.run(
            [str(installer_path), "--repair", "--branch", "auto"],
            timeout=120,
            capture_output=silent,
        )
        if result.returncode == 0:
            if not silent:
                console.print("[green]Réparation Vencord terminée avec succès.[/green]")
            return True
        if not silent:
            console.print("[red]La réparation Vencord a échoué.[/red]")
        return False
    except subprocess.TimeoutExpired:
        if not silent:
            console.print("[red]La réparation a expiré (timeout 2 min).[/red]")
        return False
    except OSError as e:
        if not silent:
            console.print(f"[red]Erreur lors de l'exécution de l'installateur : {e}[/red]")
        return False


def get_discord_install_path() -> Path | None:
    """Trouve le chemin d'installation de Discord (version la plus récente)."""
    for base in DISCORD_PATHS:
        if not base.exists():
            continue
        app_dirs = [d for d in base.iterdir() if d.is_dir() and d.name.startswith("app-")]
        if not app_dirs:
            continue
        # Extraire les versions (ex: app-1.0.9224 -> (1, 0, 9224))
        def parse_version(name: str) -> tuple:
            match = re.match(r"app-(\d+)\.(\d+)\.(\d+)", name)
            return (int(match.group(1)), int(match.group(2)), int(match.group(3))) if match else (0, 0, 0)

        latest = max(app_dirs, key=lambda d: parse_version(d.name))
        exe_path = latest / "Discord.exe"
        if exe_path.exists():
            return latest
    return None


# Tailles minimales pour les bundles Vencord (patcher.js ~40KB, vencord.asar ~centaines de KB)
VENCORD_BUNDLE_MIN_SIZE = 10 * 1024  # 10 KB (patcher.js fait ~40KB)


def _get_vencord_path_from_app_asar(app_asar_path: Path) -> Path | None:
    """
    Extrait le chemin du bundle Vencord depuis le contenu de app.asar.
    L'installateur écrit require("chemin") - peut être vencord.asar ou dist/patcher.js.
    Retourne None si le chemin n'est pas trouvé.
    """
    try:
        data = app_asar_path.read_bytes()
        # Chercher require("...") - .asar ou .js (patcher.js dans la nouvelle structure)
        for pattern in (
            rb'require\s*\(\s*"([^"]+\.(?:asar|js))"\s*\)',
            rb"require\s*\(\s*'([^']+\.(?:asar|js))'\s*\)",
        ):
            match = re.search(pattern, data)
            if match:
                path_str = match.group(1).decode("utf-8", errors="replace")
                path_str = path_str.replace("\\\\", "\\")
                return Path(path_str)
    except (OSError, UnicodeDecodeError):
        pass
    return None


def _get_vencord_bundle_path(install_path: Path) -> Path | None:
    """
    Retourne le chemin vers le bundle Vencord (vencord.asar ou dist/patcher.js).
    Source : chemin extrait de app.asar, sinon emplacements connus.
    """
    app_asar = install_path / "resources" / "app.asar"
    if not app_asar.exists():
        return None
    # 1. Extraire le chemin réel depuis app.asar (source de vérité)
    extracted = _get_vencord_path_from_app_asar(app_asar)
    if extracted and extracted.exists():
        return extracted
    # 2. Fallback : emplacements connus (ancienne structure .asar + nouvelle dist/patcher.js)
    candidates = []
    for env_var in ("APPDATA", "LOCALAPPDATA"):
        appdata = os.environ.get(env_var, "")
        if appdata:
            base = Path(appdata) / "Vencord"
            candidates.extend([base / "vencord.asar", base / "dist" / "patcher.js"])
    discord_data = os.environ.get("APPDATA", "")
    if discord_data:
        base = Path(discord_data) / "VencordData"
        candidates.extend([base / "vencord.asar", base / "dist" / "patcher.js"])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def is_vencord_present() -> bool:
    """Vérifie si Vencord est présent (référence dans app.asar)."""
    install_path = get_discord_install_path()
    if not install_path:
        return False
    app_asar = install_path / "resources" / "app.asar"
    if not app_asar.exists():
        return False
    try:
        data = app_asar.read_bytes()
        return b"vencord" in data.lower() or b"Vencord" in data
    except OSError:
        return False


def is_vencord_loaded() -> bool:
    """Alias de is_vencord_present() pour compatibilité."""
    return is_vencord_present()


def is_vencord_valid() -> bool:
    """
    Vérifie que Vencord est correctement installé :
    - _app.asar existe (sauvegarde de l'original Discord)
    - Bundle Vencord existe (vencord.asar ou dist/patcher.js) et a une taille minimale
    """
    if not is_vencord_present():
        return False
    install_path = get_discord_install_path()
    if not install_path:
        return False
    # Vérifier _app.asar
    app_asar_backup = install_path / "resources" / "_app.asar"
    if not app_asar_backup.exists():
        return False
    # Vérifier le bundle Vencord (chemin extrait ou emplacements connus)
    bundle_path = _get_vencord_bundle_path(install_path)
    if not bundle_path or not bundle_path.exists():
        return False
    try:
        return bundle_path.stat().st_size >= VENCORD_BUNDLE_MIN_SIZE
    except OSError:
        return False


def get_vencord_status() -> str:
    """
    Retourne l'état de Vencord : 'valide', 'cassé' ou 'absent'.
    """
    if not is_vencord_present():
        return "absent"
    if is_vencord_valid():
        return "valide"
    return "cassé"


def is_discord_running() -> bool:
    """Vérifie si Discord.exe est en cours d'exécution."""
    for proc in psutil.process_iter(attrs=['name']):
        if proc.info['name'] and proc.info['name'].lower() == 'discord.exe':
            return True
    return False


def get_discord_processes():
    """Retourne la liste des processus Discord.exe trouvés."""
    processes = []
    for proc in psutil.process_iter(attrs=['pid', 'name', 'status']):
        if proc.info['name'] and proc.info['name'].lower() == 'discord.exe':
            processes.append(proc.info)
    return processes


def launch_discord(silent: bool = False) -> bool:
    """Lance Discord via son exécutable. Retourne True si le lancement a réussi."""
    install_path = get_discord_install_path()
    if not install_path:
        if not silent:
            console.print("[red]Discord n'a pas été trouvé sur ce système.[/red]")
        return False
    exe_path = install_path / "Discord.exe"
    try:
        flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        subprocess.Popen(
            [str(exe_path)],
            cwd=str(install_path),
            creationflags=flags,
        )
        return True
    except OSError as e:
        if not silent:
            console.print(f"[red]Erreur lors du lancement de Discord : {e}[/red]")
        return False


def _vencord_status_display(status: str) -> tuple[str, str]:
    """Retourne (texte, style_bordure) pour l'affichage du statut Vencord."""
    if status == "valide":
        return "[green][OK] Vencord valide et fonctionnel[/green]", "green"
    if status == "cassé":
        return "[yellow][!] Vencord cassé (paramètres absents) - exécutez --repair[/yellow]", "yellow"
    return "[red][X] Vencord absent[/red]", "red"


def _run_startup_mode(silent: bool = False) -> None:
    """
    Mode démarrage : vérifie Vencord, répare si cassé, lance Discord.
    Utilisé au démarrage de la machine.
    """
    install_path = get_discord_install_path()
    if not install_path:
        if not silent:
            console.print("[red]Discord n'est pas installé.[/red]")
        return

    vencord_status = get_vencord_status()

    if vencord_status == "cassé":
        if not silent:
            console.print("[yellow]Vencord cassé détecté. Réparation en cours...[/yellow]")
        if repair_vencord(silent=silent) and not silent:
            console.print("[green]Vencord réparé.[/green]")
    elif vencord_status == "absent" and not silent:
        console.print("[dim]Vencord non installé. Lancement de Discord standard.[/dim]")

    if not silent:
        console.print("[dim]Lancement de Discord...[/dim]")
    if launch_discord(silent=silent):
        if not silent:
            console.print("[green]Discord lancé.[/green]")


def _install_startup() -> bool:
    """Ajoute le programme au démarrage Windows. Retourne True si succès."""
    if os.name != "nt":
        console.print("[red]L'installation au démarrage n'est supportée que sur Windows.[/red]")
        return False
    startup_folder = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    if not startup_folder.exists():
        console.print("[red]Dossier de démarrage introuvable.[/red]")
        return False
    # PyInstaller : sys.executable = exe. Sinon : python + chemin main.py
    if getattr(sys, "frozen", False):
        cmd = f'"{sys.executable}" --startup --silent'
    else:
        main_py = Path(__file__).resolve()
        cmd = f'"{sys.executable}" "{main_py}" --startup --silent'
    bat_path = startup_folder / "discord-monitor-startup.bat"
    bat_content = f'@echo off\nstart "" {cmd}\n'
    try:
        bat_path.write_text(bat_content, encoding="utf-8")
        console.print(f"[green]Fichier de démarrage créé : {bat_path}[/green]")
        return True
    except OSError as e:
        console.print(f"[red]Erreur : {e}[/red]")
        return False


def _uninstall_startup() -> bool:
    """Retire le programme du démarrage Windows. Retourne True si succès."""
    if os.name != "nt":
        console.print("[red]Seul Windows est supporté.[/red]")
        return False
    startup_folder = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    removed = False
    for name in ("discord-monitor-startup.bat",):
        path = startup_folder / name
        if path.exists():
            try:
                path.unlink()
                console.print(f"[green]Supprimé : {path}[/green]")
                removed = True
            except OSError as e:
                console.print(f"[red]Erreur lors de la suppression de {path} : {e}[/red]")
    if not removed:
        console.print("[yellow]Aucune entrée de démarrage trouvée.[/yellow]")
    return removed


@click.command()
@click.option("--monitor", is_flag=True, help="Afficher les processus Discord en détail.")
@click.option("--launch", is_flag=True, help="Lancer Discord et vérifier que Vencord est chargé.")
@click.option(
    "--repair",
    is_flag=True,
    help="Détecter Vencord cassé, télécharger l'installateur et exécuter la réparation.",
)
@click.option(
    "--startup",
    is_flag=True,
    help="Mode démarrage : vérifier Vencord, réparer si cassé, puis lancer Discord.",
)
@click.option(
    "--silent",
    is_flag=True,
    help="Réduire les messages (pour --startup en arrière-plan).",
)
@click.option(
    "--install-startup",
    is_flag=True,
    help="Ajouter ce programme au démarrage Windows.",
)
@click.option(
    "--uninstall-startup",
    is_flag=True,
    help="Retirer ce programme du démarrage Windows.",
)
def main(monitor, launch, repair, startup, silent, install_startup, uninstall_startup):
    """CLI pour surveiller Discord et vérifier le chargement de Vencord."""
    if install_startup:
        _install_startup()
        return
    if uninstall_startup:
        _uninstall_startup()
        return

    if startup:
        _run_startup_mode(silent=silent)
        return

    vencord_status = get_vencord_status()

    if repair:
        if vencord_status == "valide":
            console.print("[green]Vencord est déjà valide. Aucune réparation nécessaire.[/green]")
            return
        if vencord_status == "absent":
            console.print(
                "[yellow]Vencord n'est pas installé. Utilisez l'installateur Vencord pour une première installation.[/yellow]"
            )
            return
        # vencord_status == "cassé"
        console.print("[yellow]Vencord cassé détecté. Lancement de la réparation...[/yellow]")
        if repair_vencord():
            vencord_status = get_vencord_status()
            if vencord_status == "valide":
                console.print("[green]Vencord a été réparé avec succès.[/green]")
        return

    if launch:
        vencord_text, vencord_style = _vencord_status_display(vencord_status)
        vencord_panel = Panel(vencord_text, title="Vérification Vencord", border_style=vencord_style)
        console.print(vencord_panel)

        if vencord_status != "valide":
            if vencord_status == "cassé":
                console.print("[yellow]Exécutez avec --repair pour réparer Vencord.[/yellow]")
            else:
                console.print("[yellow]Attention : Discord sera lancé sans Vencord. Réinstallez Vencord si nécessaire.[/yellow]")

        console.print("[dim]Lancement de Discord...[/dim]")
        if launch_discord():
            console.print("[green]Discord a été lancé.[/green]")
        return

    # Vérification du statut Discord.exe
    discord_running = is_discord_running()
    status_text = "[green][OK] En cours d'exécution[/green]" if discord_running else "[red][X] Non exécuté[/red]"
    status_panel = Panel(
        f"[bold]Discord.exe[/bold] : {status_text}",
        title="Statut Discord",
        border_style="green" if discord_running else "red",
    )
    console.print(status_panel)

    # Vérification Vencord (3 états : valide, cassé, absent)
    vencord_text, vencord_style = _vencord_status_display(vencord_status)
    vencord_panel = Panel(vencord_text, title="Vencord", border_style=vencord_style)
    console.print(vencord_panel)

    if monitor:
        monitor_discord()


def monitor_discord():
    """Monitor the Discord process."""
    discord_procs = get_discord_processes()
    table = Table(title="Discord Process Monitor")
    table.add_column("Process ID", justify="right", style="cyan", no_wrap=True)
    table.add_column("Nom", style="magenta")
    table.add_column("Statut", style="green")

    if discord_procs:
        for proc in discord_procs:
            table.add_row(str(proc['pid']), proc['name'], proc['status'])
    else:
        table.add_row("-", "Aucun processus Discord.exe", "-")

    console.print(table)

if __name__ == '__main__':
    main()