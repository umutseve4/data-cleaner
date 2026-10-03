# 🧹 data-cleaner

![tests](https://github.com/umutseve4/data-cleaner/actions/workflows/tests.yml/badge.svg)

Reusable, **tested** pandas functions that turn messy CSV / Excel exports into clean, analysis-ready tables.
Built with Turkish-style data in mind (`1.250,50 TL`, `03.10.2026`, `Müşteri Adı`), but works for US formats too.

## Before → after
**Raw** (`data/raw/sample_sales.csv`)
```
Sipariş No,Müşteri Adı ,Şehir,Sipariş Tarihi,Tutar (TL),İndirim
1001,  Ali   Yılmaz ,Bursa,03.10.2026,"1.250,50",%10
1002,Ayşe Demir,İstanbul,2026-10-04,"980,00",N/A
1003,Mehmet Kaya,ankara ,05/10/2026,"2.400,75",%5
1003,mehmet kaya,ankara,05/10/2026,"2.400,75",%5
1004,Zeynep Ak,-,06.10.2026,null,%0
1005,,İzmir,bilinmiyor,"15.000,00",%20
```
**Clean** (`data/clean/sample_sales.csv`)
```
siparis_no,musteri_adi,sehir,siparis_tarihi,tutar_tl,indirim
1001,Ali Yılmaz,Bursa,2026-10-03,1250.5,10
1002,Ayşe Demir,İstanbul,2026-10-04,980.0,
1003,Mehmet Kaya,ankara,2026-10-05,2400.75,5
1004,Zeynep Ak,,2026-10-06,,0
1005,,İzmir,,15000.0,20
```

## What it does
| Function | Fixes |
|---|---|
| `clean_column_names` | `Müşteri Adı ` → `musteri_adi`, `TotalPrice` → `total_price`, duplicate names → `_2` |
| `strip_whitespace` | `"  Ali   Yılmaz "` → `"Ali Yılmaz"` |
| `standardize_missing` | `N/A`, `null`, `-`, `?`, `yok`, `bilinmiyor`, `""` → real missing values |
| `parse_numbers` | `1.250,50`, `$3,000.25`, `₺15.000,00`, `%12` → numbers (auto-detects numeric columns, keeps integers as `Int64`) |
| `parse_dates` | mixed `03.10.2026` / `2026-10-04` / `05/10/2026` → datetime (day-first, ISO-safe) |
| `drop_duplicates` | case-insensitive duplicate rows |
| `fill_missing` | numeric gaps → median / mean / zero; text gaps → constant |
| `quality_report` | per-column dtype, missing %, unique count, example |
| `clean_dataframe` | all of the above in one call |

## Usage
```bash
git clone https://github.com/umutseve4/data-cleaner.git
cd data-cleaner
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt && pip install -e .

# command line
data-cleaner data/raw/sample_sales.csv -o out.csv --dates "Sipariş Tarihi"
```
```python
import pandas as pd
from data_cleaner import clean_dataframe, quality_report

df = pd.read_csv("messy.csv", dtype=str)
clean = clean_dataframe(df, date_columns=["Sipariş Tarihi"], fill_numeric="median")
print(quality_report(clean))
```

## Tests
```bash
pytest -v
```
GitHub Actions runs the test suite on every push (Python 3.10 & 3.12).

## Structure
```
data-cleaner/
├── src/data_cleaner/   # cleaning.py, report.py, cli.py
├── tests/              # pytest tests
├── data/raw|clean/     # small sample files
├── .github/workflows/  # CI
├── pyproject.toml
└── requirements.txt
```

## Roadmap
- [ ] Outlier detection (IQR / z-score)
- [ ] Phone / e-mail / IBAN validation
- [ ] YAML config so each dataset gets its own cleaning recipe

Python · pandas · pytest · GitHub Actions
