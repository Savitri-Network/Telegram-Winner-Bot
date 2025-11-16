# 🚀 Guida Aggiornamento Bot su VPS

Questa guida spiega come aggiornare il bot Telegram sul server VPS dopo aver fatto push delle modifiche su GitHub.

## 📋 Prerequisiti

- Accesso SSH al server VPS
- Git installato sul VPS
- Repository già clonato (o procedura per clonarlo)

---

## 🔄 Metodo 1: Aggiornamento con Repository Esistente

Se il repository è già presente sul VPS:

### Passo 1: Connettiti al VPS via SSH

```bash
ssh utente@indirizzo-vps
```

### Passo 2: Vai nella directory del progetto

```bash
cd /path/to/savitri-rewards-bot
# oppure
cd ~/savitri-rewards-bot
```

### Passo 3: Ferma il bot (se in esecuzione)

**Se usi Docker:**
```bash
cd /path/to/savitri-rewards-bot
docker compose down
```

**Se esegui direttamente Python:**
```bash
# Trova il processo
ps aux | grep main.py
# Ferma il processo (sostituisci PID con il numero del processo)
kill PID
```

### Passo 4: Salva eventuali modifiche locali (opzionale)

```bash
# Verifica se ci sono modifiche locali
git status

# Se ci sono modifiche che vuoi salvare
git stash

# Oppure committa le modifiche locali
git add .
git commit -m "Modifiche locali prima dell'aggiornamento"
```

### Passo 5: Aggiorna dal repository GitHub

```bash
# Scarica le ultime modifiche
git fetch origin

# Aggiorna il branch main
git pull origin main

# Oppure più semplice (se sei già sul branch main)
git pull
```

### Passo 6: Ricostruisci e riavvia (se usi Docker)

```bash
# Ricostruisci l'immagine Docker con le nuove modifiche
docker compose build

# Riavvia il bot
docker compose up -d

# Verifica che sia partito correttamente
docker compose logs -f
```

### Passo 7: Verifica che tutto funzioni

```bash
# Controlla i log
docker compose logs -f

# Verifica che il bot risponda
# (testa inviando un comando al bot su Telegram)
```

---

## 🆕 Metodo 2: Clonare il Repository per la Prima Volta

Se il repository non esiste ancora sul VPS:

### Passo 1: Connettiti al VPS

```bash
ssh utente@indirizzo-vps
```

### Passo 2: Installa Git (se non presente)

**Su Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install git -y
```

**Su CentOS/RHEL:**
```bash
sudo yum install git -y
```

### Passo 3: Clona il repository

```bash
# Vai nella directory dove vuoi clonare (es. home)
cd ~

# Clona il repository
git clone https://github.com/Savitri-Network/Telegram-Winner-Bot.git savitri-rewards-bot

# Oppure se vuoi una directory con nome diverso
git clone https://github.com/Savitri-Network/Telegram-Winner-Bot.git
```

### Passo 4: Configura il bot

```bash
cd savitri-rewards-bot

# Copia il file di esempio
cp env.example .env

# Modifica il file .env con le tue credenziali
nano .env
# oppure
vi .env
```

### Passo 5: Avvia il bot

**Con Docker:**
```bash
docker compose up -d
```

---

## 🔧 Script di Aggiornamento Automatico

Puoi creare uno script per automatizzare l'aggiornamento:

### Crea lo script `update_bot.sh`:

```bash
#!/bin/bash
# Script per aggiornare il bot dal repository GitHub

set -e  # Esce in caso di errore

BOT_DIR="/path/to/savitri-rewards-bot"
cd "$BOT_DIR"

echo "🛑 Fermando il bot..."
docker compose down

echo "📥 Aggiornando dal repository..."
git fetch origin
git pull origin main

echo "🔨 Ricostruendo l'immagine Docker..."
docker compose build

echo "🚀 Riavviando il bot..."
docker compose up -d

echo "✅ Aggiornamento completato!"
echo "📋 Controlla i log con: docker compose logs -f"
```

### Rendi lo script eseguibile:

```bash
chmod +x update_bot.sh
```

### Esegui lo script:

```bash
./update_bot.sh
```

---

## 🔄 Aggiornamento con Zero Downtime (Avanzato)

Per aggiornare senza interrompere il servizio:

### Metodo con Docker Swarm o Kubernetes

```bash
# Con Docker Swarm
docker service update --image nuova-immagine savitri-bot

# Oppure con rolling update manuale
docker compose up -d --scale savitri-rewards-bot=2 --no-recreate
# Attendi che il nuovo container sia pronto
docker compose up -d --scale savitri-rewards-bot=1
```

### Metodo con Blue-Green Deployment

1. Clona il repository in una nuova directory
2. Configura e avvia il nuovo bot
3. Verifica che funzioni
4. Ferma il vecchio bot
5. Rimuovi la vecchia directory

---

## ⚠️ Risoluzione Problemi

### Errore: "Your local changes would be overwritten"

```bash
# Salva le modifiche locali
git stash

# Oppure committa le modifiche
git add .
git commit -m "Modifiche locali"

# Poi fai pull
git pull
```

### Errore: "Permission denied"

```bash
# Verifica i permessi della directory
ls -la

# Se necessario, cambia i permessi
chmod -R 755 /path/to/savitri-rewards-bot
```

### Il bot non si avvia dopo l'aggiornamento

```bash
# Controlla i log per errori
docker compose logs

# Verifica la configurazione
cat .env

# Verifica che le dipendenze siano aggiornate
docker compose build --no-cache
```

### Conflitti di merge

```bash
# Se ci sono conflitti durante il pull
git status

# Risolvi i conflitti manualmente
# Poi:
git add .
git commit -m "Risolti conflitti di merge"
```

---

## 📝 Checklist Aggiornamento

- [ ] Backup dei dati (`data/` e `backups/`)
- [ ] Verifica che il bot sia fermo
- [ ] Pull delle modifiche da GitHub
- [ ] Verifica che non ci siano conflitti
- [ ] Ricostruzione immagine Docker (se necessario)
- [ ] Riavvio del bot
- [ ] Verifica log per errori
- [ ] Test funzionalità del bot

---

## 🔐 Sicurezza

### Usa SSH Keys invece di password

```bash
# Sul tuo computer locale
ssh-keygen -t rsa -b 4096

# Copia la chiave pubblica sul VPS
ssh-copy-id utente@indirizzo-vps
```

### Proteggi il file .env

```bash
# Assicurati che .env non sia tracciato da Git
# (dovrebbe già essere nel .gitignore)

# Imposta permessi restrittivi
chmod 600 .env
```

---

## 📚 Comandi Utili

```bash
# Verifica lo stato del repository
git status

# Vedi le ultime modifiche
git log --oneline -10

# Vedi le differenze con il remoto
git diff origin/main

# Ripristina a una versione precedente (se necessario)
git checkout <commit-hash>

# Rimuovi file non tracciati (attenzione!)
git clean -fd
```

---

## 🆘 Supporto

Se hai problemi durante l'aggiornamento:

1. Controlla i log: `docker compose logs -f`
2. Verifica la configurazione: `cat .env`
3. Controlla lo stato Git: `git status`
4. Verifica la connessione: `ping github.com`

---

**Ultimo aggiornamento**: 2025

