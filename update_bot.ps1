# Script PowerShell per aggiornare il bot Telegram dal repository GitHub
# Uso: .\update_bot.ps1

$ErrorActionPreference = "Stop"

# Directory del bot
$BOT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $BOT_DIR

Write-Host "🚀 Avvio aggiornamento bot..." -ForegroundColor Green
Write-Host "📁 Directory: $BOT_DIR" -ForegroundColor Cyan
Write-Host ""

# Verifica che Git sia installato
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Git non trovato. Installa Git prima di continuare." -ForegroundColor Red
    exit 1
}

# Verifica Docker
$USE_DOCKER = $false
if ((Get-Command docker -ErrorAction SilentlyContinue) -and (Test-Path "docker-compose.yml")) {
    $USE_DOCKER = $true
    Write-Host "✓ Docker trovato, userò Docker Compose" -ForegroundColor Green
} else {
    Write-Host "⚠ Docker non trovato o docker-compose.yml assente" -ForegroundColor Yellow
}

# Backup opzionale
$backup = Read-Host "Vuoi fare un backup prima dell'aggiornamento? (s/n)"
if ($backup -eq "s" -or $backup -eq "S") {
    Write-Host "📦 Creazione backup..." -ForegroundColor Yellow
    $BACKUP_DIR = "backups/manual_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    New-Item -ItemType Directory -Force -Path $BACKUP_DIR | Out-Null
    
    if (Test-Path "data") {
        Copy-Item -Path "data" -Destination $BACKUP_DIR -Recurse -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path ".env") {
        Copy-Item -Path ".env" -Destination $BACKUP_DIR -Force -ErrorAction SilentlyContinue
    }
    Write-Host "✓ Backup creato in: $BACKUP_DIR" -ForegroundColor Green
}

# Ferma il bot
Write-Host ""
Write-Host "🛑 Fermando il bot..." -ForegroundColor Yellow
if ($USE_DOCKER) {
    docker compose down
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Bot già fermo o non in esecuzione" -ForegroundColor Yellow
    }
} else {
    $process = Get-Process | Where-Object { $_.ProcessName -eq "python" -and $_.CommandLine -like "*main.py*" }
    if ($process) {
        Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        Write-Host "✓ Bot fermato" -ForegroundColor Green
    } else {
        Write-Host "⚠ Bot non trovato in esecuzione" -ForegroundColor Yellow
    }
}

# Salva modifiche locali se presenti
$gitStatus = git status --porcelain
if ($gitStatus) {
    Write-Host ""
    Write-Host "⚠ Trovate modifiche locali" -ForegroundColor Yellow
    $save = Read-Host "Vuoi salvare le modifiche locali? (s/n)"
    if ($save -eq "s" -or $save -eq "S") {
        $stashMsg = "Modifiche locali prima di aggiornamento $(Get-Date -Format 'yyyyMMdd_HHmmss')"
        git stash push -m $stashMsg
        Write-Host "✓ Modifiche salvate in stash" -ForegroundColor Green
    } else {
        Write-Host "⚠ Modifiche locali verranno sovrascritte" -ForegroundColor Yellow
        $continue = Read-Host "Continuare? (s/n)"
        if ($continue -ne "s" -and $continue -ne "S") {
            Write-Host "❌ Aggiornamento annullato" -ForegroundColor Red
            exit 1
        }
    }
}

# Aggiorna dal repository
Write-Host ""
Write-Host "📥 Aggiornando dal repository GitHub..." -ForegroundColor Yellow
git fetch origin

# Verifica se ci sono aggiornamenti
$LOCAL = git rev-parse @
$REMOTE = git rev-parse @{u}

if ($LOCAL -eq $REMOTE) {
    Write-Host "✓ Sei già aggiornato all'ultima versione" -ForegroundColor Green
} else {
    Write-Host "📥 Nuove modifiche disponibili, aggiornamento in corso..." -ForegroundColor Yellow
    git pull origin main
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Repository aggiornato con successo" -ForegroundColor Green
    } else {
        Write-Host "❌ Errore durante il pull. Controlla i conflitti." -ForegroundColor Red
        exit 1
    }
}

# Ricostruisci Docker se necessario
if ($USE_DOCKER) {
    Write-Host ""
    Write-Host "🔨 Ricostruendo l'immagine Docker..." -ForegroundColor Yellow
    docker compose build
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Immagine ricostruita" -ForegroundColor Green
    } else {
        Write-Host "❌ Errore durante la ricostruzione" -ForegroundColor Red
        exit 1
    }
}

# Riavvia il bot
Write-Host ""
Write-Host "🚀 Riavviando il bot..." -ForegroundColor Yellow
if ($USE_DOCKER) {
    docker compose up -d
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Bot avviato" -ForegroundColor Green
    } else {
        Write-Host "❌ Errore durante l'avvio" -ForegroundColor Red
        exit 1
    }
    
    Start-Sleep -Seconds 3
    
    $running = docker compose ps | Select-String "Up"
    if ($running) {
        Write-Host "✓ Bot in esecuzione" -ForegroundColor Green
    } else {
        Write-Host "⚠ Bot potrebbe non essere avviato correttamente" -ForegroundColor Yellow
        Write-Host "Controlla i log con: docker compose logs"
    }
} else {
    # Avvia Python direttamente
    Start-Process python -ArgumentList "main.py" -WindowStyle Hidden
    Start-Sleep -Seconds 2
    
    $process = Get-Process | Where-Object { $_.ProcessName -eq "python" -and $_.CommandLine -like "*main.py*" }
    if ($process) {
        Write-Host "✓ Bot avviato" -ForegroundColor Green
    } else {
        Write-Host "⚠ Bot potrebbe non essere avviato correttamente" -ForegroundColor Yellow
    }
}

# Informazioni finali
Write-Host ""
Write-Host "✅ Aggiornamento completato!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Comandi utili:" -ForegroundColor Cyan
if ($USE_DOCKER) {
    Write-Host "  - Log: docker compose logs -f"
    Write-Host "  - Status: docker compose ps"
    Write-Host "  - Ferma: docker compose down"
} else {
    Write-Host "  - Log: Get-Content bot.log -Wait"
    Write-Host "  - Status: Get-Process python"
    Write-Host "  - Ferma: Stop-Process -Name python"
}
Write-Host "  - Git status: git status"
Write-Host "  - Ultimi commit: git log --oneline -5"

