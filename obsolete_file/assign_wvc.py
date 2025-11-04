#!/usr/bin/env python3
"""
assign_wvc.py  —  Merge Zealy winners CSV with WVC CSV (row-by-row) with delimiter auto-detection.

Usage:
  python assign_wvc.py --zealy zealy_winners.csv --wvc wvc_list.csv --out zealy_with_wvc.csv --verbose
"""

import csv
import sys
from pathlib import Path
import argparse

def sniff_csv(path: Path):
    """Open a CSV, sniff delimiter, return (rows:list[dict], fieldnames:list[str], delimiter:str)."""
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        # Tenta di indovinare il delimitatore tra ; , \t |
        delimiters_to_try = [",", ";", "\t", "|"]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters="".join(delimiters_to_try))
            delimiter = dialect.delimiter
        except Exception:
            # fallback: se l'header contiene molti ';', usa ';', altrimenti ','
            header_line = sample.splitlines()[0] if sample else ""
            delimiter = ";" if header_line.count(";") >= header_line.count(",") else ","
        reader = csv.DictReader(f, delimiter=delimiter)
        rows = list(reader)
        return rows, (reader.fieldnames or []), delimiter

def print_preview(title: str, rows, max_rows=3):
    print(f"\n--- {title} (preview up to {max_rows}) ---")
    if not rows:
        print("(no rows)")
        return
    for i, r in enumerate(rows[:max_rows], 1):
        print(f"{i:02d}: {r}")
    print(f"Total rows: {len(rows)}")

def main():
    ap = argparse.ArgumentParser(description="Assign WVC codes to Zealy winners (row-by-row) with delimiter auto-detection.")
    ap.add_argument("--zealy", required=True, help="Zealy winners CSV path (delimiter auto-detected)")
    ap.add_argument("--wvc", required=True, help="WVC CSV path (must have 'wvc' column; delimiter auto-detected)")
    ap.add_argument("--out", default="zealy_with_wvc.csv", help="Output CSV path")
    ap.add_argument("--verbose", action="store_true", help="Verbose logs")
    args = ap.parse_args()

    zealy_path = Path(args.zealy)
    wvc_path = Path(args.wvc)
    out_path = Path(args.out)

    if not zealy_path.exists():
        print(f"ERROR: Zealy file not found: {zealy_path}")
        sys.exit(1)
    if not wvc_path.exists():
        print(f"ERROR: WVC file not found: {wvc_path}")
        sys.exit(1)

    # Load Zealy with detected delimiter
    zealy_rows, zealy_headers, zealy_delim = sniff_csv(zealy_path)
    if args.verbose:
        print(f"Detected Zealy delimiter: '{zealy_delim}'")
        print(f"Zealy headers: {zealy_headers}")
        print_preview("Zealy", zealy_rows)

    if not zealy_rows:
        print("ERROR: Zealy CSV has no data rows.")
        sys.exit(1)

    # Load WVC with detected delimiter
    wvc_rows, wvc_headers, wvc_delim = sniff_csv(wvc_path)
    if args.verbose:
        print(f"\nDetected WVC delimiter: '{wvc_delim}'")
        print(f"WVC headers: {wvc_headers}")
        print_preview("WVC", wvc_rows)

    if not wvc_rows:
        print("ERROR: WVC CSV has no data rows.")
        sys.exit(1)

    # Find 'wvc' column (case-insensitive)
    lower_map = {h.lower(): h for h in (wvc_headers or [])}
    wvc_col = lower_map.get("wvc")
    if not wvc_col:
        print("ERROR: WVC CSV must contain a 'wvc' column (case-insensitive).")
        print(f"Headers found: {wvc_headers}")
        sys.exit(1)

    # Extract WVC codes list (in order)
    wvcs = [ (row.get(wvc_col) or "").strip() for row in wvc_rows if (row.get(wvc_col) or "").strip() ]
    if len(zealy_rows) > len(wvcs):
        print(f"ERROR: Winners ({len(zealy_rows)}) > WVC available ({len(wvcs)}). Generate more codes.")
        sys.exit(1)

    # Merge row-by-row
    merged = []
    for i, z in enumerate(zealy_rows):
        out_row = dict(z)
        out_row["WVC"] = wvcs[i]
        merged.append(out_row)

    # Output headers: keep original Zealy headers, then append WVC
    out_headers = list(zealy_headers)
    if "WVC" not in out_headers:
        out_headers.append("WVC")

    # Write output using Zealy's delimiter (so chi aprirà in Excel vede tutto allineato)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_headers, delimiter=zealy_delim)
        writer.writeheader()
        writer.writerows(merged)

    print(f"\n✅ Output written: {out_path.resolve()}")
    print(f"   Rows: {len(merged)} | Delimiter used: '{zealy_delim}'")
    if args.verbose:
        print_preview("Merged (output)", merged)

if __name__ == "__main__":
    main()


