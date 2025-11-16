#!/usr/bin/env python3
"""
Test specifico per le funzionalità di download (submissions, proofs, all).
Simula le funzioni admin_download_* senza Telegram.
"""

import sys
import json
import zipfile
import tempfile
from pathlib import Path
from io import BytesIO

sys.path.insert(0, str(Path(__file__).parent))

from main import (
    SUBMISSIONS_FILE, DATA_DIR, load_submissions,
    admin_download_submissions, admin_download_proofs, admin_download_all
)

def test_submissions_file_download():
    """Test: Verifica che il file submissions possa essere letto e compresso"""
    print("\n[TEST] Download Submissions File")
    print("="*60)
    
    try:
        if not SUBMISSIONS_FILE.exists():
            print("[INFO] File non trovato, creando file di test...")
            test_data = {
                "test_123": {
                    "tg_id": 123456789,
                    "username": "test_user",
                    "reg_wallet": "0x1234567890123456789012345678901234567890",
                    "proofs": ["data/proofs/test.jpg"]
                }
            }
            SUBMISSIONS_FILE.write_text(
                json.dumps(test_data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        
        # Leggi il file
        with open(SUBMISSIONS_FILE, "rb") as f:
            data = f.read()
        
        print(f"[OK] File letto: {len(data)} bytes")
        
        # Verifica che sia JSON valido
        subs = load_submissions()
        print(f"[OK] JSON valido con {len(subs)} entries")
        
        # Simula creazione BytesIO per invio
        data_io = BytesIO(data)
        data_io.name = "user_submissions.json"
        
        print(f"[OK] BytesIO creato: {len(data_io.getvalue())} bytes")
        print("[OK] Test download submissions: PASS")
        return True
        
    except Exception as e:
        print(f"[ERROR] Errore: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_proofs_zip_creation():
    """Test: Verifica creazione ZIP degli screenshot"""
    print("\n[TEST] Creazione ZIP Proofs")
    print("="*60)
    
    try:
        proofs_dir = DATA_DIR / "proofs"
        
        if not proofs_dir.exists():
            print("[INFO] Directory proofs non trovata")
            return True  # Non è un errore
        
        proof_files = list(proofs_dir.glob("*.jpg"))
        
        if not proof_files:
            print("[INFO] Nessuno screenshot trovato (normale)")
            return True
        
        print(f"[INFO] Trovati {len(proof_files)} file screenshot")
        
        # Crea ZIP temporaneo
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_zip:
            zip_path = Path(tmp_zip.name)
        
        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                proof_count = 0
                for proof_file in proof_files:
                    try:
                        zf.write(proof_file, arcname=proof_file.name)
                        proof_count += 1
                    except Exception as e:
                        print(f"[WARN] Errore aggiungendo {proof_file.name}: {e}")
            
            print(f"[OK] ZIP creato: {proof_count} file")
            print(f"[OK] Dimensione ZIP: {zip_path.stat().st_size} bytes")
            
            # Verifica contenuto ZIP
            with zipfile.ZipFile(zip_path, "r") as zf:
                file_list = zf.namelist()
                print(f"[OK] File nello ZIP: {len(file_list)}")
            
            # Simula BytesIO per invio
            with open(zip_path, "rb") as f:
                data_io = BytesIO(f.read())
                data_io.name = "proofs_export.zip"
            
            print(f"[OK] BytesIO creato: {len(data_io.getvalue())} bytes")
            print("[OK] Test creazione ZIP proofs: PASS")
            return True
            
        finally:
            # Pulisci file temporaneo
            if zip_path.exists():
                zip_path.unlink()
        
    except Exception as e:
        print(f"[ERROR] Errore: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_complete_export_zip():
    """Test: Verifica creazione ZIP completo (submissions + proofs)"""
    print("\n[TEST] Creazione ZIP Completo")
    print("="*60)
    
    try:
        # Crea ZIP temporaneo
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_zip:
            zip_path = Path(tmp_zip.name)
        
        try:
            subs_count = 0
            proof_count = 0
            
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # Aggiungi submissions JSON
                if SUBMISSIONS_FILE.exists():
                    zf.write(SUBMISSIONS_FILE, arcname="user_submissions.json")
                    subs = load_submissions()
                    subs_count = len(subs)
                    print(f"[OK] Aggiunto user_submissions.json ({subs_count} entries)")
                
                # Aggiungi proofs
                proofs_dir = DATA_DIR / "proofs"
                if proofs_dir.exists():
                    for proof_file in proofs_dir.glob("*.jpg"):
                        try:
                            zf.write(proof_file, arcname=f"proofs/{proof_file.name}")
                            proof_count += 1
                        except Exception as e:
                            print(f"[WARN] Errore aggiungendo {proof_file.name}: {e}")
            
            print(f"[OK] ZIP completo creato")
            print(f"[OK] Submission: {subs_count}, Screenshot: {proof_count}")
            print(f"[OK] Dimensione ZIP: {zip_path.stat().st_size} bytes")
            
            # Verifica struttura ZIP
            with zipfile.ZipFile(zip_path, "r") as zf:
                file_list = zf.namelist()
                print(f"[OK] File totali nello ZIP: {len(file_list)}")
                
                # Verifica che ci sia il JSON
                if "user_submissions.json" in file_list:
                    print("[OK] user_submissions.json presente nello ZIP")
                
                # Verifica che ci siano proofs
                proofs_in_zip = [f for f in file_list if f.startswith("proofs/")]
                print(f"[OK] Screenshot nello ZIP: {len(proofs_in_zip)}")
            
            # Simula BytesIO per invio
            with open(zip_path, "rb") as f:
                data_io = BytesIO(f.read())
                data_io.name = "user_data_export.zip"
            
            print(f"[OK] BytesIO creato: {len(data_io.getvalue())} bytes")
            print("[OK] Test ZIP completo: PASS")
            return True
            
        finally:
            # Pulisci file temporaneo
            if zip_path.exists():
                zip_path.unlink()
        
    except Exception as e:
        print(f"[ERROR] Errore: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_all_download_tests():
    """Esegue tutti i test di download"""
    print("\n" + "="*60)
    print("[TEST] TEST FUNZIONALITA DOWNLOAD")
    print("="*60)
    
    tests = [
        ("Download Submissions", test_submissions_file_download),
        ("Creazione ZIP Proofs", test_proofs_zip_creation),
        ("ZIP Completo", test_complete_export_zip),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"[ERROR] Test '{name}' fallito: {e}")
            results.append((name, False))
    
    # Riepilogo
    print("\n" + "="*60)
    print("[RIEPILOGO] RIEPILOGO TEST DOWNLOAD")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} - {name}")
    
    print(f"\nTotale: {passed}/{total} test passati")
    
    if passed == total:
        print("[OK] Tutti i test di download sono passati!")
        return 0
    else:
        print(f"[ERROR] {total - passed} test falliti")
        return 1

if __name__ == "__main__":
    try:
        exit_code = run_all_download_tests()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n[INFO] Test interrotti dall'utente")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Errore fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

