# data-cleaner

A repo for data cleaning scripts.

Reusable Python scripts for turning messy raw data (CSV, Excel, API dumps) into clean, analysis-ready tables.

## Goals
- Handle missing values, duplicates and inconsistent types
- Normalize text, dates and numeric formats
- Keep every cleaning step reproducible and testable

## Planned structure
```
data-cleaner/
├── src/          # cleaning functions
├── tests/        # pytest tests
├── data/         # sample raw / cleaned data (small files only)
└── requirements.txt
```

## Getting started
```bash
git clone https://github.com/umutseve4/data-cleaner.git
cd data-cleaner
python -m venv .venv && source .venv/bin/activate
pip install pandas
```

## Tech
Python · pandas
