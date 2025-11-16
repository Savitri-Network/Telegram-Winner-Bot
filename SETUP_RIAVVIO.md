# 🔄 Configurazione Riavvio Automatico

## Stato Attuale

Il bot ha già un sistema di riavvio automatico a più livelli:

### ✅ Già Configurato

1. **Loop di Riavvio Interno** (`entrypoint.sh`)
   - Se il bot crasha, si riavvia automaticamente dopo 5 secondi
   - Gestisce crash del codice Python

2. **Docker Restart Policy** (`restart: unless-stopped`)
   - Se Docker si riavvia, il container si riavvia automaticamente
   - Gestisce riavvii di Docker

3. **Persistenza Dati**
   - Tutti i dati sono salvati in `./data` (montato come volume)
   - Backup giornalieri in `./backups`
   - I dati sopravvivono ai riavvii

### ⚠️ Da Configurare (se il VPS crasha completamente)

Se il VPS si riavvia completamente, devi assicurarti che:

1. **Docker si avvii automaticamente al boot**
   ```bash
   sudo systemctl enable docker
   sudo systemctl start docker
   ```

2. **Il container si avvii automaticamente**
   ```bash
   # Il docker-compose.yml ha già 'restart: unless-stopped'
   # Quindi se Docker è attivo, il container si riavvia
   ```

3. **Opzionale: Servizio Systemd** (per maggiore controllo)
   ```bash
   # Copia il file di servizio
   sudo cp savitri-bot.service /etc/systemd/system/
   
   # Modifica il percorso nel file:
   # WorkingDirectory=/path/to/savitri-rewards-bot
   # (sostituisci con il percorso reale)
   
   # Abilita e avvia il servizio
   sudo systemctl daemon-reload
   sudo systemctl enable savitri-bot.service
   sudo systemctl start savitri-bot.service
   ```

## Verifica

Per verificare che tutto funzioni:

```bash
# Verifica che Docker si avvii al boot
sudo systemctl is-enabled docker

# Verifica che il container sia in esecuzione
docker ps | grep savitri

# Verifica i log
docker logs savitri-rewards-bot

# Test di crash (il bot dovrebbe riavviarsi)
docker restart savitri-rewards-bot
```

## File Importanti

- `data/` - Tutti i dati persistenti (stato bot, richieste, submissioni)
- `backups/` - Backup giornalieri automatici
- `entrypoint.sh` - Script di riavvio automatico
- `docker-compose.yml` - Configurazione Docker con restart policy

## Nota

Con la configurazione attuale:
- ✅ **Crash del bot**: Si riavvia automaticamente (entrypoint.sh)
- ✅ **Riavvio Docker**: Il container si riavvia (restart policy)
- ✅ **Riavvio VPS**: Se Docker è abilitato al boot, il container si riavvia
- ✅ **Dati**: Sempre persistenti (volume montato)


