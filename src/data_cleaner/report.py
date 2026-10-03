"""Data quality report: what is wrong with a table, column by column."""
import pandas as pd


def quality_report(df: pd.DataFrame) -> pd.DataFrame:
    """One row per column: dtype, missing count/%, unique values, example value."""
    rows = []
    n = len(df)
    for c in df.columns:
        s = df[c]
        missing = int(s.isna().sum())
        example = s.dropna().iloc[0] if s.notna().any() else None
        rows.append({
            "column": c,
            "dtype": str(s.dtype),
            "missing": missing,
            "missing_pct": round(missing / n * 100, 1) if n else 0.0,
            "unique": int(s.nunique(dropna=True)),
            "example": example,
        })
    rep = pd.DataFrame(rows)
    rep.attrs["rows"] = n
    rep.attrs["duplicate_rows"] = int(df.duplicated().sum())
    return rep
