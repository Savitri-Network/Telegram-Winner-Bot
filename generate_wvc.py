#!/usr/bin/env python3
"""
generate_wvc.py

Generates a list of Winner Validation Codes (WVC) and writes them to CSV.
Optional: generates QR code images for each WVC and packs them in a ZIP.

Usage:
    python generate_wvc.py --count 150 --prefix SAVI --segments 4 --seglen 4 --expiry-days 30 --out wvc_list.csv --qrcode

Dependencies:
    pip install python-dotenv qrcode[pil] pillow
( qrcode only required if you use --qrcode )
"""

import csv
import secrets
import string
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import zipfile
import os

# Optional imports for QR generation
try:
    import qrcode
    QR_AVAILABLE = True
except Exception:
    QR_AVAILABLE = False

ALPHABET = string.ascii_uppercase + string.digits

def random_segment(seglen: int) -> str:
    return ''.join(secrets.choice(ALPHABET) for _ in range(seglen))

def make_code(prefix: str, segments: int, seglen: int) -> str:
    parts = [prefix] if prefix else []
    for _ in range(segments):
        parts.append(random_segment(seglen))
    return '-'.join(parts)

def generate_codes(count: int, prefix: str, segments: int, seglen: int) -> list:
    codes = set()
    attempts = 0
    while len(codes) < count:
        c = make_code(prefix, segments, seglen)
        attempts += 1
        if c not in codes:
            codes.add(c)
        if attempts > count * 20:
            # safety to avoid infinite loop (extremely unlikely)
            raise RuntimeError("Too many collisions generating codes; try longer seglen")
    return list(codes)

def write_csv(out_path: Path, codes: list, expiry_days: int):
    header = ["wvc", "assigned_to", "created_at", "expires_at", "used"]
    now = datetime.utcnow()
    expires = (now + timedelta(days=expiry_days)).isoformat() if expiry_days and expiry_days > 0 else ""
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for code in codes:
            writer.writerow([code, "", now.isoformat(), expires, "false"])

def generate_qrcodes(codes: list, out_dir: Path):
    if not QR_AVAILABLE:
        raise RuntimeError("qrcode library not available. Install with: pip install qrcode[pil]")
    out_dir.mkdir(parents=True, exist_ok=True)
    for code in codes:
        img = qrcode.make(code)
        fname = out_dir / f"{code}.png"
        img.save(fname)

def zip_qrcodes(qr_dir: Path, zip_path: Path):
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(qr_dir.iterdir()):
            zf.write(p, arcname=p.name)

def main():
    parser = argparse.ArgumentParser(description="Generate Winner Validation Codes (WVC).")
    parser.add_argument("--count", type=int, default=150, help="Number of codes to generate.")
    parser.add_argument("--prefix", type=str, default="SAVI", help="Prefix for codes (e.g. SAVI)")
    parser.add_argument("--segments", type=int, default=3, help="Number of random segments after prefix")
    parser.add_argument("--seglen", type=int, default=4, help="Length of each random segment")
    parser.add_argument("--expiry-days", type=int, default=0, help="Expiry in days (0 = no expiry)")
    parser.add_argument("--out", type=str, default="wvc_list.csv", help="Output CSV filename")
    parser.add_argument("--qrcode", action="store_true", help="Also generate QR codes and zip them (requires qrcode[pil])")
    parser.add_argument("--qr-dir", type=str, default="wvc_qr", help="Directory for QR images (if --qrcode)")
    parser.add_argument("--zip", type=str, default="wvc_qr.zip", help="Output zip filename for QR images (if --qrcode)")

    args = parser.parse_args()

    out_path = Path(args.out)
    codes = generate_codes(args.count, args.prefix, args.segments, args.seglen)
    write_csv(out_path, codes, args.expiry_days)
    print(f"[OK] Generated {len(codes)} codes -> {out_path.resolve()}")

    if args.qrcode:
        qr_dir = Path(args.qr_dir)
        print("[..] Generating QR codes (this may take a few seconds)...")
        generate_qrcodes(codes, qr_dir)
        zip_path = Path(args.zip)
        zip_qrcodes(qr_dir, zip_path)
        print(f"[OK] QR images in {qr_dir.resolve()} zipped -> {zip_path.resolve()}")

if __name__ == "__main__":
    main()
