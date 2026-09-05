"""SQLite data layer for RetailIQ.

Provides:
- Deterministic database initialization from CSV datasets
- Foreign key enforcement and indexed queries
- Safe, parameterized query helper functions for products, stores, sales, and inventory
"""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional
import pandas as pd

from src.config import DATABASE_PATH, DATA_DIR


def ensure_data_directory(data_dir: Path = DATA_DIR) -> None:
    """Ensure the target data directory exists."""
    data_dir.mkdir(parents=True, exist_ok=True)


def get_connection(db_path: str | Path = DATABASE_PATH) -> sqlite3.Connection:
    """Get a connection to the SQLite database with foreign keys enabled."""
    ensure_data_directory(Path(db_path).parent)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db_cursor(db_path: str | Path = DATABASE_PATH) -> Generator[sqlite3.Cursor, None, None]:
    """Context manager for acquiring a database cursor with automatic commit/rollback."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def create_tables(conn: sqlite3.Connection) -> None:
    """Create products, stores, sales, and inventory tables with indexes."""
    cursor = conn.cursor()

    # 1. Products table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        product_id TEXT PRIMARY KEY,
        product_name TEXT NOT NULL,
        category TEXT NOT NULL,
        unit_price REAL NOT NULL CHECK (unit_price > 0),
        reorder_level INTEGER NOT NULL CHECK (reorder_level >= 0)
    );
    """)

    # 2. Stores table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stores (
        store_id TEXT PRIMARY KEY,
        store_name TEXT NOT NULL,
        city TEXT NOT NULL
    );
    """)

    # 3. Sales table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        sale_id TEXT PRIMARY KEY,
        date TEXT NOT NULL,
        store_id TEXT NOT NULL,
        product_id TEXT NOT NULL,
        quantity INTEGER NOT NULL CHECK (quantity > 0),
        unit_price REAL NOT NULL CHECK (unit_price > 0),
        revenue REAL NOT NULL CHECK (revenue >= 0),
        FOREIGN KEY (store_id) REFERENCES stores (store_id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products (product_id) ON DELETE CASCADE
    );
    """)

    # 4. Inventory table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        store_id TEXT NOT NULL,
        product_id TEXT NOT NULL,
        current_stock INTEGER NOT NULL CHECK (current_stock >= 0),
        reorder_level INTEGER NOT NULL CHECK (reorder_level >= 0),
        PRIMARY KEY (store_id, product_id),
        FOREIGN KEY (store_id) REFERENCES stores (store_id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products (product_id) ON DELETE CASCADE
    );
    """)

    # 5. Indexes for fast query performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_date ON sales (date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_product_id ON sales (product_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_store_id ON sales (store_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_date_product ON sales (date, product_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_product_id ON inventory (product_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_store_id ON inventory (store_id);")

    conn.commit()


def load_csv_data(conn: sqlite3.Connection, data_dir: Path = DATA_DIR) -> Dict[str, int]:
    """Load products, stores, sales, and inventory CSV files into the SQLite database.

    Returns a dictionary of loaded record counts per table.
    Raises FileNotFoundError or sqlite3.IntegrityError if validation fails.
    """
    products_csv = data_dir / "products.csv"
    stores_csv = data_dir / "stores.csv"
    sales_csv = data_dir / "sales.csv"
    inventory_csv = data_dir / "inventory.csv"

    for required_file in (products_csv, stores_csv, sales_csv, inventory_csv):
        if not required_file.exists():
            raise FileNotFoundError(f"Required CSV dataset not found: {required_file}")

    df_products = pd.read_csv(products_csv)
    df_stores = pd.read_csv(stores_csv)
    df_sales = pd.read_csv(sales_csv)
    df_inventory = pd.read_csv(inventory_csv)

    cursor = conn.cursor()

    # Load products
    product_rows = [
        (
            str(row["product_id"]),
            str(row["product_name"]),
            str(row["category"]),
            float(row["unit_price"]),
            int(row["reorder_level"]),
        )
        for _, row in df_products.iterrows()
    ]
    cursor.executemany(
        """
        INSERT OR REPLACE INTO products (product_id, product_name, category, unit_price, reorder_level)
        VALUES (?, ?, ?, ?, ?);
        """,
        product_rows,
    )

    # Load stores
    store_rows = [
        (str(row["store_id"]), str(row["store_name"]), str(row["city"]))
        for _, row in df_stores.iterrows()
    ]
    cursor.executemany(
        """
        INSERT OR REPLACE INTO stores (store_id, store_name, city)
        VALUES (?, ?, ?);
        """,
        store_rows,
    )

    # Load sales
    sales_rows = [
        (
            str(row["sale_id"]),
            str(row["date"]),
            str(row["store_id"]),
            str(row["product_id"]),
            int(row["quantity"]),
            float(row["unit_price"]),
            float(row["revenue"]),
        )
        for _, row in df_sales.iterrows()
    ]
    cursor.executemany(
        """
        INSERT OR REPLACE INTO sales (sale_id, date, store_id, product_id, quantity, unit_price, revenue)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        sales_rows,
    )

    # Load inventory
    inv_rows = [
        (
            str(row["store_id"]),
            str(row["product_id"]),
            int(row["current_stock"]),
            int(row["reorder_level"]),
        )
        for _, row in df_inventory.iterrows()
    ]
    cursor.executemany(
        """
        INSERT OR REPLACE INTO inventory (store_id, product_id, current_stock, reorder_level)
        VALUES (?, ?, ?, ?);
        """,
        inv_rows,
    )

    conn.commit()

    return {
        "products": len(product_rows),
        "stores": len(store_rows),
        "sales": len(sales_rows),
        "inventory": len(inv_rows),
    }


def is_database_initialized(db_path: str | Path = DATABASE_PATH) -> bool:
    """Check whether the SQLite database exists and has populated tables."""
    path = Path(db_path)
    if not path.exists() or path.stat().st_size == 0:
        return False

    try:
        conn = get_connection(path)
        cursor = conn.cursor()
        required_tables = {"products", "stores", "sales", "inventory"}
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_tables = {row["name"] for row in cursor.fetchall()}
        if not required_tables.issubset(existing_tables):
            conn.close()
            return False

        # Verify tables contain records
        for table in required_tables:
            cursor.execute(f"SELECT COUNT(*) as count FROM {table};")
            if cursor.fetchone()["count"] == 0:
                conn.close()
                return False

        conn.close()
        return True
    except Exception:
        return False


def init_db(
    db_path: str | Path = DATABASE_PATH,
    data_dir: Path = DATA_DIR,
    force: bool = False,
) -> Dict[str, int]:
    """Initialize SQLite database: create schema and populate from CSV if not already done.

    Returns the table record counts.
    """
    if not force and is_database_initialized(db_path):
        return get_table_counts(db_path)

    conn = get_connection(db_path)
    try:
        create_tables(conn)
        counts = load_csv_data(conn, data_dir=data_dir)
        return counts
    finally:
        conn.close()


def get_table_counts(db_path: str | Path = DATABASE_PATH) -> Dict[str, int]:
    """Get the row count for each core table."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        counts = {}
        for table in ("products", "stores", "sales", "inventory"):
            cursor.execute(f"SELECT COUNT(*) as cnt FROM {table};")
            counts[table] = cursor.fetchone()["cnt"]
        return counts
    finally:
        conn.close()


# --------------------------------------------------------------------------
# Reusable Parameterized Query Layer
# --------------------------------------------------------------------------

def get_product(product_id: str, db_path: str | Path = DATABASE_PATH) -> Optional[Dict[str, Any]]:
    """Retrieve a single product by ID."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT product_id, product_name, category, unit_price, reorder_level FROM products WHERE product_id = ?;",
            (product_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_products(category: Optional[str] = None, db_path: str | Path = DATABASE_PATH) -> List[Dict[str, Any]]:
    """Retrieve all products, optionally filtered by category."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        if category:
            cursor.execute(
                "SELECT product_id, product_name, category, unit_price, reorder_level FROM products WHERE category = ? ORDER BY product_id;",
                (category,),
            )
        else:
            cursor.execute(
                "SELECT product_id, product_name, category, unit_price, reorder_level FROM products ORDER BY product_id;"
            )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_store(store_id: str, db_path: str | Path = DATABASE_PATH) -> Optional[Dict[str, Any]]:
    """Retrieve a single store by ID."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT store_id, store_name, city FROM stores WHERE store_id = ?;",
            (store_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_stores(db_path: str | Path = DATABASE_PATH) -> List[Dict[str, Any]]:
    """Retrieve all stores."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT store_id, store_name, city FROM stores ORDER BY store_id;")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_sales(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    store_id: Optional[str] = None,
    product_id: Optional[str] = None,
    limit: Optional[int] = None,
    db_path: str | Path = DATABASE_PATH,
) -> List[Dict[str, Any]]:
    """Retrieve sales records with optional date range, store, product, and limit filters."""
    query = "SELECT sale_id, date, store_id, product_id, quantity, unit_price, revenue FROM sales WHERE 1=1"
    params: List[Any] = []

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    if store_id:
        query += " AND store_id = ?"
        params.append(store_id)
    if product_id:
        query += " AND product_id = ?"
        params.append(product_id)

    query += " ORDER BY date ASC, sale_id ASC"

    if limit is not None and limit > 0:
        query += " LIMIT ?"
        params.append(limit)

    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_product_sales(
    product_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
    db_path: str | Path = DATABASE_PATH,
) -> List[Dict[str, Any]]:
    """Retrieve all sales for a given product."""
    return get_sales(
        product_id=product_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        db_path=db_path,
    )


def get_store_sales(
    store_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
    db_path: str | Path = DATABASE_PATH,
) -> List[Dict[str, Any]]:
    """Retrieve all sales for a given store."""
    return get_sales(
        store_id=store_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        db_path=db_path,
    )


def get_inventory(
    store_id: Optional[str] = None,
    product_id: Optional[str] = None,
    db_path: str | Path = DATABASE_PATH,
) -> List[Dict[str, Any]]:
    """Retrieve inventory records, optionally filtered by store or product."""
    query = "SELECT store_id, product_id, current_stock, reorder_level FROM inventory WHERE 1=1"
    params: List[Any] = []

    if store_id:
        query += " AND store_id = ?"
        params.append(store_id)
    if product_id:
        query += " AND product_id = ?"
        params.append(product_id)

    query += " ORDER BY store_id ASC, product_id ASC"

    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_product_inventory(
    product_id: str,
    db_path: str | Path = DATABASE_PATH,
) -> List[Dict[str, Any]]:
    """Retrieve inventory for a specific product across all stores."""
    return get_inventory(product_id=product_id, db_path=db_path)
