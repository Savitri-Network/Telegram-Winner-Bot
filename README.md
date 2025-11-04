# 🤖 Savitri Rewards Bot

Bot Telegram per la gestione dei rewards del progetto Savitri Network su Zealy. Il bot permette agli utenti di registrare e modificare i propri wallet BSC (Binance Smart Chain) con un sistema di verifica tramite firme crittografiche.

## 📋 Indice

- [Panoramica](#panoramica)
- [Funzionalità](#funzionalità)
- [Installazione](#installazione)
- [Configurazione](#configurazione)
- [Utilizzo per Utenti](#utilizzo-per-utenti)
- [Utilizzo per Admin](#utilizzo-per-admin)
- [Personalizzazione](#personalizzazione)
- [Architettura](#architettura)
- [Manutenzione](#manutenzione)

---

## 🎯 Panoramica

Il **Savitri Rewards Bot** è un bot Telegram che gestisce la registrazione e la modifica dei wallet BSC per gli utenti partecipanti al contest Zealy di Savitri Network. Il bot implementa un sistema sicuro di verifica tramite:

- **Firme crittografiche** su BscScan
- **Screenshot di verifica** del profilo Zealy
- **Gestione codici WVC** (Winner Validation Codes)
- **Sistema di approvazione admin** per le richieste

---

## ✨ Funzionalità

### Per gli Utenti

- ✅ **Registrazione Username Zealy**: Impostazione del proprio username Zealy
- 📊 **Visualizzazione Status**: Controllo rank, XP, wallet registrato e deadline
- 💳 **Registrazione Wallet**: Aggiunta di un nuovo wallet BSC con verifica tramite firma
- 🔄 **Modifica Wallet**: Cambio di wallet esistente con doppia firma (vecchio e nuovo wallet)
- 📸 **Invio Proof**: Upload di screenshot del profilo Zealy come prova
- 🔑 **Gestione WVC**: Validazione di codici Winner Validation Code (se abilitati)

### Per gli Admin

- 📋 **Gestione Richieste**: Visualizzazione e gestione delle richieste di wallet
- ✅ **Approvazione/Rifiuto**: Sistema di approvazione con pulsanti inline
- 📊 **Export Dati**: Esportazione richieste e dati finali in CSV
- 📤 **Import CSV Zealy**: Caricamento dati da CSV di Zealy per indicizzazione utenti
- 🔄 **Backup Automatico**: Backup giornalieri automatici dei dati
- 📢 **Notifiche Gruppo**: Invio notifiche in un gruppo Telegram dedicato

### Sistema

- 🔄 **Auto-restart**: Riavvio automatico in caso di crash
- 💾 **Persistenza Dati**: Salvataggio stato bot e dati utente
- 🐕 **Watchdog**: Monitoraggio continuo dello stato del bot
- 📦 **Backup Giornalieri**: Backup automatici programmati
- 🔒 **Sicurezza Token**: Protezione token nei log

---

## 🚀 Installazione

### Prerequisiti

- Python 3.11+
- Docker e Docker Compose (consigliato)
- Token bot Telegram (da @BotFather)
- Account Telegram per admin

### Installazione con Docker (Consigliata)

1. **Clona o scarica il progetto**
   ```bash
   cd savitri-rewards-bot
   ```

2. **Copia il file di configurazione**
   ```bash
   cp env.example .env
   ```

3. **Configura le variabili d'ambiente** (vedi sezione [Configurazione](#configurazione))

4. **Costruisci e avvia il container**
   ```bash
   docker compose build
   docker compose up -d
   ```

5. **Verifica i log**
   ```bash
   docker compose logs -f
   ```

   Dovresti vedere: `🚀 SavitriRewardsBot is running...`

### Installazione Manuale

1. **Installa le dipendenze**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configura le variabili d'ambiente** (vedi sezione [Configurazione](#configurazione))

3. **Avvia il bot**
   ```bash
   python main.py
   ```

---

## ⚙️ Configurazione

### File `.env`

Crea un file `.env` nella root del progetto basandoti su `env.example`:

```env
# Token del bot Telegram (obbligatorio)
TELEGRAM_TOKEN=123456:ABC_defYourBotToken

# ID degli admin separati da virgola (obbligatorio)
# Trova il tuo ID con @userinfobot su Telegram
ADMIN_CHAT_IDS=111111111,222222222

# Directory per i dati (opzionale, default: data)
DATA_DIR=data

# Directory per i backup (opzionale, default: backups)
BACKUP_DIR=backups

# Orario backup giornaliero formato HH:MM (opzionale, default: 03:00)
BACKUP_TIME=03:00

# File heartbeat per watchdog (opzionale)
HEARTBEAT_FILE=data/heartbeat.txt

# Configurazione watchdog (opzionale)
WATCHDOG_MAX_FAILS=6        # Numero massimo di fallimenti prima del riavvio
WATCHDOG_INTERVAL=30         # Intervallo in secondi tra i controlli

# Percorso CSV Zealy (opzionale, default: zealy_with_wvc.csv)
# Il bot cerca anche file import_*_zealy_with_wvc.csv nella cartella data
ZEALY_CSV_PATH=zealy_with_wvc.csv

# Testo deadline per il cambio wallet (opzionale)
DEADLINE_TEXT=30-11-2025

# ID chat gruppo per notifiche (opzionale, 0 = disabilitato)
GROUP_NOTIFY_CHAT_ID=0
```

### Come Ottenere il Token Bot

1. Apri Telegram e cerca **@BotFather**
2. Invia `/newbot` e segui le istruzioni
3. Copia il token fornito e incollalo in `TELEGRAM_TOKEN`

### Come Ottenere il Tuo User ID

1. Apri Telegram e cerca **@userinfobot**
2. Invia `/start`
3. Copia il tuo ID numerico e aggiungilo a `ADMIN_CHAT_IDS`

### Formato CSV Zealy

Il CSV deve essere separato da punto e virgola (`;`) e contenere almeno queste colonne:

- `Username` (o `username`)
- `Position on Leaderboard` (o `Position`, `Position on Leadborad`)
- `XP` (o `XP on Zealy`, `Zealy XP`)
- `Binance Smart Chain Address` (o `BSC Address`, `Wallet`)
- `WVC` (opzionale, per i codici Winner Validation Code)

**Esempio CSV:**
```csv
Username;Position on Leaderboard;XP;Binance Smart Chain Address;WVC
user1;1;15000;0x1234567890123456789012345678901234567890;SAVI-ABCD-1234
user2;2;12000;0x0987654321098765432109876543210987654321;SAVI-EFGH-5678
```

---

## 👤 Utilizzo per Utenti

### Comandi Base

#### `/start`
Avvia il bot e mostra il messaggio di benvenuto con un pulsante per richiedere l'aggiornamento del wallet.

#### `/help`
Mostra la guida completa su come utilizzare il bot.

#### `/set_username <username>`
Imposta il tuo username Zealy. Deve contenere solo lettere, numeri e underscore, lunghezza 2-32 caratteri.

**Esempio:**
```
/set_username andrea_xyz
```

#### `/status`
Mostra lo stato del tuo account:
- Username Zealy
- Rank sulla leaderboard
- XP totali
- Wallet BSC registrato
- Deadline per il cambio wallet
- Codice WVC (se presente)

### Registrazione Wallet

Per registrare un nuovo wallet BSC:

1. **Invia screenshot del profilo Zealy**
   ```
   /proof
   ```
   Poi invia lo screenshot come **foto** (non come file).

2. **Avvia il flusso di registrazione**
   ```
   /add_wallet
   ```

3. **Invia il tuo wallet BSC**
   ```
   /set_wallet 0x1234567890123456789012345678901234567890
   ```

4. **Firma il messaggio su BscScan**
   - Vai su https://bscscan.com/verifiedSignatures
   - Firma il messaggio mostrato dal bot con il tuo wallet
   - Copia l'hash della firma (SHA-256)

5. **Invia la firma**
   ```
   /reg_sig 0xabcd1234...
   ```

**Messaggio da firmare:**
```
Wallet registration — Zealy: <tuo_username> — Wallet: <tuo_wallet>
I declare that I request the registration of the wallet indicated above and release Savitri Network from any liability in case of my own mistake.
```

### Modifica Wallet

Per cambiare un wallet esistente:

1. **Invia screenshot del profilo Zealy**
   ```
   /proof
   ```

2. **Avvia il flusso di modifica**
   ```
   /change_wallet
   ```

3. **Firma con il VECCHIO wallet**
   - Firma il messaggio mostrato dal bot con il tuo wallet attuale
   - Invia la firma:
   ```
   /old_sig 0xabcd1234...
   ```

4. **Invia il NUOVO wallet**
   ```
   /new_wallet 0x9876543210987654321098765432109876543210
   ```

5. **Firma con il NUOVO wallet**
   - Firma il nuovo messaggio con il nuovo wallet
   - Invia la firma:
   ```
   /new_sig 0xefgh5678...
   ```

**Messaggi da firmare:**
- **Vecchio wallet:**
  ```
  Wallet change request — Zealy: <username> — Old: <vecchio_wallet>
  ```
- **Nuovo wallet:**
  ```
  Wallet change request — Zealy: <username> — Old: <vecchio_wallet> — New: <nuovo_wallet>
  ```

### Comandi Utili

- `/proof` - Richiede l'invio di uno screenshot del profilo Zealy
- `/update_wallet` - Alternativa per richiedere l'aggiornamento del wallet (metodo semplificato)

---

## 🔧 Utilizzo per Admin

### Comandi Admin

Tutti i comandi admin iniziano con `/admin_` e sono disponibili solo agli utenti configurati in `ADMIN_CHAT_IDS`.

#### `/admin_list [all]`
Mostra le richieste di wallet in sospeso. Usa `all` per vedere tutte le richieste (incluse quelle già gestite).

**Esempio:**
```
/admin_list
/admin_list all
```

#### `/admin_export`
Esporta le ultime 100 richieste in formato CSV.

#### `/admin_export_final`
Esporta un CSV completo con tutti i dati finali degli utenti, includendo:
- Username
- Telegram ID
- Rank e XP
- Wallet originale e aggiornato
- Tipo di modifica (aggiunta/cambio)
- Firme (reg_sig, old_sig, new_sig)
- Percorsi dei proof

#### Gestione Richieste via Pulsanti

Quando un utente invia una richiesta di wallet, gli admin ricevono un messaggio con pulsanti inline:

- **✅ Approve** - Approva la richiesta
- **❌ Reject** - Rifiuta la richiesta
- **📄 Details** - Mostra i dettagli completi della richiesta

### Import Dati Zealy

#### Metodo 1: Upload Diretto
Invia un file CSV direttamente al bot. Il bot riconoscerà automaticamente i file CSV e li importerà.

#### Metodo 2: Comando
```
/admin_upload_zealy_csv
```
Poi rispondi a un messaggio che contiene un file CSV con lo stesso comando.

**Esempio:**
1. Invia il CSV al bot
2. Rispondi al messaggio con `/admin_upload_zealy_csv`

Il bot salverà il CSV in `data/import_<timestamp>_zealy_with_wvc.csv` e ricaricherà l'indice degli utenti.

### Backup

I backup vengono eseguiti automaticamente ogni giorno all'orario configurato in `BACKUP_TIME` (default: 03:00). I backup vengono salvati in `backups/backup_YYYYMMDD_HHMMSS.zip` e gli admin ricevono una notifica.

### Monitoraggio

Il bot include un sistema di watchdog che:
- Monitora lo stato del bot ogni `WATCHDOG_INTERVAL` secondi
- Se il bot fallisce `WATCHDOG_MAX_FAILS` volte consecutive, si riavvia automaticamente
- Scrive un file heartbeat in `HEARTBEAT_FILE` per monitoraggio esterno

---

## 🎨 Personalizzazione

### Modificare i Messaggi

Tutti i messaggi del bot sono definiti in `messages.py`. Puoi modificare:

- **Testi dei messaggi**: Modifica le funzioni in `messages.py`
- **Disclaimer**: Modifica la costante `DISCLAIMER`
- **Deadline**: Cambia `DEADLINE_TEXT` nel file `.env`

**Esempio di modifica:**
```python
# messages.py
def msg_status(username: str, ...):
    return wrap_with_disclaimer(
        "🧾 *Il Tuo Status*\n"  # Modifica qui
        f"• Username: `{username}`\n"
        # ...
    )
```

### Aggiungere Nuovi Comandi

1. **Crea la funzione handler** in `main.py`:
   ```python
   async def mio_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
       await update.message.reply_text("Messaggio personalizzato")
   ```

2. **Registra il comando** nella funzione `main()`:
   ```python
   application.add_handler(CommandHandler("mio_comando", mio_comando))
   ```

### Personalizzare il Flusso Wallet

Il flusso di registrazione/modifica wallet è gestito da queste funzioni in `main.py`:

- `add_wallet_cmd` - Inizio registrazione
- `change_wallet_cmd` - Inizio modifica
- `set_wallet_cmd2` - Impostazione wallet
- `reg_sig_cmd` - Firma registrazione
- `old_sig_cmd` - Firma vecchio wallet
- `new_wallet_cmd` - Impostazione nuovo wallet
- `new_sig_cmd` - Firma nuovo wallet

Puoi modificare queste funzioni per personalizzare il flusso.

### Modificare il Validatore Wallet

Il formato del wallet è validato dalla regex in `main.py`:

```python
WALLET_REGEX = re.compile(r"^0x[a-fA-F0-9]{40}$")
```

Per cambiare il formato (es. supportare altri network), modifica questa regex.

### Aggiungere Funzionalità WVC

I codici Winner Validation Code (WVC) sono supportati ma non completamente implementati nel flusso principale. Per abilitarli:

1. **Genera i codici WVC**:
   ```bash
   python generate_wvc.py --count 150 --prefix SAVI --out wvc_list.csv
   ```

2. **Importa i codici nel CSV Zealy** (colonna `WVC`)

3. **Modifica il flusso** in `main.py` per richiedere la validazione WVC prima delle azioni wallet

### Personalizzare i Backup

La funzione `make_backup_archive()` in `main.py` gestisce i backup. Puoi modificarla per:

- Includere/escludere file specifici
- Cambiare formato di compressione
- Aggiungere metadati

### Modificare le Notifiche

Le notifiche al gruppo sono gestite da `notify_group()` in `main.py`. Puoi personalizzare:

- Formato dei messaggi
- Quando inviare notifiche
- Aggiungere notifiche per nuovi eventi

### Aggiungere Nuove Funzionalità Admin

1. **Crea il comando handler**:
   ```python
   async def admin_mia_funzione(update: Update, context: ContextTypes.DEFAULT_TYPE):
       if not is_admin(update.effective_user.id):
           return
       # Logica personalizzata
       await update.message.reply_text("Risultato")
   ```

2. **Registra il comando**:
   ```python
   application.add_handler(CommandHandler("admin_mia_funzione", admin_mia_funzione))
   ```

---

## 🏗️ Architettura

### Struttura File

```
savitri-rewards-bot/
├── main.py                 # Logica principale del bot
├── messages.py             # Tutti i messaggi del bot
├── generate_wvc.py         # Generatore codici WVC
├── requirements.txt        # Dipendenze Python
├── Dockerfile              # Immagine Docker
├── docker-compose.yml      # Configurazione Docker Compose
├── entrypoint.sh           # Script di avvio con auto-restart
├── env.example             # Template file configurazione
├── .env                    # File configurazione (da creare)
├── data/                   # Dati persistenti
│   ├── bot_state          # Stato persistente del bot
│   ├── user_submissions.json  # Submissioni utenti
│   ├── wallet_update_requests.json  # Richieste wallet
│   ├── proofs/            # Screenshot utenti
│   └── heartbeat.txt       # File heartbeat watchdog
├── backups/               # Backup automatici
└── README.md              # Questa documentazione
```

### Flussi Principali

#### Flusso Registrazione Wallet
1. Utente invia `/proof` → Screenshot
2. Utente invia `/add_wallet` → Guida
3. Utente invia `/set_wallet 0x...` → Wallet salvato
4. Utente firma su BscScan
5. Utente invia `/reg_sig 0x...` → Notifica admin

#### Flusso Modifica Wallet
1. Utente invia `/proof` → Screenshot
2. Utente invia `/change_wallet` → Guida
3. Utente invia `/old_sig 0x...` → Firma vecchio wallet
4. Utente invia `/new_wallet 0x...` → Nuovo wallet
5. Utente invia `/new_sig 0x...` → Firma nuovo wallet → Notifica admin

#### Flusso Admin
1. Admin riceve notifica con pulsanti
2. Admin clicca Approve/Reject
3. Stato salvato in `wallet_update_requests.json`
4. Admin può esportare dati con `/admin_export`

### Storage Dati

- **PicklePersistence**: Salva lo stato del bot (conversazioni, user_data) in `data/bot_state`
- **JSON Files**: 
  - `user_submissions.json`: Submissioni utenti (proof, wallet, firme)
  - `wallet_update_requests.json`: Richieste wallet (metodo legacy)
- **CSV Files**: Import dati Zealy da CSV
- **File System**: Screenshot in `data/proofs/`

### Sicurezza

- **Token Protection**: I token vengono nascosti nei log
- **Validazione Input**: Wallet e username vengono validati
- **Firme Crittografiche**: Verifica tramite BscScan
- **Admin Only**: Comandi admin riservati agli ID configurati

---

## 🔧 Manutenzione

### Log

I log del bot mostrano:
- Avvio/chiusura
- Errori e eccezioni
- Operazioni importanti (import CSV, backup, etc.)

**Con Docker:**
```bash
docker compose logs -f
```

**Manualmente:**
I log vengono scritti su stdout/stderr.

### Backup Manuale

Esegui un backup manuale:
```bash
# Con Docker
docker compose exec savitri-rewards-bot python -c "from main import make_backup_archive; print(make_backup_archive())"
```

### Ripristino da Backup

1. Ferma il bot:
   ```bash
   docker compose down
   ```

2. Estrai il backup:
   ```bash
   unzip backups/backup_YYYYMMDD_HHMMSS.zip -d data_restored/
   ```

3. Sostituisci i file in `data/` con quelli ripristinati

4. Riavvia il bot:
   ```bash
   docker compose up -d
   ```

### Aggiornamento

1. **Ferma il bot:**
   ```bash
   docker compose down
   ```

2. **Aggiorna il codice:**
   ```bash
   git pull  # Se usi git
   # Oppure sostituisci i file manualmente
   ```

3. **Ricostruisci l'immagine:**
   ```bash
   docker compose build
   ```

4. **Riavvia:**
   ```bash
   docker compose up -d
   ```

### Troubleshooting

#### Bot non si avvia
- Verifica che `TELEGRAM_TOKEN` sia corretto
- Verifica che `ADMIN_CHAT_IDS` contenga almeno un ID valido
- Controlla i log per errori: `docker compose logs`

#### CSV non viene importato
- Verifica che il CSV sia separato da punto e virgola (`;`)
- Verifica che contenga le colonne necessarie (Username, Position, XP, Wallet)
- Controlla i log per errori di parsing

#### Backup non funzionano
- Verifica che `BACKUP_DIR` esista e sia scrivibile
- Verifica che `BACKUP_TIME` sia nel formato corretto (HH:MM)
- Controlla i log per errori

#### Watchdog riavvia continuamente
- Controlla i log per capire il problema
- Aumenta `WATCHDOG_MAX_FAILS` se necessario
- Verifica la connessione a Telegram

### Pulizia Dati

Per pulire i dati (attenzione: cancella tutto):

```bash
# Ferma il bot
docker compose down

# Rimuovi i dati
rm -rf data/* backups/*

# Riavvia (il bot creerà nuovi file vuoti)
docker compose up -d
```

---

## 📝 Note Aggiuntive

### Limitazioni

- Il bot supporta solo wallet BSC (formato `0x` + 40 caratteri esadecimali)
- I CSV devono essere separati da punto e virgola
- Le firme devono essere verificate manualmente dagli admin su BscScan

### Best Practices

1. **Backup Regolari**: I backup automatici sono importanti, ma considera backup manuali prima di aggiornamenti importanti
2. **Monitoraggio**: Controlla regolarmente i log per errori
3. **Test**: Testa sempre le modifiche in un ambiente di sviluppo prima di applicarle in produzione
4. **Sicurezza**: Non condividere mai il file `.env` o i token
5. **Performance**: Per grandi volumi di utenti, considera l'uso di un database invece di file JSON

### Supporto

Per problemi o domande:
1. Controlla i log del bot
2. Verifica la configurazione nel file `.env`
3. Consulta questa documentazione
4. Controlla i file di esempio nel progetto

---

## 📄 Licenza

Questo progetto è fornito "così com'è" senza garanzie. Utilizza a tuo rischio.

---

## 🙏 Ringraziamenti

Bot sviluppato per Savitri Network. Utilizza la libreria `python-telegram-bot` per l'interfaccia Telegram.

---

**Ultimo aggiornamento**: 2025

