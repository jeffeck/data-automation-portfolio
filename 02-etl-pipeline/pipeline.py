"""Clean messy sales CSVs and load them into a database, safely re-runnable.

Extract: read every CSV in the input folder.
Transform: standardize dates, money, names, emails; drop blanks and duplicates;
           quarantine rows that fail validation instead of silently losing them.
Load: upsert into SQLite keyed on order_id, so re-running never double-counts.

Usage: python pipeline.py [--input sample_data] [--db sales.db]
"""
import argparse
import logging
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

log = logging.getLogger("etl")

COLUMN_MAP = {
    "Order ID": "order_id",
    "Order Date": "order_date",
    "Product": "product",
    "Qty": "quantity",
    "Unit Price": "unit_price",
    "Sales Rep": "sales_rep",
    "Customer Email": "customer_email",
}
DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%d-%b-%Y", "%Y/%m/%d"]


@dataclass
class RunReport:
    files: int = 0
    rows_read: int = 0
    blank_rows: int = 0
    duplicates: int = 0
    superseded: int = 0
    rejected: int = 0
    loaded: int = 0
    reject_reasons: dict = field(default_factory=dict)

    def summary(self) -> str:
        lines = [
            f"Files read:        {self.files}",
            f"Rows read:         {self.rows_read}",
            f"Blank rows:        {self.blank_rows}",
            f"Duplicates:        {self.duplicates}",
            f"Superseded:        {self.superseded} (older versions of corrected orders)",
            f"Rejected:          {self.rejected}",
            f"Loaded (upserted): {self.loaded}",
        ]
        lines += [f"  - {reason}: {n}" for reason, n in self.reject_reasons.items()]
        return "\n".join(lines)


def parse_date(value: str):
    for fmt in DATE_FORMATS:
        parsed = pd.to_datetime(value, format=fmt, errors="coerce")
        if pd.notna(parsed):
            return parsed.date().isoformat()
    return None


def parse_money(value: str):
    cleaned = str(value).replace("USD", "").replace("$", "").replace(",", "").strip()
    return pd.to_numeric(cleaned, errors="coerce")


def extract(input_dir: Path, report: RunReport) -> pd.DataFrame:
    frames = []
    for path in sorted(input_dir.glob("*.csv")):
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        df["source_file"] = path.name
        frames.append(df)
        log.info("Read %s (%d rows)", path.name, len(df))
    if not frames:
        raise SystemExit(f"No CSV files found in {input_dir}")
    report.files = len(frames)
    combined = pd.concat(frames, ignore_index=True)
    report.rows_read = len(combined)
    return combined


def transform(raw: pd.DataFrame, report: RunReport) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = raw.rename(columns=COLUMN_MAP)

    blank = (df[list(COLUMN_MAP.values())].apply(lambda c: c.str.strip()) == "").all(axis=1)
    report.blank_rows = int(blank.sum())
    df = df[~blank].copy()

    df["order_id"] = pd.to_numeric(df["order_id"].str.strip(), errors="coerce")
    df["order_date"] = df["order_date"].str.strip().map(parse_date)
    df["product"] = df["product"].str.strip().str.title()
    df["quantity"] = pd.to_numeric(df["quantity"].str.strip(), errors="coerce")
    df["unit_price"] = df["unit_price"].map(parse_money)
    df["sales_rep"] = df["sales_rep"].str.strip().str.title()
    df["customer_email"] = df["customer_email"].str.strip().str.lower()

    checks = {
        "invalid order_id": df["order_id"].isna(),
        "invalid date": df["order_date"].isna(),
        "invalid quantity": df["quantity"].isna() | (df["quantity"] <= 0),
        "invalid price": df["unit_price"].isna() | (df["unit_price"] < 0),
        "missing email": df["customer_email"] == "",
    }
    bad = pd.Series(False, index=df.index)
    reasons = pd.Series("", index=df.index)
    for reason, mask in checks.items():
        reasons[mask & ~bad] = reason
        bad |= mask
        if mask.any():
            report.reject_reasons[reason] = int(mask.sum())
    rejects = raw.loc[df.index[bad]].assign(reject_reason=reasons[bad])
    report.rejected = len(rejects)

    good = df[~bad].copy()
    before = len(good)
    good = good.drop_duplicates(subset=list(COLUMN_MAP.values()))
    report.duplicates = before - len(good)

    # The same order can appear in a later export with corrections: keep the latest.
    before = len(good)
    good = good.drop_duplicates(subset="order_id", keep="last")
    report.superseded = before - len(good)
    good["order_id"] = good["order_id"].astype(int)
    good["quantity"] = good["quantity"].astype(int)
    good["line_total"] = (good["quantity"] * good["unit_price"]).round(2)
    return good, rejects


def load(clean: pd.DataFrame, db_path: Path, report: RunReport) -> None:
    con = sqlite3.connect(db_path)
    con.execute(
        """CREATE TABLE IF NOT EXISTS sales (
               order_id       INTEGER PRIMARY KEY,
               order_date     TEXT NOT NULL,
               product        TEXT NOT NULL,
               quantity       INTEGER NOT NULL,
               unit_price     REAL NOT NULL,
               line_total     REAL NOT NULL,
               sales_rep      TEXT NOT NULL,
               customer_email TEXT NOT NULL,
               source_file    TEXT NOT NULL
           )"""
    )
    cols = ["order_id", "order_date", "product", "quantity", "unit_price",
            "line_total", "sales_rep", "customer_email", "source_file"]
    with con:
        con.executemany(
            f"""INSERT INTO sales ({", ".join(cols)}) VALUES ({", ".join("?" * len(cols))})
                ON CONFLICT(order_id) DO UPDATE SET
                {", ".join(f"{c} = excluded.{c}" for c in cols[1:])}""",
            clean[cols].itertuples(index=False, name=None),
        )
    con.close()
    report.loaded = len(clean)


def run(input_dir: Path, db_path: Path, rejects_path: Path) -> RunReport:
    report = RunReport()
    raw = extract(input_dir, report)
    clean, rejects = transform(raw, report)
    load(clean, db_path, report)
    rejects.to_csv(rejects_path, index=False)
    log.info("Wrote %d rejected rows to %s for review", len(rejects), rejects_path.name)
    return report


if __name__ == "__main__":
    here = Path(__file__).parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=here / "sample_data")
    parser.add_argument("--db", type=Path, default=here / "sales.db")
    parser.add_argument("--rejects", type=Path, default=here / "rejects.csv")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    print("\n" + run(args.input, args.db, args.rejects).summary())
