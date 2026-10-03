import pandas as pd

from data_cleaner import (
    clean_column_names,
    clean_dataframe,
    drop_duplicates,
    fill_missing,
    parse_dates,
    parse_numbers,
    quality_report,
    standardize_missing,
    strip_whitespace,
)
from data_cleaner.cleaning import _to_number


def test_clean_column_names_turkish_camel_and_duplicates():
    df = pd.DataFrame(columns=["Müşteri Adı ", "TotalPrice", "Şehir", "şehir", "  "])
    assert list(clean_column_names(df).columns) == [
        "musteri_adi", "total_price", "sehir", "sehir_2", "column",
    ]


def test_strip_whitespace_only_touches_text():
    df = pd.DataFrame({"name": ["  Ali   Veli ", None], "n": [1, 2]})
    out = strip_whitespace(df)
    assert out.loc[0, "name"] == "Ali Veli"
    assert out["n"].tolist() == [1, 2]


def test_standardize_missing_tokens():
    df = pd.DataFrame({"x": ["N/A", "null", "-", "", "ok", "Bilinmiyor"]})
    out = standardize_missing(df)
    assert out["x"].isna().tolist() == [True, True, True, True, False, True]


def test_to_number_formats():
    cases = {
        "1.250,50": 1250.5,      # Turkish
        "$3,000.25": 3000.25,    # US
        "₺15.000,00": 15000.0,
        "%12": 12.0,
        "12,5": 12.5,
        "1,234,567": 1234567.0,
        "1.234.567": 1234567.0,
        "-7": -7.0,
        "abc": None,
    }
    for raw, expected in cases.items():
        assert _to_number(raw) == expected, raw


def test_parse_numbers_auto_detect_skips_names():
    df = pd.DataFrame({"name": ["Ali", "Ayşe"], "price": ["1.000,50", "2,25"], "id": ["7", "8"]})
    out = parse_numbers(df)
    assert out["name"].tolist() == ["Ali", "Ayşe"]
    assert out["price"].tolist() == [1000.5, 2.25]
    assert str(out["id"].dtype) == "Int64"


def test_parse_dates_mixed_formats_dayfirst():
    df = pd.DataFrame({"d": ["03.10.2026", "2026-10-04", "05/10/2026", "garbage"]})
    out = parse_dates(df, ["d"])
    assert out["d"].dt.strftime("%Y-%m-%d").tolist()[:3] == ["2026-10-03", "2026-10-04", "2026-10-05"]
    assert pd.isna(out.loc[3, "d"])


def test_drop_duplicates_case_insensitive():
    df = pd.DataFrame({"name": ["Mehmet", "mehmet", "Ali"], "n": [1, 1, 1]})
    out = drop_duplicates(df)
    assert out["name"].tolist() == ["Mehmet", "Ali"]


def test_fill_missing_median_handles_int_columns():
    df = pd.DataFrame({"n": pd.array([1, 4, None], dtype="Int64"), "t": ["a", None, "b"]})
    out = fill_missing(df, numeric="median", text="unknown")
    assert out["n"].tolist() == [1.0, 4.0, 2.5]
    assert out["t"].tolist() == ["a", "unknown", "b"]


def test_clean_dataframe_end_to_end():
    raw = pd.DataFrame({
        "Sipariş No": ["1001", "1002", "1002"],
        " Müşteri Adı": ["  Ali  ", "Ayşe", "ayşe"],
        "Sipariş Tarihi": ["03.10.2026", "2026-10-04", "2026-10-04"],
        "Tutar (TL)": ["1.250,50", "N/A", "n/a"],
    })
    out = clean_dataframe(raw, date_columns=["Sipariş Tarihi"])
    assert list(out.columns) == ["siparis_no", "musteri_adi", "siparis_tarihi", "tutar_tl"]
    assert len(out) == 2
    assert out.loc[0, "musteri_adi"] == "Ali"
    assert out.loc[0, "tutar_tl"] == 1250.5
    assert pd.isna(out.loc[1, "tutar_tl"])
    assert pd.api.types.is_datetime64_any_dtype(out["siparis_tarihi"])


def test_quality_report():
    df = pd.DataFrame({"a": [1, None, 1], "b": ["x", "y", "x"]})
    rep = quality_report(df)
    assert rep.set_index("column").loc["a", "missing"] == 1
    assert rep.attrs["rows"] == 3
