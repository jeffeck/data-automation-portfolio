"""Scrape a paginated product catalog into a clean CSV.

Targets books.toscrape.com, a public sandbox site built for scraping practice.
The same pattern (paginate -> parse -> normalize -> export) applies to
real catalogs, directories, and listings sites.

Usage: python scraper.py [--pages 5] [--out books.csv] [--delay 1.0]
"""
import argparse
import csv
import logging
import re
import time
from dataclasses import asdict, dataclass
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://books.toscrape.com/"
RATINGS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
log = logging.getLogger("scraper")


@dataclass
class Book:
    title: str
    price_gbp: float
    rating: int
    in_stock: bool
    url: str


def fetch(session: requests.Session, url: str, retries: int = 3) -> str:
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(url, timeout=15)
            resp.raise_for_status()
            resp.encoding = "utf-8"
            return resp.text
        except requests.RequestException as exc:
            if attempt == retries:
                raise
            wait = 2 ** attempt
            log.warning("Attempt %d for %s failed (%s); retrying in %ds", attempt, url, exc, wait)
            time.sleep(wait)
    raise AssertionError("unreachable")


def parse_page(html: str, page_url: str) -> tuple[list[Book], str | None]:
    """Return the books on a listing page and the URL of the next page, if any."""
    soup = BeautifulSoup(html, "html.parser")
    books = []
    for card in soup.select("article.product_pod"):
        link = card.select_one("h3 a")
        rating_class = next(c for c in card.select_one("p.star-rating")["class"] if c != "star-rating")
        price_text = card.select_one("p.price_color").get_text(strip=True)
        books.append(Book(
            title=link["title"].strip(),
            price_gbp=float(re.search(r"\d+(?:\.\d+)?", price_text).group()),
            rating=RATINGS.get(rating_class, 0),
            in_stock="in stock" in card.select_one("p.availability").get_text(" ", strip=True).lower(),
            url=urljoin(page_url, link["href"]),
        ))
    next_link = soup.select_one("li.next a")
    return books, urljoin(page_url, next_link["href"]) if next_link else None


def scrape(max_pages: int, delay: float) -> list[Book]:
    session = requests.Session()
    session.headers["User-Agent"] = "portfolio-demo-scraper/1.0 (+https://github.com/jeffeck/data-automation-portfolio)"
    url, books = BASE_URL, []
    for page in range(1, max_pages + 1):
        page_books, url = parse_page(fetch(session, url), url)
        books.extend(page_books)
        log.info("Page %d: %d books", page, len(page_books))
        if not url:
            break
        time.sleep(delay)  # be polite to the server
    return books


def write_csv(books: list[Book], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(Book.__dataclass_fields__))
        writer.writeheader()
        writer.writerows(asdict(b) for b in books)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=5)
    parser.add_argument("--out", default="books.csv")
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    results = scrape(args.pages, args.delay)
    write_csv(results, args.out)
    print(f"Saved {len(results)} books to {args.out}")
