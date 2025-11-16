#!/bin/bash
# Script per aggiornare il bot Telegram dal repository GitHub
# Uso: ./update_bot.sh

set -e  # Esce in caso di errore

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Directory del bot (modifica se necessario)
BOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BOT_DIR"

echo -e "${GREEN}🚀 Avvio aggiornamento bot...${NC}"
echo "📁 Directory: $BOT_DIR"
echo ""

# Verifica che Git sia installato
if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ Git non trovato. Installa Git prima di continuare.${NC}"
    exit 1
fi

# Verifica che Docker sia installato (se usi Docker)
if command -v docker &> /dev/null && [ -f "docker-compose.yml" ]; then
    USE_DOCKER=true
    echo -e "${GREEN}✓ Docker trovato, userò Docker Compose${NC}"
else
    USE_DOCKER=false
    echo -e "${YELLOW}⚠ Docker non trovato o docker-compose.yml assente, userò Python diretto${NC}"
fi

# Backup opzionale
read -p "Vuoi fare un backup prima dell'aggiornamento? (s/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    echo -e "${YELLOW}📦 Creazione backup...${NC}"
    BACKUP_DIR="backups/manual_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    if [ -d "data" ]; then
        cp -r data "$BACKUP_DIR/" 2>/dev/null || true
    fi
    if [ -f ".env" ]; then
        cp .env "$BACKUP_DIR/" 2>/dev/null || true
    fi
    echo -e "${GREEN}✓ Backup creato in: $BACKUP_DIR${NC}"
fi

# Ferma il bot
echo ""
echo -e "${YELLOW}🛑 Fermando il bot...${NC}"
if [ "$USE_DOCKER" = true ]; then
    docker compose down || echo "Bot già fermo o non in esecuzione"
else
    # Cerca processi Python del bot
    if pgrep -f "main.py" > /dev/null; then
        pkill -f "main.py"
        sleep 2
        echo -e "${GREEN}✓ Bot fermato${NC}"
    else
        echo -e "${YELLOW}⚠ Bot non trovato in esecuzione${NC}"
    fi
fi

# Salva modifiche locali se presenti
if [ -n "$(git status --porcelain)" ]; then
    echo ""
    echo -e "${YELLOW}⚠ Trovate modifiche locali${NC}"
    read -p "Vuoi salvare le modifiche locali? (s/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        git stash push -m "Modifiche locali prima di aggiornamento $(date +%Y%m%d_%H%M%S)"
        echo -e "${GREEN}✓ Modifiche salvate in stash${NC}"
    else
        echo -e "${YELLOW}⚠ Modifiche locali verranno sovrascritte${NC}"
        read -p "Continuare? (s/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Ss]$ ]]; then
            echo -e "${RED}❌ Aggiornamento annullato${NC}"
            exit 1
        fi
    fi
fi

# Aggiorna dal repository
echo ""
echo -e "${YELLOW}📥 Aggiornando dal repository GitHub...${NC}"
git fetch origin

# Verifica se ci sono aggiornamenti
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u})

if [ "$LOCAL" = "$REMOTE" ]; then
    echo -e "${GREEN}✓ Sei già aggiornato all'ultima versione${NC}"
else
    echo -e "${YELLOW}📥 Nuove modifiche disponibili, aggiornamento in corso...${NC}"
    git pull origin main
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Repository aggiornato con successo${NC}"
    else
        echo -e "${RED}❌ Errore durante il pull. Controlla i conflitti.${NC}"
        exit 1
    fi
fi

# Ricostruisci Docker se necessario
if [ "$USE_DOCKER" = true ]; then
    echo ""
    echo -e "${YELLOW}🔨 Ricostruendo l'immagine Docker...${NC}"
    docker compose build
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Immagine ricostruita${NC}"
    else
        echo -e "${RED}❌ Errore durante la ricostruzione${NC}"
        exit 1
    fi
fi

# Riavvia il bot
echo ""
echo -e "${YELLOW}🚀 Riavviando il bot...${NC}"
if [ "$USE_DOCKER" = true ]; then
    docker compose up -d
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Bot avviato${NC}"
    else
        echo -e "${RED}❌ Errore durante l'avvio${NC}"
        exit 1
    fi
    
    # Attendi qualche secondo
    sleep 3
    
    # Verifica che sia in esecuzione
    if docker compose ps | grep -q "Up"; then
        echo -e "${GREEN}✓ Bot in esecuzione${NC}"
    else
        echo -e "${RED}⚠ Bot potrebbe non essere avviato correttamente${NC}"
        echo "Controlla i log con: docker compose logs"
    fi
else
    # Avvia Python direttamente (in background)
    nohup python3 main.py > bot.log 2>&1 &
    sleep 2
    
    if pgrep -f "main.py" > /dev/null; then
        echo -e "${GREEN}✓ Bot avviato${NC}"
    else
        echo -e "${RED}⚠ Bot potrebbe non essere avviato correttamente${NC}"
        echo "Controlla i log con: tail -f bot.log"
    fi
fi

# Mostra informazioni finali
echo ""
echo -e "${GREEN}✅ Aggiornamento completato!${NC}"
echo ""
echo "📋 Comandi utili:"
if [ "$USE_DOCKER" = true ]; then
    echo "  - Log: docker compose logs -f"
    echo "  - Status: docker compose ps"
    echo "  - Ferma: docker compose down"
else
    echo "  - Log: tail -f bot.log"
    echo "  - Status: ps aux | grep main.py"
    echo "  - Ferma: pkill -f main.py"
fi
echo "  - Git status: git status"
echo "  - Ultimi commit: git log --oneline -5"

