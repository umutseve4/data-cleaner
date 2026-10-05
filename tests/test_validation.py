import pandas as pd
import pytest

from data_cleaner.validation import (
    format_iban,
    handle_outliers,
    is_valid_email,
    is_valid_iban,
    normalize_tr_phone,
    outlier_mask,
    validate_columns,
)

PRICES = pd.Series([100, 102, 98, 101, 99, 103, 97, 5000, None])


def test_outlier_mask_finds_the_spike():
    # with 8 points, a single spike's |z| can be at most (n-1)/sqrt(n) ≈ 2.47 -> use z=2.4 for zscore
    for method, kw in [("iqr", {}), ("mad", {}), ("zscore", {"z": 2.4})]:
        m = outlier_mask(PRICES, method=method, **kw)
        assert m.tolist() == [False] * 7 + [True, False], method   # NaN never flagged


def test_outlier_constant_column_has_no_outliers():
    assert not outlier_mask(pd.Series([5, 5, 5, 5]), method="zscore").any()
    assert not outlier_mask(pd.Series([5, 5, 5, 5]), method="mad").any()
    with pytest.raises(ValueError):
        outlier_mask(PRICES, method="magic")


def test_handle_outliers_actions():
    df = pd.DataFrame({"price": PRICES, "name": list("abcdefghi")})
    assert handle_outliers(df, action="flag")["price_outlier"].sum() == 1
    assert len(handle_outliers(df, action="remove")) == 8
    assert handle_outliers(df, action="clip")["price"].max() < 200
    assert pd.isna(handle_outliers(df, action="nan").loc[7, "price"])
    assert df.loc[7, "price"] == 5000          # original untouched
    with pytest.raises(ValueError):
        handle_outliers(df, action="explode")


def test_email():
    assert is_valid_email("umut.sever@ogr.uludag.edu.tr")
    assert is_valid_email(" Ali@Mail.com ")
    for bad in ["ali@", "ali.mail.com", "ali@mail", "ali@@mail.com", "a..b@mail.com", None, 5]:
        assert not is_valid_email(bad), bad


def test_tr_phone_normalized():
    for raw in ["0532 123 45 67", "+90 (532) 123-4567", "5321234567", "0090 532 123 45 67", "905321234567"]:
        assert normalize_tr_phone(raw) == "+905321234567", raw


def test_tr_phone_invalid():
    assert normalize_tr_phone("0224 294 00 00") == "+902242940000"   # Bursa landline is fine
    for bad in ["123", "0632 123 45 67", "05321234567890", None, "abc", True]:
        assert normalize_tr_phone(bad) is None, bad


def test_iban():
    good = "TR33 0006 1005 1978 6457 8413 26"   # standard example IBAN
    assert is_valid_iban(good)
    assert is_valid_iban(good.replace(" ", "").lower())
    assert is_valid_iban("DE89 3704 0044 0532 0130 00")
    assert not is_valid_iban("TR34 0006 1005 1978 6457 8413 26")   # wrong check digits
    assert not is_valid_iban("TR33 0006 1005 1978 6457 8413")      # wrong length
    assert not is_valid_iban(None)
    assert format_iban("tr330006100519786457841326") == good


def test_validate_columns():
    df = pd.DataFrame({
        "email": ["A@B.com", "bad"],
        "tel": ["0532 123 45 67", "12"],
        "iban": ["tr330006100519786457841326", "TR00"],
    })
    out = validate_columns(df, email=["email"], phone=["tel"], iban=["iban"])
    assert out["email_valid"].tolist() == [True, False]
    assert out["tel_valid"].tolist() == [True, False]
    assert out["iban_valid"].tolist() == [True, False]
    assert out.loc[0, "email"] == "a@b.com"
    assert out.loc[0, "tel"] == "+905321234567"
    assert out.loc[1, "tel"] == "12"                      # invalid values kept as-is for review
    assert out.loc[0, "iban"].startswith("TR33 0006")
    assert "email_valid" not in df.columns                # original untouched
