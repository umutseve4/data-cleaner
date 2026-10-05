"""Outlier detection and field validators (e-mail, Turkish phone, IBAN).

All DataFrame functions return a NEW DataFrame (no in-place edits), like cleaning.py.
"""
from __future__ import annotations

import re

import pandas as pd

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}$")

# IBAN length per country (subset; extend as needed). TR = 26.
IBAN_LENGTHS = {"TR": 26, "DE": 22, "GB": 22, "FR": 27, "NL": 18, "ES": 24, "IT": 27, "AT": 20, "BE": 16, "CH": 21}


# ----------------------------------------------------------------- outliers
def outlier_mask(s: pd.Series, method: str = "iqr", k: float = 1.5, z: float = 3.0) -> pd.Series:
    """True where the value is an outlier.

    method='iqr'    -> outside [Q1 - k*IQR, Q3 + k*IQR]   (robust, default k=1.5)
    method='zscore' -> |x - mean| / std > z              (assumes ~normal data)
    method='mad'    -> |x - median| / (1.4826*MAD) > z   (robust z-score)
    Missing values are never flagged.
    """
    x = pd.to_numeric(s, errors="coerce").astype(float)
    if method == "iqr":
        q1, q3 = x.quantile(0.25), x.quantile(0.75)
        iqr = q3 - q1
        lo, hi = q1 - k * iqr, q3 + k * iqr
        mask = (x < lo) | (x > hi)
    elif method == "zscore":
        std = x.std()
        mask = ((x - x.mean()).abs() / std > z) if std and std > 0 else pd.Series(False, index=x.index)
    elif method == "mad":
        med = x.median()
        mad = (x - med).abs().median() * 1.4826
        mask = ((x - med).abs() / mad > z) if mad and mad > 0 else pd.Series(False, index=x.index)
    else:
        raise ValueError(f"unknown method {method!r} (use 'iqr', 'zscore' or 'mad')")
    return mask.fillna(False).astype(bool)


def handle_outliers(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    method: str = "iqr",
    action: str = "flag",
    **kw,
) -> pd.DataFrame:
    """Detect outliers in numeric columns and 'flag' | 'clip' | 'remove' | 'nan' them.

    flag   -> adds a boolean column <col>_outlier
    clip   -> clips to the IQR fences (method='iqr' only) or to the 1st/99th percentile otherwise
    remove -> drops rows that are an outlier in ANY of the columns
    nan    -> replaces outliers with missing
    """
    if action not in {"flag", "clip", "remove", "nan"}:
        raise ValueError(f"unknown action {action!r} (use 'flag', 'clip', 'remove' or 'nan')")
    out = df.copy()
    cols = columns or [c for c in out.columns
                       if pd.api.types.is_numeric_dtype(out[c]) and not pd.api.types.is_bool_dtype(out[c])]
    any_mask = pd.Series(False, index=out.index)
    for c in cols:
        m = outlier_mask(out[c], method=method, **kw)
        if action == "flag":
            out[f"{c}_outlier"] = m
        elif action == "clip":
            x = out[c].astype(float)
            if method == "iqr":
                k = kw.get("k", 1.5)
                q1, q3 = x.quantile(0.25), x.quantile(0.75)
                lo, hi = q1 - k * (q3 - q1), q3 + k * (q3 - q1)
            else:
                lo, hi = x.quantile(0.01), x.quantile(0.99)
            out[c] = x.clip(lo, hi)
        elif action == "nan":
            out[c] = out[c].astype(float).mask(m)
        else:  # remove
            any_mask |= m
    if action == "remove":
        out = out[~any_mask].reset_index(drop=True)
    return out


# ----------------------------------------------------------------- validators
def is_valid_email(v) -> bool:
    return isinstance(v, str) and bool(_EMAIL_RE.match(v.strip())) and ".." not in v


def normalize_tr_phone(v) -> str | None:
    """'0532 123 45 67', '+90 (532) 123-4567', '5321234567' -> '+905321234567'. Invalid -> None.

    Accepts Turkish mobile (5xx) and landline (2xx, 3xx, 4xx) numbers, 10 national digits.
    """
    if not isinstance(v, (str, int)) or isinstance(v, bool):
        return None
    digits = re.sub(r"\D", "", str(v))
    if digits.startswith("0090"):
        digits = digits[4:]
    elif digits.startswith("90") and len(digits) == 12:
        digits = digits[2:]
    elif digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    if len(digits) != 10 or digits[0] not in "2345":
        return None
    return "+90" + digits


def is_valid_iban(v) -> bool:
    """ISO 13616 check: country length + mod-97 == 1. Spaces/lowercase are fine."""
    if not isinstance(v, str):
        return False
    s = re.sub(r"\s+", "", v).upper()
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}", s):
        return False
    if IBAN_LENGTHS.get(s[:2], len(s)) != len(s):
        return False
    rearranged = s[4:] + s[:4]
    numeric = "".join(str(int(ch, 36)) for ch in rearranged)  # A=10 ... Z=35
    return int(numeric) % 97 == 1


def format_iban(v) -> str | None:
    """Valid IBAN -> 'TR33 0006 1005 1978 6457 8413 26'; invalid -> None."""
    if not is_valid_iban(v):
        return None
    s = re.sub(r"\s+", "", v).upper()
    return " ".join(s[i:i + 4] for i in range(0, len(s), 4))


def validate_columns(
    df: pd.DataFrame,
    email: list[str] | None = None,
    phone: list[str] | None = None,
    iban: list[str] | None = None,
    normalize: bool = True,
) -> pd.DataFrame:
    """Adds <col>_valid boolean columns; with normalize=True also rewrites e-mails/phones/IBANs to a standard form.

    Invalid values are kept as-is so they can be reviewed.
    """
    out = df.copy()
    for c in email or []:
        out[f"{c}_valid"] = out[c].map(is_valid_email).astype(bool)
        if normalize:
            out[c] = out[c].map(lambda v: v.strip().lower() if isinstance(v, str) else v)
    for c in phone or []:
        norm = out[c].map(normalize_tr_phone)
        out[f"{c}_valid"] = norm.notna().astype(bool)
        if normalize:
            out[c] = [n if isinstance(n, str) else o for n, o in zip(norm, out[c])]
    for c in iban or []:
        out[f"{c}_valid"] = out[c].map(is_valid_iban).astype(bool)
        if normalize:
            out[c] = out[c].map(lambda v: format_iban(v) or v)
    return out
