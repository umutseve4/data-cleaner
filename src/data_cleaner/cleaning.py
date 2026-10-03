"""Core cleaning functions. Every function takes a DataFrame and returns a NEW one (no in-place edits)."""
from __future__ import annotations

import re
import unicodedata

import pandas as pd

# Values that people (and Excel exports) use to mean "no data"
MISSING_TOKENS = {"", "na", "n/a", "nan", "null", "none", "-", "--", "?", "yok", "bilinmiyor"}

_TR_MAP = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")


def _is_text(s: pd.Series) -> bool:
    return pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s)


def _snake(name: str) -> str:
    name = str(name).translate(_TR_MAP)
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)       # camelCase -> camel_Case
    name = re.sub(r"[^0-9a-zA-Z]+", "_", name).strip("_").lower()
    return name or "column"


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """'Müşteri Adı ' -> 'musteri_adi', 'TotalPrice' -> 'total_price'. Duplicates get _2, _3 ..."""
    seen: dict[str, int] = {}
    cols = []
    for c in df.columns:
        base = _snake(c)
        seen[base] = seen.get(base, 0) + 1
        cols.append(base if seen[base] == 1 else f"{base}_{seen[base]}")
    out = df.copy()
    out.columns = cols
    return out


def strip_whitespace(df: pd.DataFrame) -> pd.DataFrame:
    """Trim text cells and collapse repeated inner spaces: '  Ali   Veli ' -> 'Ali Veli'."""
    out = df.copy()
    for c in out.columns:
        if _is_text(out[c]):
            out[c] = out[c].map(lambda v: re.sub(r"\s+", " ", v).strip() if isinstance(v, str) else v)
    return out


def standardize_missing(df: pd.DataFrame, tokens: set[str] | None = None) -> pd.DataFrame:
    """Turn 'N/A', 'null', '-', '' ... into real missing values (NA)."""
    tokens = {t.lower() for t in (tokens or MISSING_TOKENS)}
    out = df.copy()
    for c in out.columns:
        if _is_text(out[c]):
            mask = out[c].map(lambda v: isinstance(v, str) and v.strip().lower() in tokens).astype(bool)
            out[c] = out[c].astype(object).where(~mask, None)
    return out


def _to_number(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (int, float)):
        return v
    s = re.sub(r"[^\d,.\-]", "", str(v))          # drop currency, %, spaces: '₺1.234,50' -> '1.234,50'
    if not s or s in {"-", ".", ","}:
        return None
    if "," in s and "." in s:                      # whichever comes last is the decimal separator
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:                                 # '12,5' -> 12.5 ; '1,234,567' -> 1234567
        s = s.replace(",", "") if re.fullmatch(r"-?\d{1,3}(,\d{3})+", s) else s.replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(\.\d{3}){2,}", s):  # '1.234.567' -> 1234567
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def parse_numbers(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    min_success: float = 0.8,
    exclude: list[str] | None = None,
) -> pd.DataFrame:
    """Convert text numbers ('1.234,50 TL', '%12', '$3,000.25') to floats.

    If `columns` is None, a text column is converted only when >= `min_success` of its
    non-missing values parse as numbers (so name/city columns are left alone).
    """
    out = df.copy()
    exclude = set(exclude or [])
    targets = columns if columns is not None else [
        c for c in out.columns if _is_text(out[c]) and c not in exclude
    ]
    for c in targets:
        raw = out[c]
        parsed = raw.map(_to_number)
        non_missing = raw.notna().sum()
        ok = parsed.notna().sum()
        if columns is not None or (non_missing and ok / non_missing >= min_success):
            num = pd.to_numeric(parsed, errors="coerce")
            whole = num.dropna()
            is_int = len(whole) > 0 and bool((whole % 1 == 0).all())
            out[c] = num.astype("Int64") if is_int else num.astype(float)
    return out


def parse_dates(df: pd.DataFrame, columns: list[str], dayfirst: bool = True) -> pd.DataFrame:
    """Parse mixed date strings ('03.10.2026', '2026-10-03', '3/10/2026'). Unparseable -> NaT."""
    out = df.copy()
    for c in columns:
        s = out[c].astype("string")
        iso = s.str.match(r"^\s*\d{4}-\d{1,2}-\d{1,2}", na=False)   # ISO is never day-first
        parsed = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
        if iso.any():
            parsed[iso] = pd.to_datetime(s[iso], errors="coerce", format="ISO8601")
        if (~iso).any():
            parsed[~iso] = pd.to_datetime(s[~iso], errors="coerce", dayfirst=dayfirst, format="mixed")
        out[c] = parsed
    return out


def drop_duplicates(df: pd.DataFrame, subset: list[str] | None = None) -> pd.DataFrame:
    """Drop exact duplicate rows (case-insensitive for text) and reset the index."""
    key = df.copy()
    for c in key.columns:
        if _is_text(key[c]):
            key[c] = key[c].map(lambda v: v.lower() if isinstance(v, str) else v)
    keep = ~key.duplicated(subset=subset, keep="first")
    return df[keep.values].reset_index(drop=True)


def fill_missing(df: pd.DataFrame, numeric: str = "median", text: str | None = None) -> pd.DataFrame:
    """Fill numeric gaps with 'median' | 'mean' | 'zero' | 'none'; optionally fill text gaps with a constant."""
    out = df.copy()
    for c in out.columns:
        s = out[c]
        if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
            value = {"median": s.median, "mean": s.mean, "zero": lambda: 0}.get(numeric, lambda: None)()
            if value is None or pd.isna(value):
                continue
            if pd.api.types.is_integer_dtype(s) and float(value) % 1 != 0:
                s = s.astype(float)               # 2.5 can't live in an integer column
            out[c] = s.fillna(value)
        elif text is not None and _is_text(s):
            out[c] = s.fillna(text)
    return out


def clean_dataframe(
    df: pd.DataFrame,
    date_columns: list[str] | None = None,
    fill_numeric: str = "none",
    fill_text: str | None = None,
) -> pd.DataFrame:
    """One-call pipeline: names -> whitespace -> missing tokens -> numbers -> dates -> duplicates -> fill."""
    out = clean_column_names(df)
    out = strip_whitespace(out)
    out = standardize_missing(out)
    date_cols = [_snake(c) for c in (date_columns or [])]
    out = parse_numbers(out, exclude=date_cols)
    if date_cols:
        out = parse_dates(out, date_cols)
    out = drop_duplicates(out)
    out = fill_missing(out, numeric=fill_numeric, text=fill_text)
    return out
