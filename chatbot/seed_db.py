"""Create a small sample store database (deterministic, no downloads)."""
import random
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "store.db"

PRODUCTS = [
    ("Laptop", "Electronics", 950.0), ("Headphones", "Electronics", 120.0),
    ("Smartphone", "Electronics", 700.0), ("Desk Lamp", "Home", 35.0),
    ("Office Chair", "Home", 180.0), ("Notebook", "Stationery", 4.5),
    ("Pen Set", "Stationery", 12.0), ("Backpack", "Accessories", 60.0),
]
CUSTOMERS = [
    ("Ayesha Khan", "Islamabad"), ("Bilal Ahmed", "Lahore"),
    ("Sara Malik", "Karachi"), ("Usman Ali", "Islamabad"),
    ("Hina Raza", "Peshawar"), ("Zain Abbas", "Lahore"),
]


def create_db(path: Path = DB_PATH, force: bool = False) -> Path:
    if path.exists():
        if not force:
            return path
        path.unlink()
    rnd = random.Random(42)
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, city TEXT);
        CREATE TABLE products  (id INTEGER PRIMARY KEY, name TEXT, category TEXT, price REAL);
        CREATE TABLE orders    (id INTEGER PRIMARY KEY, customer_id INTEGER, product_id INTEGER,
                                quantity INTEGER, order_date TEXT);
    """)
    con.executemany("INSERT INTO customers(name, city) VALUES (?,?)", CUSTOMERS)
    con.executemany("INSERT INTO products(name, category, price) VALUES (?,?,?)", PRODUCTS)
    for _ in range(60):
        con.execute(
            "INSERT INTO orders(customer_id, product_id, quantity, order_date) VALUES (?,?,?,?)",
            (rnd.randint(1, len(CUSTOMERS)), rnd.randint(1, len(PRODUCTS)),
             rnd.randint(1, 4), f"2026-{rnd.randint(1, 9):02d}-{rnd.randint(1, 28):02d}"),
        )
    con.commit()
    con.close()
    return path


if __name__ == "__main__":
    print("Created", create_db(force=True))
