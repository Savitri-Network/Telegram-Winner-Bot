#!/usr/bin/env python3
"""
Script di test per verificare la funzionalità di import CSV.
Questo script simula il processo di caricamento CSV senza Telegram.
"""

import sys
from pathlib import Path

# Aggiungi la directory corrente al path per importare main
sys.path.insert(0, str(Path(__file__).parent))

# Importa le funzioni necessarie
from main import load_zealy_index, DATA_DIR, ZEALY_INDEX

def test_load_zealy_index():
    """Test della funzione load_zealy_index"""
    print("[TEST] Test caricamento indice Zealy...")
    print(f"[INFO] Directory dati: {DATA_DIR}")
    print(f"[INFO] Directory esiste: {DATA_DIR.exists()}\n")
    
    # Lista file CSV disponibili
    csv_files = list(DATA_DIR.glob("import_*_zealy_with_wvc.csv"))
    if csv_files:
        print(f"[INFO] File CSV trovati: {len(csv_files)}")
        for f in sorted(csv_files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
            print(f"   - {f.name} (modificato: {f.stat().st_mtime})")
    else:
        print("[WARN] Nessun file CSV import_*_zealy_with_wvc.csv trovato")
    
    print("\n[INFO] Caricamento indice...")
    success, message, total = load_zealy_index()
    
    if success:
        print(f"[OK] Successo!")
        print(f"   Messaggio: {message}")
        print(f"   Utenti indicizzati: {total}")
        print(f"   Dimensione indice: {len(ZEALY_INDEX)}")
        
        # Mostra alcuni esempi
        if ZEALY_INDEX:
            print("\n[INFO] Esempi di utenti indicizzati:")
            for i, (username, data) in enumerate(list(ZEALY_INDEX.items())[:3]):
                print(f"   {i+1}. {username}:")
                print(f"      - Rank: {data.get('rank', 'N/A')}")
                print(f"      - XP: {data.get('xp', 'N/A')}")
                print(f"      - Wallet: {data.get('wallet', 'N/A')[:20]}..." if data.get('wallet') else "      - Wallet: N/A")
    else:
        print(f"[ERROR] Errore!")
        print(f"   Messaggio: {message}")
        print(f"   Utenti indicizzati: {total}")
    
    return success

if __name__ == "__main__":
    try:
        success = test_load_zealy_index()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"[ERROR] Errore durante il test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

