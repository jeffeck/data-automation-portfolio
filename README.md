# Data Automation Portfolio

Small, working examples of the data jobs I do for clients: making slow SQL fast, turning messy exports into clean databases, and pulling structured data from the web.

I'm a data consultant with 15 years of experience in databases, SQL, Python, and data engineering. Each folder below is self-contained, runs in a minute or two, and has tests.

| Project | The client problem | Result |
|---|---|---|
| [SQL query tuning](01-sql-query-tuning/) | "Our report query takes forever." | **257x faster** (7.08 s → 0.03 s), identical results, verified automatically |
| [ETL pipeline](02-etl-pipeline/) | "Someone spends hours every week cleaning CSV exports by hand." | Automated cleaning, deduplication, and quarantine of bad rows, with safe re-runs |
| [Web scraper](03-web-scraper/) | "I need this site's catalog in a spreadsheet." | Paginated scrape to a clean CSV, with retries, polite delays, and offline tests |

## Quick start

```bash
pip install -r requirements.txt

cd 01-sql-query-tuning && python setup_db.py && python benchmark.py && cd ..
cd 02-etl-pipeline && python generate_sample.py && python pipeline.py && cd ..
cd 03-web-scraper && python scraper.py --pages 2 && cd ..

python -m pytest
```

## Work with me

Have a slow query, a manual data process, or data you need collected? Reach out on Upwork and I'll tell you honestly how I'd approach it.
