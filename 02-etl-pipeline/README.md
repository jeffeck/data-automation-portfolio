# ETL Pipeline: Messy CSV Exports → Clean Database

A common request: *"Every week we export sales from our system into CSVs, and someone spends hours cleaning them up in Excel before they go into our database or report."*

This pipeline does that job automatically and can be re-run safely.

## What it handles

| Problem in the raw files | What the pipeline does |
|---|---|
| Dates in 4 formats (`2025-03-04`, `03/04/2025`, `04-Mar-2025`, …) | Converts them all to ISO `YYYY-MM-DD` |
| Money as `$1,234.50`, `USD 9.99`, ` 12.00 ` | Turns them into numbers |
| `alice smith`, `BOB JONES`, ` Carol Diaz ` | Trims and title-cases names |
| `  Customer1@Example.com ` | Trims and lowercases emails |
| Blank rows and exact duplicates | Removes them and counts them |
| The same order re-sent with corrections in a later file | Keeps the latest version |
| Rows that can't be trusted (bad date, `n/a` quantity, missing email) | **Quarantines** them in `rejects.csv` with a reason, so nothing is lost silently |
| Running the job twice | Upserts on `order_id`, so nothing is double-counted |

## Sample run

```
Files read:        3
Rows read:         627
Blank rows:        3
Duplicates:        24
Superseded:        4 (older versions of corrected orders)
Rejected:          9
Loaded (upserted): 587
  - invalid date: 3
  - invalid quantity: 3
  - missing email: 3
```

## Run it

```bash
pip install pandas pytest
python generate_sample.py   # creates sample_data/*.csv with realistic mess
python pipeline.py          # loads sales.db, writes rejects.csv
python -m pytest tests      # 10 tests: parsing, rejects, dedupe, idempotent reruns
```

## Adapting it

The load step uses SQLite here so the demo runs anywhere. In a real job it would point at PostgreSQL, SQL Server, BigQuery, Snowflake, or a Google Sheet. The input could also be an API, an SFTP drop, or an email attachment instead of a folder. A scheduler such as cron, GitHub Actions, or Airflow can run it every week with no manual work.
