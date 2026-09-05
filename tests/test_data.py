"""Automated validation test suite for RetailIQ synthetic datasets.

Validates:
1. Schema validation (required columns in all CSVs)
2. Referential integrity (products, stores, sales, inventory)
3. Revenue calculation (revenue == quantity * unit_price)
4. Positive quantities
5. Positive prices
6. Valid dates (ISO format YYYY-MM-DD, 120-day historical span)
7. Inventory references (every store-product combination present)
8. Intentional retail scenario presence:
   - Stock-out risks (at least 3 store/product pairs with < 4 days coverage)
   - Overstock (at least 3 store/product pairs with > 60 days coverage)
   - Sales spikes (at least 2 products with recent sales spike vs baseline)
   - Sales drops (at least 2 products with recent sales decline vs baseline)
   - Store-specific performance variations
   - Product demand diversity (fast, medium, slow moving products)
"""

import unittest
from datetime import datetime
from pathlib import Path
import pandas as pd
import numpy as np


class TestSyntheticRetailData(unittest.TestCase):
    """Test suite validating data quality and scenario coverage in RetailIQ datasets."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.data_dir = Path(__file__).resolve().parent.parent / "data"
        cls.products_path = cls.data_dir / "products.csv"
        cls.stores_path = cls.data_dir / "stores.csv"
        cls.sales_path = cls.data_dir / "sales.csv"
        cls.inventory_path = cls.data_dir / "inventory.csv"

        cls.products = pd.read_csv(cls.products_path)
        cls.stores = pd.read_csv(cls.stores_path)
        cls.sales = pd.read_csv(cls.sales_path)
        cls.inventory = pd.read_csv(cls.inventory_path)

    # 1. Schema validation
    def test_schema_products(self) -> None:
        """Validate products.csv schema and catalog size."""
        expected_cols = {"product_id", "product_name", "category", "unit_price", "reorder_level"}
        self.assertTrue(expected_cols.issubset(set(self.products.columns)))
        self.assertGreaterEqual(len(self.products), 35)
        self.assertLessEqual(len(self.products), 45)
        self.assertEqual(self.products["product_id"].nunique(), len(self.products))

    def test_schema_stores(self) -> None:
        """Validate stores.csv schema and store count."""
        expected_cols = {"store_id", "store_name", "city"}
        self.assertTrue(expected_cols.issubset(set(self.stores.columns)))
        self.assertEqual(len(self.stores), 4)
        self.assertEqual(self.stores["store_id"].nunique(), 4)

    def test_schema_sales(self) -> None:
        """Validate sales.csv schema and record count."""
        expected_cols = {"sale_id", "date", "store_id", "product_id", "quantity", "unit_price", "revenue"}
        self.assertTrue(expected_cols.issubset(set(self.sales.columns)))
        self.assertGreater(len(self.sales), 5000)
        self.assertEqual(self.sales["sale_id"].nunique(), len(self.sales))

    def test_schema_inventory(self) -> None:
        """Validate inventory.csv schema."""
        expected_cols = {"store_id", "product_id", "current_stock", "reorder_level"}
        self.assertTrue(expected_cols.issubset(set(self.inventory.columns)))
        expected_count = len(self.stores) * len(self.products)
        self.assertEqual(len(self.inventory), expected_count)

    # 2. Referential integrity
    def test_referential_integrity_sales(self) -> None:
        """Ensure all product_ids and store_ids in sales exist in catalog."""
        product_ids = set(self.products["product_id"])
        store_ids = set(self.stores["store_id"])

        sales_product_ids = set(self.sales["product_id"])
        sales_store_ids = set(self.sales["store_id"])

        self.assertTrue(sales_product_ids.issubset(product_ids))
        self.assertTrue(sales_store_ids.issubset(store_ids))

    def test_referential_integrity_inventory(self) -> None:
        """Ensure all product_ids and store_ids in inventory exist in catalog."""
        product_ids = set(self.products["product_id"])
        store_ids = set(self.stores["store_id"])

        inv_product_ids = set(self.inventory["product_id"])
        inv_store_ids = set(self.inventory["store_id"])

        self.assertTrue(inv_product_ids.issubset(product_ids))
        self.assertTrue(inv_store_ids.issubset(store_ids))

        # Check every store-product pair exists exactly once
        inv_pairs = list(zip(self.inventory["store_id"], self.inventory["product_id"]))
        self.assertEqual(len(inv_pairs), len(set(inv_pairs)))

    # 3. Revenue calculation
    def test_revenue_calculation(self) -> None:
        """Ensure revenue equals quantity * unit_price within floating point tolerance."""
        calculated_rev = (self.sales["quantity"] * self.sales["unit_price"]).round(2)
        actual_rev = self.sales["revenue"].round(2)
        diff = (calculated_rev - actual_rev).abs().max()
        self.assertLess(diff, 0.02)

    # 4. Positive quantities & non-negative inventory
    def test_positive_quantities(self) -> None:
        """Ensure sales quantities are strictly positive integers."""
        self.assertTrue((self.sales["quantity"] > 0).all())
        self.assertTrue((self.inventory["current_stock"] >= 0).all())
        self.assertTrue((self.inventory["reorder_level"] > 0).all())

    # 5. Positive prices
    def test_positive_prices(self) -> None:
        """Ensure prices are strictly positive."""
        self.assertTrue((self.products["unit_price"] > 0).all())
        self.assertTrue((self.sales["unit_price"] > 0).all())

    # 6. Valid dates and historical span
    def test_valid_dates(self) -> None:
        """Validate date format and historical period length."""
        parsed_dates = pd.to_datetime(self.sales["date"], format="%Y-%m-%d")
        min_date = parsed_dates.min()
        max_date = parsed_dates.max()
        date_span_days = (max_date - min_date).days + 1
        self.assertGreaterEqual(date_span_days, 115)
        self.assertLessEqual(date_span_days, 125)

    # 7. Categories & diverse price range
    def test_categories_and_pricing(self) -> None:
        """Ensure all 6 retail categories are populated with realistic INR pricing."""
        expected_categories = {"Electronics", "Accessories", "Home", "Personal Care", "Office", "Grocery"}
        present_categories = set(self.products["category"])
        self.assertTrue(expected_categories.issubset(present_categories))
        self.assertGreaterEqual(self.products["unit_price"].min(), 50.0)
        self.assertLessEqual(self.products["unit_price"].max(), 10000.0)

    # 8. Scenario Presence Tests
    def test_scenario_stockout_risk(self) -> None:
        """At least 3 store/product combinations should have stockout risk (coverage < 4 days)."""
        # Calculate daily sales per store/product across the 120-day period
        num_days = self.sales["date"].nunique()
        sales_agg = self.sales.groupby(["store_id", "product_id"])["quantity"].sum().reset_index()
        sales_agg["daily_rate"] = sales_agg["quantity"] / num_days

        merged = pd.merge(self.inventory, sales_agg, on=["store_id", "product_id"], how="left")
        merged["daily_rate"] = merged["daily_rate"].fillna(0.1)
        merged["coverage_days"] = merged["current_stock"] / merged["daily_rate"]

        stockout_risks = merged[merged["coverage_days"] < 4.0]
        self.assertGreaterEqual(len(stockout_risks), 3)

    def test_scenario_overstock(self) -> None:
        """At least 3 store/product combinations should have overstock (coverage > 60 days)."""
        num_days = self.sales["date"].nunique()
        sales_agg = self.sales.groupby(["store_id", "product_id"])["quantity"].sum().reset_index()
        sales_agg["daily_rate"] = sales_agg["quantity"] / num_days

        merged = pd.merge(self.inventory, sales_agg, on=["store_id", "product_id"], how="left")
        merged["daily_rate"] = merged["daily_rate"].fillna(0.1)
        merged["coverage_days"] = merged["current_stock"] / merged["daily_rate"]

        overstocked = merged[merged["coverage_days"] > 60.0]
        self.assertGreaterEqual(len(overstocked), 3)

    def test_scenario_sales_spikes(self) -> None:
        """At least 2 products should experience a noticeable recent sales spike."""
        sales_sorted = self.sales.sort_values("date")
        dates = sorted(sales_sorted["date"].unique())
        split_date = dates[-18]  # last 18 days vs baseline

        baseline_sales = sales_sorted[sales_sorted["date"] < split_date]
        recent_sales = sales_sorted[sales_sorted["date"] >= split_date]

        baseline_rate = baseline_sales.groupby("product_id")["quantity"].sum() / (len(dates) - 18)
        recent_rate = recent_sales.groupby("product_id")["quantity"].sum() / 18

        growth_ratio = recent_rate / baseline_rate
        spiked_products = growth_ratio[growth_ratio >= 1.75]
        self.assertGreaterEqual(len(spiked_products), 2)

    def test_scenario_sales_drops(self) -> None:
        """At least 2 products should experience a noticeable recent sales decline."""
        sales_sorted = self.sales.sort_values("date")
        dates = sorted(sales_sorted["date"].unique())
        split_date = dates[-25]  # last 25 days vs baseline

        baseline_sales = sales_sorted[sales_sorted["date"] < split_date]
        recent_sales = sales_sorted[sales_sorted["date"] >= split_date]

        baseline_rate = baseline_sales.groupby("product_id")["quantity"].sum() / (len(dates) - 25)
        recent_rate = recent_sales.groupby("product_id")["quantity"].sum() / 25

        decline_ratio = recent_rate / baseline_rate
        dropped_products = decline_ratio[decline_ratio <= 0.40]
        self.assertGreaterEqual(len(dropped_products), 2)

    def test_scenario_store_specific_performance(self) -> None:
        """Some products should perform substantially better in one store than another."""
        store_prod_sales = self.sales.groupby(["product_id", "store_id"])["quantity"].sum().unstack().fillna(0)
        # Check ratio of max store sales to min store sales for laptop stand (PRD010) or arabica coffee (PRD035)
        ratio_laptop_stand = store_prod_sales.loc["PRD010"].max() / max(1, store_prod_sales.loc["PRD010"].min())
        self.assertGreater(ratio_laptop_stand, 2.5)

    def test_scenario_demand_diversity(self) -> None:
        """Ensure diverse mix of fast-moving, medium-moving, and slow-moving products."""
        prod_totals = self.sales.groupby("product_id")["quantity"].sum()
        fast_moving = prod_totals[prod_totals > 1200]
        medium_moving = prod_totals[(prod_totals >= 400) & (prod_totals <= 1200)]
        slow_moving = prod_totals[prod_totals < 400]

        self.assertGreaterEqual(len(fast_moving), 5)
        self.assertGreaterEqual(len(medium_moving), 10)
        self.assertGreaterEqual(len(slow_moving), 4)


if __name__ == "__main__":
    unittest.main()
