"""Unit tests for RetailIQ deterministic inventory intelligence engine."""

import unittest
from fastapi.testclient import TestClient

from app import app
from src.config import (
    DATABASE_PATH,
    RISK_THRESHOLD_CRITICAL,
    RISK_THRESHOLD_HIGH,
    RISK_THRESHOLD_MEDIUM,
    TARGET_REORDER_COVERAGE_DAYS,
    VELOCITY_FAST_UNITS_PER_DAY,
    VELOCITY_SLOW_UNITS_PER_DAY,
)
from src.inventory import InventoryIntelligenceEngine
from src.analytics import EntityNotFoundError


class TestInventoryIntelligenceEngine(unittest.TestCase):
    """Test suite for deterministic inventory intelligence, risk classification, and replenishment."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = InventoryIntelligenceEngine(db_path=DATABASE_PATH)
        cls.client = TestClient(app)

    # 1. Average Daily Sales
    def test_01_average_daily_sales(self) -> None:
        """Verify calculation of average daily sales over the 30-day window."""
        res = self.engine.get_average_daily_sales("PRD001", "STR001")
        self.assertEqual(res["product_id"], "PRD001")
        self.assertEqual(res["store_id"], "STR001")
        self.assertEqual(res["demand_window_days"], 30)
        self.assertGreater(res["total_units_sold"], 0)
        self.assertEqual(res["average_daily_sales"], round(res["total_units_sold"] / 30, 2))
        self.assertEqual(res["status"], "normal")

    # 2. Inventory Coverage
    def test_02_inventory_coverage_calculation(self) -> None:
        """Verify days of coverage formula: Current Stock / Avg Daily Sales."""
        cov, status = self.engine.calculate_inventory_coverage(current_stock=20, average_daily_sales=5.0)
        self.assertEqual(cov, 4.0)
        self.assertEqual(status, "normal")

        # Non-integer rounding check
        cov2, _ = self.engine.calculate_inventory_coverage(current_stock=18, average_daily_sales=5.0)
        self.assertEqual(cov2, 3.6)

    # 3. Critical Stock-Out Risk (< 3 days)
    def test_03_critical_stockout_risk(self) -> None:
        """Verify critical risk classification when coverage is under 3 days or stock is 0."""
        level, thresh = self.engine.assess_stockout_risk(days_of_coverage=2.4, current_stock=12)
        self.assertEqual(level, "CRITICAL")
        self.assertEqual(thresh, RISK_THRESHOLD_CRITICAL)

        # Zero stock is always critical
        level0, _ = self.engine.assess_stockout_risk(days_of_coverage=0.0, current_stock=0)
        self.assertEqual(level0, "CRITICAL")

    # 4. High Stock-Out Risk (3 - 7 days)
    def test_04_high_stockout_risk(self) -> None:
        """Verify high risk classification when coverage is between 3 and 7 days."""
        level, thresh = self.engine.assess_stockout_risk(days_of_coverage=4.5, current_stock=20)
        self.assertEqual(level, "HIGH")
        self.assertEqual(thresh, RISK_THRESHOLD_HIGH)

    # 5. Medium Risk (7 - 14 days)
    def test_05_medium_risk(self) -> None:
        """Verify medium risk classification when coverage is between 7 and 14 days."""
        level, thresh = self.engine.assess_stockout_risk(days_of_coverage=10.0, current_stock=30)
        self.assertEqual(level, "MEDIUM")
        self.assertEqual(thresh, RISK_THRESHOLD_MEDIUM)

    # 6. Safe Inventory (> 14 days)
    def test_06_safe_inventory(self) -> None:
        """Verify low risk classification when coverage exceeds 14 days."""
        level, _ = self.engine.assess_stockout_risk(days_of_coverage=25.0, current_stock=50)
        self.assertEqual(level, "LOW")

    # 7. Zero Demand (No division by zero)
    def test_07_zero_demand_handling(self) -> None:
        """Verify safe handling when average daily sales is zero without dividing by zero."""
        cov, status = self.engine.calculate_inventory_coverage(current_stock=50, average_daily_sales=0.0)
        self.assertIsNone(cov)
        self.assertEqual(status, "no_recent_demand")

        level, _ = self.engine.assess_stockout_risk(days_of_coverage=cov, current_stock=50, status=status)
        self.assertEqual(level, "NO_DEMAND")

    # 8. Reorder Calculation
    def test_08_reorder_recommendation(self) -> None:
        """Verify deterministic reorder calculation."""
        # Case A: Stock is below target
        rec = self.engine.get_reorder_recommendation(
            current_stock=12, average_daily_sales=4.0, target_days=21.0, reorder_level=25
        )
        # target_stock = round(4.0 * 21) = 84 (greater than reorder_level 25)
        self.assertEqual(rec["target_stock_units"], 84)
        self.assertEqual(rec["recommended_reorder_quantity"], 72)
        self.assertTrue(rec["replenishment_needed"])

        # Case B: Stock exceeds target
        rec2 = self.engine.get_reorder_recommendation(
            current_stock=100, average_daily_sales=2.0, target_days=21.0, reorder_level=20
        )
        self.assertEqual(rec2["recommended_reorder_quantity"], 0)
        self.assertFalse(rec2["replenishment_needed"])

    # 9. Overstock Detection
    def test_09_overstock_detection(self) -> None:
        """Verify detection of items with excessive coverage and excess unit estimates."""
        overstocked = self.engine.get_overstocked_products(threshold_days=30.0)
        self.assertGreaterEqual(len(overstocked), 3)

        for item in overstocked:
            self.assertGreater(item["current_stock"], 0)
            self.assertGreater(item["excess_inventory_units"], 0)
            self.assertGreater(item["excess_capital_inr"], 0.0)
            self.assertIn(item["severity"], ("CRITICAL", "HIGH", "MODERATE"))

    # 10. Fast-Moving & 11. Slow-Moving Classification
    def test_10_and_11_velocity_classification(self) -> None:
        """Verify products are partitioned into Fast, Medium, and Slow tiers."""
        velocities = self.engine.classify_product_velocities()
        counts = velocities["counts"]

        self.assertGreaterEqual(counts["fast"], 3)
        self.assertGreaterEqual(counts["medium"], 5)
        self.assertGreaterEqual(counts["slow"], 3)
        self.assertEqual(counts["total"], 40)

        # Fast products have daily sales >= VELOCITY_FAST_UNITS_PER_DAY
        for p in velocities["fast_moving"]:
            self.assertGreaterEqual(p["average_daily_sales"], VELOCITY_FAST_UNITS_PER_DAY)

        # Slow products have daily sales < VELOCITY_SLOW_UNITS_PER_DAY
        for p in velocities["slow_moving"]:
            self.assertLess(p["average_daily_sales"], VELOCITY_SLOW_UNITS_PER_DAY)

    # 12. Inventory Health Summary
    def test_12_inventory_health_summary(self) -> None:
        """Verify portfolio-wide inventory health summary."""
        summary = self.engine.get_inventory_health_summary()
        self.assertEqual(summary["total_inventory_records"], 160)
        self.assertGreater(summary["total_stock_units"], 1000)
        self.assertGreater(summary["total_stock_value_inr"], 500_000.0)

        dist = summary["risk_distribution"]
        total_accounted = sum(dist.values())
        self.assertEqual(total_accounted, 160)

        pcts = summary["percentages"]
        self.assertGreater(pcts["healthy_pct"], 50.0)

    # 13. Attention Items
    def test_13_attention_items(self) -> None:
        """Verify prioritized attention items combining stock-out, overstock, spike, and drop."""
        items = self.engine.get_attention_items(limit=15)
        self.assertGreater(len(items), 0)

        types_found = {it["type"] for it in items}
        self.assertTrue({"STOCK_OUT", "OVERSTOCK"}.issubset(types_found))

        for it in items:
            self.assertIn(it["severity"], ("CRITICAL", "HIGH", "MEDIUM", "MODERATE"))
            self.assertIn("title", it)
            self.assertIn("evidence", it)
            self.assertIn("recommended_action", it)

    # 14. Unknown Product Error Handling
    def test_14_unknown_product(self) -> None:
        """Verify querying non-existent product raises EntityNotFoundError."""
        with self.assertRaises(EntityNotFoundError):
            self.engine.get_average_daily_sales("PRD_GHOST", "STR001")

        with self.assertRaises(EntityNotFoundError):
            self.engine.get_product_inventory_detail("PRD_GHOST")

    # 15. Unknown Store Error Handling
    def test_15_unknown_store(self) -> None:
        """Verify querying non-existent store raises EntityNotFoundError."""
        with self.assertRaises(EntityNotFoundError):
            self.engine.get_average_daily_sales("PRD001", "STR_GHOST")

        with self.assertRaises(EntityNotFoundError):
            self.engine.get_products_at_risk(store_id="STR_GHOST")

        with self.assertRaises(EntityNotFoundError):
            self.engine.get_overstocked_products(store_id="STR_GHOST")

    # 16. Insufficient Data Window Handling
    def test_16_demand_window_and_edge_cases(self) -> None:
        """Verify demand window computation and negative stock defense."""
        start_d, end_d, days = self.engine.get_demand_window()
        self.assertEqual(days, 30)
        self.assertTrue(start_d < end_d)

        # Defense against negative stock
        cov, status = self.engine.calculate_inventory_coverage(current_stock=-5, average_daily_sales=2.0)
        self.assertEqual(status, "invalid_stock")

    # 17. Scenario Verification in Synthetic Dataset
    def test_17_verify_synthetic_scenarios(self) -> None:
        """Verify presence of all planned scenarios in the synthetic dataset."""
        # Scenario A: At least 3 stock-out risks
        critical_risks = self.engine.get_products_at_risk(risk_level="CRITICAL")
        self.assertGreaterEqual(len(critical_risks), 3)

        # Scenario B: At least 3 overstock scenarios
        overstock_cases = self.engine.get_overstocked_products(threshold_days=60.0)
        self.assertGreaterEqual(len(overstock_cases), 3)

        # Scenario C: Attention items contains spike or drop
        attention = self.engine.get_attention_items(limit=25)
        att_types = {a["type"] for a in attention}
        self.assertTrue("SALES_SPIKE" in att_types or "SALES_DROP" in att_types)

    # 18. API Endpoint Verification
    def test_18_inventory_api_endpoints(self) -> None:
        """Verify all REST API inventory endpoints return 200 with structured JSON."""
        # Health
        r1 = self.client.get("/api/inventory/health")
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()["total_inventory_records"], 160)

        # Risks
        r2 = self.client.get("/api/inventory/risks?risk_level=CRITICAL")
        self.assertEqual(r2.status_code, 200)
        self.assertGreaterEqual(len(r2.json()), 3)

        # Overstock
        r3 = self.client.get("/api/inventory/overstock")
        self.assertEqual(r3.status_code, 200)
        self.assertGreaterEqual(len(r3.json()), 3)

        # Attention
        r4 = self.client.get("/api/inventory/attention?limit=5")
        self.assertEqual(r4.status_code, 200)
        self.assertEqual(len(r4.json()), 5)

        # Velocity
        r5 = self.client.get("/api/inventory/velocity")
        self.assertEqual(r5.status_code, 200)
        self.assertEqual(r5.json()["counts"]["total"], 40)

        # Product Detail
        r6 = self.client.get("/api/inventory/PRD001")
        self.assertEqual(r6.status_code, 200)
        self.assertEqual(r6.json()["product_id"], "PRD001")
        self.assertEqual(len(r6.json()["stores"]), 4)


if __name__ == "__main__":
    unittest.main()
