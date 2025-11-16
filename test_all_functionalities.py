#!/usr/bin/env python3
"""
Script di test completo per tutte le funzionalità del bot.
Testa: CSV import, download submissions, download proofs, gestione dati.
"""

import sys
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Aggiungi la directory corrente al path
sys.path.insert(0, str(Path(__file__).parent))

# Importa le funzioni necessarie
from main import (
    load_zealy_index, DATA_DIR, ZEALY_INDEX, SUBMISSIONS_FILE,
    load_submissions, save_submissions, _discover_latest_zealy_csv
)

def print_test(name):
    """Stampa l'inizio di un test"""
    print(f"\n{'='*60}")
    print(f"[TEST] {name}")
    print(f"{'='*60}")

def print_success(msg):
    """Stampa un messaggio di successo"""
    print(f"[OK] {msg}")

def print_error(msg):
    """Stampa un messaggio di errore"""
    print(f"[ERROR] {msg}")

def print_info(msg):
    """Stampa un messaggio informativo"""
    print(f"[INFO] {msg}")

def test_zealy_index_loading():
    """Test 1: Caricamento indice Zealy"""
    print_test("Caricamento Indice Zealy")
    
    try:
        success, message, count = load_zealy_index()
        
        if success:
            print_success(f"Indice caricato: {count} utenti")
            print_info(f"Messaggio: {message}")
            
            # Verifica che l'indice non sia vuoto (se ci sono CSV)
            csv_path = _discover_latest_zealy_csv()
            if csv_path.exists():
                if count > 0:
                    print_success(f"Trovati {count} utenti nell'indice")
                    # Mostra un esempio
                    if ZEALY_INDEX:
                        example_user = list(ZEALY_INDEX.items())[0]
                        print_info(f"Esempio utente: {example_user[0]}")
                        print_info(f"  - Rank: {example_user[1].get('rank', 'N/A')}")
                        print_info(f"  - XP: {example_user[1].get('xp', 'N/A')}")
                        print_info(f"  - Wallet: {example_user[1].get('wallet', 'N/A')[:20]}..." if example_user[1].get('wallet') else "  - Wallet: N/A")
                else:
                    print_error("CSV trovato ma nessun utente indicizzato")
            else:
                print_info("Nessun CSV trovato (normale se non ancora importato)")
            
            return True
        else:
            print_error(f"Caricamento fallito: {message}")
            return False
            
    except Exception as e:
        print_error(f"Eccezione durante il test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_submissions_loading():
    """Test 2: Caricamento e salvataggio submissions"""
    print_test("Gestione Submissions")
    
    try:
        # Carica submissions esistenti
        subs = load_submissions()
        print_info(f"Submissions caricate: {len(subs)}")
        
        # Test salvataggio (con dati di test)
        test_data = {
            "test_user_123": {
                "tg_id": 123456789,
                "username": "test_user",
                "reg_wallet": "0x1234567890123456789012345678901234567890",
                "reg_sig": "0xtest_signature",
                "proofs": ["data/proofs/test_123.jpg"]
            }
        }
        
        # Salva dati di test
        original_subs = subs.copy()
        save_submissions(test_data)
        
        # Verifica che sia stato salvato
        loaded = load_submissions()
        if "test_user_123" in loaded:
            print_success("Salvataggio submissions funziona correttamente")
        else:
            print_error("Salvataggio non funziona")
            return False
        
        # Ripristina dati originali
        save_submissions(original_subs)
        print_success("Ripristino dati originali completato")
        
        return True
        
    except Exception as e:
        print_error(f"Eccezione durante il test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_submissions_file_exists():
    """Test 3: Verifica esistenza file submissions"""
    print_test("Verifica File Submissions")
    
    try:
        if SUBMISSIONS_FILE.exists():
            print_success(f"File trovato: {SUBMISSIONS_FILE}")
            
            # Verifica che sia un JSON valido
            try:
                with open(SUBMISSIONS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print_success(f"JSON valido con {len(data)} entries")
                
                # Mostra statistiche
                if data:
                    total_proofs = sum(len(rec.get('proofs', [])) for rec in data.values())
                    wallets_reg = sum(1 for rec in data.values() if rec.get('reg_wallet'))
                    wallets_changed = sum(1 for rec in data.values() if rec.get('new_wallet'))
                    
                    print_info(f"  - Totale utenti: {len(data)}")
                    print_info(f"  - Totale proof: {total_proofs}")
                    print_info(f"  - Wallet registrati: {wallets_reg}")
                    print_info(f"  - Wallet modificati: {wallets_changed}")
                
                return True
            except json.JSONDecodeError as e:
                print_error(f"JSON non valido: {e}")
                return False
        else:
            print_info("File non trovato (normale se non ci sono submission ancora)")
            return True  # Non è un errore se il file non esiste
            
    except Exception as e:
        print_error(f"Eccezione durante il test: {e}")
        return False

def test_proofs_directory():
    """Test 4: Verifica directory proofs"""
    print_test("Verifica Directory Proofs")
    
    try:
        proofs_dir = DATA_DIR / "proofs"
        
        if proofs_dir.exists():
            print_success(f"Directory trovata: {proofs_dir}")
            
            # Conta i file
            proof_files = list(proofs_dir.glob("*.jpg"))
            print_info(f"File screenshot trovati: {len(proof_files)}")
            
            if proof_files:
                # Mostra alcuni esempi
                print_info("Esempi di file:")
                for f in proof_files[:3]:
                    size_kb = f.stat().st_size / 1024
                    print_info(f"  - {f.name} ({size_kb:.1f} KB)")
            
            return True
        else:
            print_info("Directory non trovata (normale se non ci sono proof ancora)")
            # Crea la directory per test
            proofs_dir.mkdir(parents=True, exist_ok=True)
            print_success("Directory creata per test")
            return True
            
    except Exception as e:
        print_error(f"Eccezione durante il test: {e}")
        return False

def test_data_directory_structure():
    """Test 5: Verifica struttura directory dati"""
    print_test("Verifica Struttura Directory Dati")
    
    try:
        required_dirs = [
            DATA_DIR,
            DATA_DIR / "proofs",
        ]
        
        optional_files = [
            SUBMISSIONS_FILE,
            DATA_DIR / "wallet_update_requests.json",
            DATA_DIR / "bot_state",
        ]
        
        print_info(f"Directory dati: {DATA_DIR}")
        print_info(f"Directory esiste: {DATA_DIR.exists()}")
        
        # Verifica directory richieste
        all_ok = True
        for dir_path in required_dirs:
            if dir_path.exists():
                print_success(f"[OK] {dir_path.name}")
            else:
                print_info(f"[WARN] {dir_path.name} non trovato (verrà creato automaticamente)")
        
        # Verifica file opzionali
        print_info("\nFile opzionali:")
        for file_path in optional_files:
            if file_path.exists():
                size = file_path.stat().st_size
                print_success(f"[OK] {file_path.name} ({size} bytes)")
            else:
                print_info(f"[WARN] {file_path.name} non trovato")
        
        return True
        
    except Exception as e:
        print_error(f"Eccezione durante il test: {e}")
        return False

def test_csv_discovery():
    """Test 6: Verifica scoperta file CSV"""
    print_test("Scoperta File CSV")
    
    try:
        csv_path = _discover_latest_zealy_csv()
        print_info(f"Percorso CSV trovato: {csv_path}")
        
        if csv_path.exists():
            print_success("File CSV trovato")
            size = csv_path.stat().st_size
            modified = datetime.fromtimestamp(csv_path.stat().st_mtime)
            print_info(f"  - Dimensione: {size} bytes")
            print_info(f"  - Modificato: {modified}")
        else:
            print_info("File CSV non trovato (normale se non ancora importato)")
            
            # Verifica se ci sono file import_* nella directory data
            import_files = list(DATA_DIR.glob("import_*_zealy_with_wvc.csv"))
            if import_files:
                print_info(f"Trovati {len(import_files)} file import nella directory data:")
                for f in sorted(import_files, key=lambda x: x.stat().st_mtime, reverse=True)[:3]:
                    print_info(f"  - {f.name}")
        
        return True
        
    except Exception as e:
        print_error(f"Eccezione durante il test: {e}")
        return False

def test_zealy_index_structure():
    """Test 7: Verifica struttura indice Zealy"""
    print_test("Struttura Indice Zealy")
    
    try:
        if not ZEALY_INDEX:
            print_info("Indice vuoto (normale se non ci sono CSV)")
            return True
        
        print_success(f"Indice contiene {len(ZEALY_INDEX)} utenti")
        
        # Verifica struttura dati
        sample_user = list(ZEALY_INDEX.items())[0]
        username, data = sample_user
        
        print_info(f"Esempio struttura per utente '{username}':")
        expected_keys = ['rank', 'xp', 'wallet', 'wvc', 'wvc_used']
        
        for key in expected_keys:
            value = data.get(key)
            if value is not None:
                print_success(f"  [OK] {key}: {value}")
            else:
                print_info(f"  - {key}: None (opzionale)")
        
        # Statistiche
        users_with_wallet = sum(1 for d in ZEALY_INDEX.values() if d.get('wallet'))
        users_with_wvc = sum(1 for d in ZEALY_INDEX.values() if d.get('wvc'))
        
        print_info(f"\nStatistiche:")
        print_info(f"  - Utenti con wallet: {users_with_wallet}")
        print_info(f"  - Utenti con WVC: {users_with_wvc}")
        
        return True
        
    except Exception as e:
        print_error(f"Eccezione durante il test: {e}")
        return False

def test_submissions_structure():
    """Test 8: Verifica struttura submissions"""
    print_test("Struttura Submissions")
    
    try:
        subs = load_submissions()
        
        if not subs:
            print_info("Nessuna submission trovata (normale se non ci sono ancora)")
            return True
        
        print_success(f"Trovate {len(subs)} submission")
        
        # Analizza struttura
        sample = list(subs.items())[0]
        tg_id, data = sample
        
        print_info(f"Esempio struttura per TG ID {tg_id}:")
        expected_keys = ['tg_id', 'username', 'reg_wallet', 'reg_sig', 'old_sig', 'new_sig', 'new_wallet', 'proofs']
        
        for key in expected_keys:
            value = data.get(key)
            if value is not None:
                if key == 'proofs':
                    print_success(f"  [OK] {key}: {len(value)} file")
                elif key == 'reg_wallet' or key == 'new_wallet':
                    print_success(f"  [OK] {key}: {str(value)[:20]}...")
                else:
                    print_success(f"  [OK] {key}: {value}")
            else:
                print_info(f"  - {key}: None")
        
        return True
        
    except Exception as e:
        print_error(f"Eccezione durante il test: {e}")
        return False

def run_all_tests():
    """Esegue tutti i test"""
    print("\n" + "="*60)
    print("[TEST] TEST COMPLETO FUNZIONALITA BOT")
    print("="*60)
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Directory dati: {DATA_DIR}")
    print(f"Directory esiste: {DATA_DIR.exists()}")
    
    tests = [
        ("Struttura Directory Dati", test_data_directory_structure),
        ("Scoperta File CSV", test_csv_discovery),
        ("Caricamento Indice Zealy", test_zealy_index_loading),
        ("Struttura Indice Zealy", test_zealy_index_structure),
        ("Gestione Submissions", test_submissions_loading),
        ("File Submissions", test_submissions_file_exists),
        ("Struttura Submissions", test_submissions_structure),
        ("Directory Proofs", test_proofs_directory),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print_error(f"Test '{name}' fallito con eccezione: {e}")
            results.append((name, False))
    
    # Riepilogo
    print("\n" + "="*60)
    print("[RIEPILOGO] RIEPILOGO TEST")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} - {name}")
    
    print(f"\nTotale: {passed}/{total} test passati")
    
    if passed == total:
        print_success("Tutti i test sono passati!")
        return 0
    else:
        print_error(f"{total - passed} test falliti")
        return 1

if __name__ == "__main__":
    try:
        exit_code = run_all_tests()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n[INFO] Test interrotti dall'utente")
        sys.exit(1)
    except Exception as e:
        print_error(f"Errore fatale durante i test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

