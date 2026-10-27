"""Generate messy CSV exports like the ones clients actually send.

Each file has the problems that show up in real exports: mixed date formats,
currency symbols, stray whitespace, inconsistent casing, duplicate rows, blank
lines, and a few rows that can't be saved.

Usage: python generate_sample.py
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

OUT_DIR = Path(__file__).parent / "sample_data"
PRODUCTS = ["Widget A", "Widget B", "Gadget Pro", "Gadget Mini", "Service Plan"]
REPS = ["alice smith", "BOB JONES", " Carol Diaz ", "dave kim"]
DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%d-%b-%Y", "%Y/%m/%d"]


def messy_amount(value: float) -> str:
    return random.choice([f"{value:.2f}", f"${value:,.2f}", f" {value:.2f} ", f"USD {value:.2f}"])


def generate(files: int = 3, rows_per_file: int = 200, seed: int = 7) -> None:
    random.seed(seed)
    OUT_DIR.mkdir(exist_ok=True)
    order_id = 1000
    for n in range(1, files + 1):
        rows = []
        for _ in range(rows_per_file):
            order_id += 1
            day = date(2025, 1, 1) + timedelta(days=random.randint(0, 300))
            qty = random.randint(1, 10)
            price = round(random.uniform(9.99, 499.0), 2)
            rows.append({
                "Order ID": str(order_id),
                "Order Date": day.strftime(random.choice(DATE_FORMATS)),
                "Product": random.choice(PRODUCTS) if random.random() > 0.05 else random.choice(PRODUCTS).upper(),
                "Qty": str(qty),
                "Unit Price": messy_amount(price),
                "Sales Rep": random.choice(REPS),
                "Customer Email": f"  Customer{random.randint(1, 80)}@Example.com ",
            })
        # Real-world problems: duplicates, bad rows, blank lines.
        rows += random.sample(rows, 8)
        rows[3]["Qty"] = "n/a"
        rows[10]["Order Date"] = "not a date"
        rows[15]["Customer Email"] = ""
        rows.insert(50, {k: "" for k in rows[0]})
        if n > 1:  # later exports re-send some orders with corrected quantities
            for r in rows[:5]:
                r["Order ID"] = str(int(r["Order ID"]) - rows_per_file)

        path = OUT_DIR / f"sales_export_{n}.csv"
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {path.name} ({len(rows)} rows)")


if __name__ == "__main__":
    generate()
