import sqlite3
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from pipeline import parse_date, parse_money, run  # noqa: E402

HEADER = "Order ID,Order Date,Product,Qty,Unit Price,Sales Rep,Customer Email\n"


@pytest.mark.parametrize("raw,expected", [
    ("2025-03-04", "2025-03-04"),
    ("03/04/2025", "2025-03-04"),
    ("04-Mar-2025", "2025-03-04"),
    ("2025/03/04", "2025-03-04"),
    ("not a date", None),
])
def test_parse_date(raw, expected):
    assert parse_date(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    ("$1,234.50", 1234.50), ("USD 9.99", 9.99), (" 12.00 ", 12.0),
])
def test_parse_money(raw, expected):
    assert parse_money(raw) == pytest.approx(expected)


def write_csv(folder: Path, name: str, body: str) -> None:
    (folder / name).write_text(HEADER + body)


def test_cleans_rejects_and_dedupes(tmp_path):
    inp = tmp_path / "in"
    inp.mkdir()
    write_csv(inp, "a.csv",
              "1,2025-01-02,widget a,2,$10.00, alice smith ,A@X.com\n"
              "1,2025-01-02,widget a,2,$10.00, alice smith ,A@X.com\n"  # exact duplicate
              ",,,,,,\n"                                                  # blank row
              "2,bad,Widget B,1,5.00,Bob,b@x.com\n")                       # bad date
    report = run(inp, tmp_path / "out.db", tmp_path / "rejects.csv")

    assert (report.blank_rows, report.duplicates, report.rejected, report.loaded) == (1, 1, 1, 1)
    row = sqlite3.connect(tmp_path / "out.db").execute("SELECT * FROM sales").fetchone()
    assert row[:8] == (1, "2025-01-02", "Widget A", 2, 10.0, 20.0, "Alice Smith", "a@x.com")
    assert pd.read_csv(tmp_path / "rejects.csv")["reject_reason"].tolist() == ["invalid date"]


def test_rerun_is_idempotent_and_applies_corrections(tmp_path):
    inp = tmp_path / "in"
    inp.mkdir()
    write_csv(inp, "a.csv", "1,2025-01-02,Widget A,2,10.00,Alice,a@x.com\n")
    db = tmp_path / "out.db"
    run(inp, db, tmp_path / "r.csv")
    run(inp, db, tmp_path / "r.csv")
    write_csv(inp, "b.csv", "1,2025-01-02,Widget A,5,10.00,Alice,a@x.com\n")  # correction
    run(inp, db, tmp_path / "r.csv")

    rows = sqlite3.connect(db).execute("SELECT order_id, quantity FROM sales").fetchall()
    assert rows == [(1, 5)]
