"""Unit tests for RetailIQ deterministic sales analytics engine."""

import unittest
from fastapi.testclient import TestClient

from app import app
from src.analytics import (
    EntityNotFoundError,
    InvalidDateRangeError,
    SalesAnalyticsEngine,
)
from src.config import DATABASE_PATH


class TestSalesAnalyticsEngine(unittest.TestCase):
    """Test suite for deterministic sales analytics calculations."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = SalesAnalyticsEngine(db_path=DATABASE_PATH)
        cls.client = TestClient(app)

    # 1. Overall sales summary
    def test_01_overall_sales_summary(self) -> None:
        """Verify overall sales summary returns expected structured metrics."""
        summary = self.engine.get_sales_summary()
        self.assertTrue(summary["has_data"])
        self.assertGreater(summary["total_revenue"], 10_000_000.0)
        self.assertGreater(summary["total_units_sold"], 20_000)
        self.assertGreater(summary["total_transactions"], 5_000)
        self.assertEqual(summary["active_selling_days"], 120)
        self.assertGreater(summary["average_daily_revenue"], 0.0)
        self.assertGreater(summary["average_daily_units_sold"], 0.0)
        self.assertGreater(summary["average_order_value"], 0.0)

    # 2. Product performance
    def test_02_product_performance(self) -> None:
        """Verify performance metrics for a known product."""
        res = self.engine.get_product_performance("PRD001")
        self.assertTrue(res["has_data"])
        self.assertEqual(res["product_id"], "PRD001")
        self.assertEqual(res["product_name"], "Wireless Optical Mouse")
        self.assertEqual(res["category"], "Electronics")
        self.assertEqual(res["unit_price"], 599.0)
        self.assertGreater(res["total_units_sold"], 0)
        self.assertEqual(res["total_revenue"], round(res["total_units_sold"] * 599.0, 2))
        self.assertEqual(res["selling_days"], 120)

    # 3. Store performance
    def test_03_store_performance(self) -> None:
        """Verify performance metrics for a known store."""
        res = self.engine.get_store_performance("STR001")
        self.assertTrue(res["has_data"])
        self.assertEqual(res["store_id"], "STR001")
        self.assertEqual(res["store_name"], "RetailIQ Prime - Indiranagar")
        self.assertEqual(res["city"], "Bengaluru")
        self.assertGreater(res["total_revenue"], 0.0)
        self.assertGreater(res["total_units_sold"], 0)
        self.assertEqual(res["active_selling_days"], 120)

    # 4. Product comparison
    def test_04_product_comparison(self) -> None:
        """Verify multi-product comparison assigns correct revenue and unit ranks."""
        res = self.engine.compare_products(["PRD001", "PRD002", "PRD003"])
        self.assertEqual(res["total_products_compared"], 3)
        products = res["products"]
        self.assertEqual(len(products), 3)

        # Ensure rankings are 1, 2, 3
        rev_ranks = [p["rank_revenue"] for p in products]
        unit_ranks = [p["rank_units"] for p in products]
        self.assertEqual(sorted(rev_ranks), [1, 2, 3])
        self.assertEqual(sorted(unit_ranks), [1, 2, 3])

        # Revenue of rank 1 >= rank 2 >= rank 3
        self.assertGreaterEqual(products[0]["revenue"], products[1]["revenue"])
        self.assertGreaterEqual(products[1]["revenue"], products[2]["revenue"])

    # 5. Store comparison
    def test_05_store_comparison(self) -> None:
        """Verify store comparison across all 4 stores."""
        res = self.engine.compare_stores()
        self.assertEqual(res["total_stores_compared"], 4)
        stores = res["stores"]
        self.assertEqual(len(stores), 4)
        rev_ranks = [s["rank_revenue"] for s in stores]
        self.assertEqual(sorted(rev_ranks), [1, 2, 3, 4])

    # 6. Category performance
    def test_06_category_performance(self) -> None:
        """Verify category breakdown and percentage contribution."""
        res = self.engine.get_category_performance()
        categories = res["categories"]
        self.assertEqual(len(categories), 6)

        # Sum of percentages should be approximately 100%
        total_pct = sum(c["revenue_percentage"] for c in categories)
        self.assertAlmostEqual(total_pct, 100.0, delta=0.5)

        # Total revenue matches sum of categories
        cat_rev_sum = round(sum(c["revenue"] for c in categories), 2)
        self.assertEqual(cat_rev_sum, res["total_revenue"])

    # 7. Period comparison & 8. Growth calculation
    def test_07_and_08_period_comparison_and_growth(self) -> None:
        """Verify period comparison and growth percentage formula."""
        res = self.engine.compare_periods(
            current_start="2026-08-01",
            current_end="2026-08-31",
            previous_start="2026-07-01",
            previous_end="2026-07-31",
        )

        curr_rev = res["current_period"]["revenue"]
        prev_rev = res["previous_period"]["revenue"]
        expected_rev_change = round(curr_rev - prev_rev, 2)
        self.assertEqual(res["revenue_change"], expected_rev_change)

        expected_growth = round(((curr_rev - prev_rev) / prev_rev) * 100.0, 2)
        self.assertEqual(res["revenue_growth_percentage"], expected_growth)
        self.assertFalse(res["zero_baseline"]["previous_revenue_is_zero"])

    # 9. Zero previous-period handling
    def test_09_zero_previous_period_handling(self) -> None:
        """Verify zero baseline in previous period is handled safely without division by zero."""
        # Using a date range in 2020 where no records exist
        res = self.engine.compare_periods(
            current_start="2026-08-01",
            current_end="2026-08-31",
            previous_start="2020-01-01",
            previous_end="2020-01-31",
        )
        self.assertEqual(res["previous_period"]["revenue"], 0.0)
        self.assertTrue(res["zero_baseline"]["previous_revenue_is_zero"])
        self.assertEqual(res["revenue_growth_percentage"], 100.0)

    # 10. Daily trend
    def test_10_daily_trend(self) -> None:
        """Verify daily sales trend is sorted chronologically."""
        res = self.engine.get_sales_trend(start_date="2026-06-01", end_date="2026-06-15")
        points = res["trend"]
        self.assertEqual(len(points), 15)

        # Check chronology
        dates = [p["date"] for p in points]
        self.assertEqual(dates, sorted(dates))

        # Check positive metrics
        for p in points:
            self.assertGreater(p["revenue"], 0.0)
            self.assertGreater(p["units"], 0)

    # 11. Top products
    def test_11_top_products(self) -> None:
        """Verify top products function by revenue and units."""
        top_rev = self.engine.get_top_products(by="revenue", limit=5)
        self.assertEqual(len(top_rev["top_products"]), 5)
        for i in range(len(top_rev["top_products"]) - 1):
            self.assertGreaterEqual(
                top_rev["top_products"][i]["revenue"],
                top_rev["top_products"][i + 1]["revenue"],
            )

        top_units = self.engine.get_top_products(by="units", limit=5)
        self.assertEqual(len(top_units["top_products"]), 5)
        for i in range(len(top_units["top_products"]) - 1):
            self.assertGreaterEqual(
                top_units["top_products"][i]["units_sold"],
                top_units["top_products"][i + 1]["units_sold"],
            )

    # 12. Unknown product error handling
    def test_12_unknown_product(self) -> None:
        """Verify querying non-existent product raises EntityNotFoundError."""
        with self.assertRaises(EntityNotFoundError):
            self.engine.get_product_performance("PRD_NONEXISTENT")

        with self.assertRaises(EntityNotFoundError):
            self.engine.get_store_product_performance("PRD_NONEXISTENT")

    # 13. Unknown store error handling
    def test_13_unknown_store(self) -> None:
        """Verify querying non-existent store raises EntityNotFoundError."""
        with self.assertRaises(EntityNotFoundError):
            self.engine.get_store_performance("STR_NONEXISTENT")

        with self.assertRaises(EntityNotFoundError):
            self.engine.get_sales_summary(store_id="STR_NONEXISTENT")

    # 14. Empty date range handling
    def test_14_empty_date_range(self) -> None:
        """Verify requesting a date range outside dataset returns has_data: False without error."""
        res = self.engine.get_sales_summary(start_date="2020-01-01", end_date="2020-01-10")
        self.assertFalse(res["has_data"])
        self.assertEqual(res["total_revenue"], 0.0)
        self.assertEqual(res["total_units_sold"], 0)
        self.assertEqual(res["total_transactions"], 0)
        self.assertEqual(res["average_daily_revenue"], 0.0)

    # 15. Invalid date range (start > end)
    def test_15_invalid_date_range(self) -> None:
        """Verify invalid date range raises InvalidDateRangeError."""
        with self.assertRaises(InvalidDateRangeError):
            self.engine.get_sales_summary(start_date="2026-08-31", end_date="2026-08-01")

    # 16. Store-Product Affinity analysis ("Which store sells this product best?")
    def test_16_store_product_best_seller(self) -> None:
        """Verify store breakdown for product answers which store sells best."""
        res = self.engine.get_store_product_performance("PRD010")
        self.assertEqual(res["product_id"], "PRD010")
        self.assertEqual(res["best_store_by_units"], "RetailIQ Prime - Indiranagar")
        self.assertEqual(res["best_store_by_revenue"], "RetailIQ Prime - Indiranagar")

    # 17. API Endpoint Integration tests
    def test_17_api_analytics_endpoints(self) -> None:
        """Verify REST API analytics endpoints return 200 with structured JSON."""
        # Summary
        r1 = self.client.get("/api/analytics/summary")
        self.assertEqual(r1.status_code, 200)
        self.assertTrue(r1.json()["has_data"])

        # Product
        r2 = self.client.get("/api/analytics/products/PRD001")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["product_id"], "PRD001")

        # Unknown product 404
        r2_err = self.client.get("/api/analytics/products/PRD_GHOST")
        self.assertEqual(r2_err.status_code, 404)

        # Store
        r3 = self.client.get("/api/analytics/stores/STR001")
        self.assertEqual(r3.status_code, 200)
        self.assertEqual(r3.json()["store_id"], "STR001")

        # Trend
        r4 = self.client.get("/api/analytics/trend?start_date=2026-06-01&end_date=2026-06-05")
        self.assertEqual(r4.status_code, 200)
        self.assertEqual(len(r4.json()["trend"]), 5)

        # Top products
        r5 = self.client.get("/api/analytics/top-products?by=revenue&limit=3")
        self.assertEqual(r5.status_code, 200)
        self.assertEqual(len(r5.json()["top_products"]), 3)

        # Categories
        r6 = self.client.get("/api/analytics/categories")
        self.assertEqual(r6.status_code, 200)
        self.assertEqual(len(r6.json()["categories"]), 6)


if __name__ == "__main__":
    unittest.main()
