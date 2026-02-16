# Script de build pour Discord Monitor
# Génère discord-monitor.exe avec PyInstaller

param(
    [switch]$NoConsole  # Build sans fenêtre console (pour démarrage silencieux)
)

$ErrorActionPreference = "Stop"

Write-Host "Installation des dependances de build..." -ForegroundColor Cyan
uv pip install pyinstaller

$args = @(
    "main.py",
    "--name", "discord-monitor",
    "--onefile",
    "--clean",
    "--noconfirm"
)

if ($NoConsole) {
    Write-Host "Build en mode sans console (ideal pour demarrage Windows)" -ForegroundColor Yellow
    $args += "--noconsole"
} else {
    Write-Host "Build avec console (pour usage manuel)" -ForegroundColor Yellow
}

Write-Host "Lancement de PyInstaller..." -ForegroundColor Cyan
uv run pyinstaller $args

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Build termine !" -ForegroundColor Green
    Write-Host "Executable : dist\discord-monitor.exe" -ForegroundColor Green
    Write-Host ""
    Write-Host "Utilisation :" -ForegroundColor Cyan
    Write-Host "  .\dist\discord-monitor.exe --install-startup   # Ajouter au demarrage"
    Write-Host "  .\dist\discord-monitor.exe --startup           # Lancer (check + repair + Discord)"
}
