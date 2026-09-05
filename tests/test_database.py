"""Unit tests for RetailIQ SQLite data layer."""

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.database import (
    create_tables,
    get_connection,
    get_inventory,
    get_product,
    get_product_inventory,
    get_product_sales,
    get_products,
    get_sales,
    get_store,
    get_store_sales,
    get_stores,
    get_table_counts,
    init_db,
    is_database_initialized,
    load_csv_data,
)


class TestDatabaseLayer(unittest.TestCase):
    """Test suite for SQLite initialization, integrity, and parameterized queries."""

    def setUp(self) -> None:
        """Create an isolated temporary SQLite database for each test."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db_path = Path(self.temp_dir.name) / "test_retailiq.db"
        self.data_dir = Path(__file__).resolve().parent.parent / "data"

    def tearDown(self) -> None:
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_create_tables_and_indexes(self) -> None:
        """Test that all required tables and indexes are created successfully."""
        conn = get_connection(self.test_db_path)
        create_tables(conn)

        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row["name"] for row in cursor.fetchall()}
        expected_tables = {"products", "stores", "sales", "inventory"}
        self.assertTrue(expected_tables.issubset(tables))

        cursor.execute("SELECT name FROM sqlite_master WHERE type='index';")
        indexes = {row["name"] for row in cursor.fetchall()}
        expected_indexes = {
            "idx_sales_date",
            "idx_sales_product_id",
            "idx_sales_store_id",
            "idx_inventory_product_id",
            "idx_inventory_store_id",
        }
        self.assertTrue(expected_indexes.issubset(indexes))
        conn.close()

    def test_load_csv_data_and_counts(self) -> None:
        """Test loading CSV files into SQLite tables and validating row counts."""
        conn = get_connection(self.test_db_path)
        create_tables(conn)
        counts = load_csv_data(conn, data_dir=self.data_dir)

        self.assertEqual(counts["products"], 40)
        self.assertEqual(counts["stores"], 4)
        self.assertGreater(counts["sales"], 5000)
        self.assertEqual(counts["inventory"], 160)
        conn.close()

    def test_init_db_idempotence(self) -> None:
        """Test that initializing an already initialized database is safe and does not duplicate rows."""
        counts1 = init_db(db_path=self.test_db_path, data_dir=self.data_dir)
        self.assertTrue(is_database_initialized(self.test_db_path))

        # Re-run initialization
        counts2 = init_db(db_path=self.test_db_path, data_dir=self.data_dir)
        self.assertEqual(counts1, counts2)

        # Confirm counts directly from DB
        verified_counts = get_table_counts(self.test_db_path)
        self.assertEqual(verified_counts["products"], 40)
        self.assertEqual(verified_counts["stores"], 4)
        self.assertEqual(verified_counts["inventory"], 160)

    def test_foreign_key_enforcement(self) -> None:
        """Test that foreign key violations raise sqlite3.IntegrityError."""
        init_db(db_path=self.test_db_path, data_dir=self.data_dir)
        conn = get_connection(self.test_db_path)
        cursor = conn.cursor()

        # Attempt to insert a sale with a non-existent product_id
        with self.assertRaises(sqlite3.IntegrityError):
            cursor.execute(
                """
                INSERT INTO sales (sale_id, date, store_id, product_id, quantity, unit_price, revenue)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                ("SAL_INVALID", "2026-06-01", "STR001", "PRD_NONEXISTENT", 1, 100.0, 100.0),
            )
            conn.commit()

        # Attempt to insert an inventory item with a non-existent store_id
        with self.assertRaises(sqlite3.IntegrityError):
            cursor.execute(
                """
                INSERT INTO inventory (store_id, product_id, current_stock, reorder_level)
                VALUES (?, ?, ?, ?);
                """,
                ("STR_NONEXISTENT", "PRD001", 10, 5),
            )
            conn.commit()

        conn.close()

    def test_parameterized_product_queries(self) -> None:
        """Test get_product and get_products query helpers."""
        init_db(db_path=self.test_db_path, data_dir=self.data_dir)

        # Single product
        product = get_product("PRD001", db_path=self.test_db_path)
        self.assertIsNotNone(product)
        self.assertEqual(product["product_id"], "PRD001")
        self.assertEqual(product["product_name"], "Wireless Optical Mouse")
        self.assertEqual(product["category"], "Electronics")

        # Non-existent product
        missing = get_product("PRD_GHOST", db_path=self.test_db_path)
        self.assertIsNone(missing)

        # Filter by category
        electronics = get_products(category="Electronics", db_path=self.test_db_path)
        self.assertGreater(len(electronics), 0)
        for p in electronics:
            self.assertEqual(p["category"], "Electronics")

        # All products
        all_prods = get_products(db_path=self.test_db_path)
        self.assertEqual(len(all_prods), 40)

    def test_parameterized_store_queries(self) -> None:
        """Test get_store and get_stores query helpers."""
        init_db(db_path=self.test_db_path, data_dir=self.data_dir)

        store = get_store("STR001", db_path=self.test_db_path)
        self.assertIsNotNone(store)
        self.assertEqual(store["store_name"], "RetailIQ Prime - Indiranagar")
        self.assertEqual(store["city"], "Bengaluru")

        stores = get_stores(db_path=self.test_db_path)
        self.assertEqual(len(stores), 4)

    def test_parameterized_sales_queries(self) -> None:
        """Test get_sales, get_product_sales, and get_store_sales."""
        init_db(db_path=self.test_db_path, data_dir=self.data_dir)

        # All sales with limit
        sales_sample = get_sales(limit=10, db_path=self.test_db_path)
        self.assertEqual(len(sales_sample), 10)

        # Sales by date range
        date_sales = get_sales(start_date="2026-06-01", end_date="2026-06-07", db_path=self.test_db_path)
        self.assertGreater(len(date_sales), 0)
        for s in date_sales:
            self.assertTrue("2026-06-01" <= s["date"] <= "2026-06-07")

        # Product sales
        prd_sales = get_product_sales("PRD001", db_path=self.test_db_path)
        self.assertGreater(len(prd_sales), 0)
        for s in prd_sales:
            self.assertEqual(s["product_id"], "PRD001")

        # Store sales
        str_sales = get_store_sales("STR001", limit=15, db_path=self.test_db_path)
        self.assertEqual(len(str_sales), 15)
        for s in str_sales:
            self.assertEqual(s["store_id"], "STR001")

    def test_parameterized_inventory_queries(self) -> None:
        """Test get_inventory and get_product_inventory query helpers."""
        init_db(db_path=self.test_db_path, data_dir=self.data_dir)

        # All inventory
        inv_all = get_inventory(db_path=self.test_db_path)
        self.assertEqual(len(inv_all), 160)

        # Filter by store
        inv_str = get_inventory(store_id="STR001", db_path=self.test_db_path)
        self.assertEqual(len(inv_str), 40)

        # Filter by product across stores
        inv_prd = get_product_inventory("PRD001", db_path=self.test_db_path)
        self.assertEqual(len(inv_prd), 4)
        for item in inv_prd:
            self.assertEqual(item["product_id"], "PRD001")


if __name__ == "__main__":
    unittest.main()
