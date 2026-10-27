import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scraper import BASE_URL, Book, parse_page, write_csv  # noqa: E402

FIXTURE = (Path(__file__).parent / "fixtures" / "listing_page.html").read_text(encoding="utf-8")


def test_parse_page_extracts_books():
    books, _ = parse_page(FIXTURE, BASE_URL)
    assert books == [
        Book("A Light in the Attic", 51.77, 3, True,
             BASE_URL + "catalogue/a-light-in-the-attic_1000/index.html"),
        # Mis-encoded currency symbol and "Out of stock" are both handled.
        Book("Tipping the Velvet", 53.74, 1, False,
             BASE_URL + "catalogue/tipping-the-velvet_999/index.html"),
    ]


def test_parse_page_finds_next_link():
    _, next_url = parse_page(FIXTURE, BASE_URL)
    assert next_url == BASE_URL + "catalogue/page-2.html"


def test_last_page_has_no_next_link():
    last_page = FIXTURE.replace('<li class="next"><a href="catalogue/page-2.html">next</a></li>', "")
    assert parse_page(last_page, BASE_URL)[1] is None


def test_write_csv(tmp_path):
    out = tmp_path / "books.csv"
    write_csv([Book("X", 1.5, 4, True, "http://x")], str(out))
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert rows == [{"title": "X", "price_gbp": "1.5", "rating": "4", "in_stock": "True", "url": "http://x"}]
