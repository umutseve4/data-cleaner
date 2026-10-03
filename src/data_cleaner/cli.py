"""Command line usage:

    python -m data_cleaner.cli data/raw/sample_sales.csv -o data/clean/sample_sales.csv --dates "Sipariş Tarihi"
"""
import argparse
from pathlib import Path

import pandas as pd

from .cleaning import clean_dataframe, standardize_missing
from .report import quality_report


def read_any(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path, dtype=str)
    return pd.read_csv(path, dtype=str, sep=None, engine="python")  # auto-detects , ; \t


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Clean a messy CSV/Excel file.")
    p.add_argument("input", type=Path)
    p.add_argument("-o", "--output", type=Path, help="output CSV (default: <input>_clean.csv)")
    p.add_argument("--dates", nargs="*", default=[], help="date column names (original names ok)")
    p.add_argument("--fill-numeric", default="none", choices=["none", "median", "mean", "zero"])
    p.add_argument("--fill-text", default=None)
    a = p.parse_args(argv)

    raw = read_any(a.input)
    clean = clean_dataframe(raw, date_columns=a.dates, fill_numeric=a.fill_numeric, fill_text=a.fill_text)
    out = a.output or a.input.with_name(a.input.stem + "_clean.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    clean.to_csv(out, index=False)

    # count hidden blanks ("N/A", "-", "null" ...) as missing in the "before" numbers too
    before, after = quality_report(standardize_missing(raw)), quality_report(clean)
    print(f"Rows: {len(raw)} -> {len(clean)}  (duplicates removed: {len(raw) - len(clean)})")
    print(f"Missing cells: {int(before['missing'].sum())} -> {int(after['missing'].sum())}")
    print("\nAfter cleaning:\n" + after.to_string(index=False))
    print(f"\nSaved -> {out}")


if __name__ == "__main__":
    main()
