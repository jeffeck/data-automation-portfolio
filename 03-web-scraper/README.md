# Web Scraper: Paginated Catalog → Clean CSV

A common request: *"I need all the products, prices, and ratings from this site in a spreadsheet."*

This scraper walks a paginated catalog, pulls structured fields from each listing, normalizes them, and writes a clean CSV. It targets [books.toscrape.com](https://books.toscrape.com), a public sandbox built for scraping practice.

## What it does well

- **Follows pagination** until the last page or a page limit.
- **Normalizes data:** prices become numbers (it even handles mis-encoded `Â£` symbols), star ratings like `"Three"` become `3`, stock status becomes `True`/`False`, and relative links become absolute URLs.
- **Fails gracefully:** network errors are retried with exponential backoff.
- **Scrapes politely:** a configurable delay between requests and an identifying User-Agent.
- **Is tested:** the parsing tests run against a saved HTML page, so they work offline and catch breakage if the site's markup changes.

## Output

| title | price_gbp | rating | in_stock | url |
|---|---|---|---|---|
| A Light in the Attic | 51.77 | 3 | True | https://books.toscrape.com/catalogue/... |
| Tipping the Velvet | 53.74 | 1 | False | https://books.toscrape.com/catalogue/... |

## Run it

```bash
pip install requests beautifulsoup4 pytest
python scraper.py --pages 5 --out books.csv
python -m pytest tests
```

## Adapting it

For a real job, the selectors in `parse_page` change to match the target site. The output can go to Google Sheets, a database, or a scheduled daily refresh instead of a CSV. JavaScript-heavy sites would use Playwright instead of `requests`. I always check a site's terms and `robots.txt` before scraping it for a client.
