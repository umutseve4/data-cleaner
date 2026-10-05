"""data_cleaner — small, reusable, tested pandas cleaning functions."""
from .cleaning import (
    clean_column_names,
    strip_whitespace,
    standardize_missing,
    parse_numbers,
    parse_dates,
    drop_duplicates,
    fill_missing,
    clean_dataframe,
)
from .report import quality_report
from .validation import (
    outlier_mask,
    handle_outliers,
    is_valid_email,
    normalize_tr_phone,
    is_valid_iban,
    format_iban,
    validate_columns,
)

__all__ = [
    "clean_column_names", "strip_whitespace", "standardize_missing", "parse_numbers",
    "parse_dates", "drop_duplicates", "fill_missing", "clean_dataframe", "quality_report",
    "outlier_mask", "handle_outliers", "is_valid_email", "normalize_tr_phone",
    "is_valid_iban", "format_iban", "validate_columns",
]
__version__ = "0.2.0"
