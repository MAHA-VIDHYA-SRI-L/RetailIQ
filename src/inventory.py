"""Deterministic Inventory Intelligence Engine for RetailIQ.

All inventory analytics, coverage calculations, risk assessments, and reorder recommendations
are executed deterministically in Python/SQL without reliance on LLMs.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.config import (
    DATABASE_PATH,
    INVENTORY_DEMAND_WINDOW_DAYS,
    OVERSTOCK_CRITICAL_DAYS,
    OVERSTOCK_THRESHOLD_DAYS,
    RISK_THRESHOLD_CRITICAL,
    RISK_THRESHOLD_HIGH,
    RISK_THRESHOLD_MEDIUM,
    TARGET_REORDER_COVERAGE_DAYS,
    VELOCITY_FAST_UNITS_PER_DAY,
    VELOCITY_SLOW_UNITS_PER_DAY,
)
from src.database import get_connection, get_product, get_store
from src.analytics import EntityNotFoundError, SalesAnalyticsEngine


class InventoryIntelligenceEngine:
    """Core deterministic engine for retail inventory health, risks, and replenishment."""

    def __init__(
        self,
        db_path: str | Path = DATABASE_PATH,
        demand_window_days: int = INVENTORY_DEMAND_WINDOW_DAYS,
    ) -> None:
        self.db_path = db_path
        self.demand_window_days = demand_window_days
        self.sales_engine = SalesAnalyticsEngine(db_path=self.db_path)

    # --------------------------------------------------------------------------
    # 1. Historical Demand Window
    # --------------------------------------------------------------------------

    def get_demand_window(self, window_days: Optional[int] = None) -> Tuple[str, str, int]:
        """Determine demand window dates based on available historical sales.

        Returns (start_date, end_date, days_count).
        """
        days = window_days or self.demand_window_days
        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(date) as max_date, MIN(date) as min_date FROM sales;")
            row = cursor.fetchone()
            if not row or not row["max_date"]:
                return "", "", 0

            max_date_str = row["max_date"]
            min_date_str = row["min_date"]

            dt_max = datetime.strptime(max_date_str, "%Y-%m-%d").date()
            dt_min = datetime.strptime(min_date_str, "%Y-%m-%d").date()

            dt_start = max(dt_min, dt_max - timedelta(days=days - 1))
            actual_days = (dt_max - dt_start).days + 1

            return dt_start.isoformat(), dt_max.isoformat(), actual_days
        finally:
            conn.close()

    # --------------------------------------------------------------------------
    # 2. Average Daily Sales & Coverage
    # --------------------------------------------------------------------------

    def get_average_daily_sales(
        self,
        product_id: str,
        store_id: str,
        window_days: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Calculate average daily sales for a product/store pair over the demand window."""
        product = get_product(product_id, db_path=self.db_path)
        if not product:
            raise EntityNotFoundError(f"Product '{product_id}' not found.")

        store = get_store(store_id, db_path=self.db_path)
        if not store:
            raise EntityNotFoundError(f"Store '{store_id}' not found.")

        start_date, end_date, actual_days = self.get_demand_window(window_days)
        if actual_days == 0:
            return {
                "product_id": product_id,
                "store_id": store_id,
                "average_daily_sales": 0.0,
                "total_units_sold": 0,
                "demand_window_days": 0,
                "status": "insufficient_history",
                "window": {"start_date": "", "end_date": ""},
            }

        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COALESCE(SUM(quantity), 0) as units_sold
                FROM sales
                WHERE product_id = ? AND store_id = ? AND date >= ? AND date <= ?;
                """,
                (product_id, store_id, start_date, end_date),
            )
            row = cursor.fetchone()
            units_sold = int(row["units_sold"]) if row else 0
            avg_daily = round(units_sold / actual_days, 2) if actual_days > 0 else 0.0
            status = "normal" if units_sold > 0 else "no_recent_demand"

            return {
                "product_id": product_id,
                "store_id": store_id,
                "average_daily_sales": avg_daily,
                "total_units_sold": units_sold,
                "demand_window_days": actual_days,
                "status": status,
                "window": {"start_date": start_date, "end_date": end_date},
            }
        finally:
            conn.close()

    def calculate_inventory_coverage(
        self, current_stock: int, average_daily_sales: float
    ) -> Tuple[Optional[float], str]:
        """Safely calculate days of inventory coverage without division by zero.

        Returns (days_of_coverage, status).
        """
        if current_stock < 0:
            return 0.0, "invalid_stock"

        if average_daily_sales <= 0.0:
            if current_stock == 0:
                return 0.0, "out_of_stock_no_demand"
            return None, "no_recent_demand"

        days = round(current_stock / average_daily_sales, 1)
        return days, "normal"

    # --------------------------------------------------------------------------
    # 3. Stock-Out Risk Assessment
    # --------------------------------------------------------------------------

    def assess_stockout_risk(
        self, days_of_coverage: Optional[float], current_stock: int, status: str = "normal"
    ) -> Tuple[str, float]:
        """Classify inventory risk based on configured coverage thresholds."""
        if current_stock == 0:
            return "CRITICAL", 0.0

        if status == "no_recent_demand":
            return "NO_DEMAND", 0.0

        if days_of_coverage is None:
            return "UNKNOWN", 0.0

        if days_of_coverage < RISK_THRESHOLD_CRITICAL:
            return "CRITICAL", RISK_THRESHOLD_CRITICAL
        if days_of_coverage < RISK_THRESHOLD_HIGH:
            return "HIGH", RISK_THRESHOLD_HIGH
        if days_of_coverage < RISK_THRESHOLD_MEDIUM:
            return "MEDIUM", RISK_THRESHOLD_MEDIUM
        return "LOW", RISK_THRESHOLD_MEDIUM

    # --------------------------------------------------------------------------
    # 4. Reorder Recommendation
    # --------------------------------------------------------------------------

    def get_reorder_recommendation(
        self,
        current_stock: int,
        average_daily_sales: float,
        target_days: float = TARGET_REORDER_COVERAGE_DAYS,
        reorder_level: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Calculate deterministic replenishment recommendation."""
        target_stock = int(round(average_daily_sales * target_days))
        if reorder_level is not None:
            target_stock = max(target_stock, reorder_level)

        recommended_qty = max(0, target_stock - current_stock)

        return {
            "target_coverage_days": target_days,
            "target_stock_units": target_stock,
            "current_stock": current_stock,
            "average_daily_sales": average_daily_sales,
            "reorder_threshold": reorder_level,
            "recommended_reorder_quantity": recommended_qty,
            "replenishment_needed": recommended_qty > 0,
            "logic": (
                f"Target Stock = max(reorder_level, round(Avg Daily Sales × {target_days} days)). "
                f"Reorder Qty = max(0, Target Stock - Current Stock)"
            ),
        }

    # --------------------------------------------------------------------------
    # 5. Products at Risk
    # --------------------------------------------------------------------------

    def get_products_at_risk(
        self,
        store_id: Optional[str] = None,
        risk_level: Optional[str] = None,
        category: Optional[str] = None,
        min_severity: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Identify product/store pairs currently at stock-out risk, sorted by urgency."""
        if store_id and not get_store(store_id, db_path=self.db_path):
            raise EntityNotFoundError(f"Store '{store_id}' not found.")

        start_date, end_date, window_days = self.get_demand_window()

        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            query = """
            SELECT 
                i.store_id,
                st.store_name,
                st.city,
                i.product_id,
                p.product_name,
                p.category,
                p.unit_price,
                i.current_stock,
                i.reorder_level,
                COALESCE(SUM(s.quantity), 0) as units_sold_window
            FROM inventory i
            JOIN products p ON i.product_id = p.product_id
            JOIN stores st ON i.store_id = st.store_id
            LEFT JOIN sales s ON i.product_id = s.product_id 
                             AND i.store_id = s.store_id
                             AND s.date >= ? AND s.date <= ?
            WHERE 1=1
            """
            params: List[Any] = [start_date, end_date]

            if store_id:
                query += " AND i.store_id = ?"
                params.append(store_id)
            if category:
                query += " AND p.category = ?"
                params.append(category)

            query += " GROUP BY i.store_id, i.product_id ORDER BY i.store_id, i.product_id;"
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()

            risk_items: List[Dict[str, Any]] = []

            for r in rows:
                stock = int(r["current_stock"])
                units_sold = int(r["units_sold_window"])
                avg_daily = round(units_sold / window_days, 2) if window_days > 0 else 0.0

                coverage, cov_status = self.calculate_inventory_coverage(stock, avg_daily)
                level, thresh = self.assess_stockout_risk(coverage, stock, cov_status)

                # Skip non-risks unless requested
                if level not in ("CRITICAL", "HIGH", "MEDIUM"):
                    continue

                if risk_level and level != risk_level.upper():
                    continue

                if min_severity:
                    min_sev = min_severity.upper()
                    if min_sev == "CRITICAL" and level != "CRITICAL":
                        continue
                    if min_sev == "HIGH" and level not in ("CRITICAL", "HIGH"):
                        continue

                reorder_info = self.get_reorder_recommendation(
                    current_stock=stock,
                    average_daily_sales=avg_daily,
                    reorder_level=int(r["reorder_level"]),
                )

                evidence = self.build_inventory_evidence(
                    metric="stockout_risk",
                    current_stock=stock,
                    average_daily_sales=avg_daily,
                    days_of_coverage=coverage,
                    threshold=thresh,
                    analysis_period={"start_date": start_date, "end_date": end_date},
                    extra={
                        "risk_level": level,
                        "recommended_reorder_qty": reorder_info["recommended_reorder_quantity"],
                    },
                )

                risk_items.append({
                    "product_id": r["product_id"],
                    "product_name": r["product_name"],
                    "category": r["category"],
                    "unit_price": float(r["unit_price"]),
                    "store_id": r["store_id"],
                    "store_name": r["store_name"],
                    "city": r["city"],
                    "current_stock": stock,
                    "average_daily_sales": avg_daily,
                    "days_of_coverage": coverage,
                    "risk_level": level,
                    "threshold_used": thresh,
                    "analysis_period": {"start_date": start_date, "end_date": end_date, "days": window_days},
                    "reorder_recommendation": reorder_info,
                    "evidence": evidence,
                })

            # Sort by severity (CRITICAL first, then HIGH, then MEDIUM) then lowest coverage
            severity_order = {"CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4, "NO_DEMAND": 5}
            risk_items.sort(
                key=lambda x: (
                    severity_order.get(x["risk_level"], 99),
                    x["days_of_coverage"] if x["days_of_coverage"] is not None else 9999,
                )
            )

            return risk_items
        finally:
            conn.close()

    # --------------------------------------------------------------------------
    # 6. Overstock Detection
    # --------------------------------------------------------------------------

    def get_overstocked_products(
        self,
        store_id: Optional[str] = None,
        category: Optional[str] = None,
        threshold_days: float = OVERSTOCK_THRESHOLD_DAYS,
    ) -> List[Dict[str, Any]]:
        """Identify products with inventory significantly exceeding expected velocity."""
        if store_id and not get_store(store_id, db_path=self.db_path):
            raise EntityNotFoundError(f"Store '{store_id}' not found.")

        start_date, end_date, window_days = self.get_demand_window()

        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            query = """
            SELECT 
                i.store_id,
                st.store_name,
                st.city,
                i.product_id,
                p.product_name,
                p.category,
                p.unit_price,
                i.current_stock,
                i.reorder_level,
                COALESCE(SUM(s.quantity), 0) as units_sold_window
            FROM inventory i
            JOIN products p ON i.product_id = p.product_id
            JOIN stores st ON i.store_id = st.store_id
            LEFT JOIN sales s ON i.product_id = s.product_id 
                             AND i.store_id = s.store_id
                             AND s.date >= ? AND s.date <= ?
            WHERE 1=1
            """
            params: List[Any] = [start_date, end_date]

            if store_id:
                query += " AND i.store_id = ?"
                params.append(store_id)
            if category:
                query += " AND p.category = ?"
                params.append(category)

            query += " GROUP BY i.store_id, i.product_id ORDER BY i.store_id, i.product_id;"
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()

            overstock_items: List[Dict[str, Any]] = []

            for r in rows:
                stock = int(r["current_stock"])
                if stock <= 0:
                    continue

                units_sold = int(r["units_sold_window"])
                avg_daily = round(units_sold / window_days, 2) if window_days > 0 else 0.0
                coverage, cov_status = self.calculate_inventory_coverage(stock, avg_daily)

                is_overstocked = False
                severity = "MODERATE"
                excess_units = 0

                if cov_status == "no_recent_demand" and stock >= 25:
                    # Stagnant inventory with zero recent sales
                    is_overstocked = True
                    severity = "CRITICAL"
                    excess_units = stock
                elif coverage is not None and coverage > threshold_days:
                    is_overstocked = True
                    expected_max_stock = int(round(avg_daily * threshold_days))
                    excess_units = max(0, stock - expected_max_stock)
                    if coverage >= OVERSTOCK_CRITICAL_DAYS:
                        severity = "CRITICAL"
                    elif coverage >= (threshold_days * 1.5):
                        severity = "HIGH"
                    else:
                        severity = "MODERATE"

                if not is_overstocked:
                    continue

                unit_price = float(r["unit_price"])
                excess_capital = round(excess_units * unit_price, 2)

                evidence = self.build_inventory_evidence(
                    metric="overstock",
                    current_stock=stock,
                    average_daily_sales=avg_daily,
                    days_of_coverage=coverage,
                    threshold=threshold_days,
                    analysis_period={"start_date": start_date, "end_date": end_date},
                    extra={
                        "excess_inventory_units": excess_units,
                        "excess_capital_inr": excess_capital,
                        "severity": severity,
                    },
                )

                overstock_items.append({
                    "product_id": r["product_id"],
                    "product_name": r["product_name"],
                    "category": r["category"],
                    "unit_price": unit_price,
                    "store_id": r["store_id"],
                    "store_name": r["store_name"],
                    "city": r["city"],
                    "current_stock": stock,
                    "average_daily_sales": avg_daily,
                    "days_of_coverage": coverage,
                    "overstock_threshold_days": threshold_days,
                    "excess_inventory_units": excess_units,
                    "excess_capital_inr": excess_capital,
                    "severity": severity,
                    "analysis_period": {"start_date": start_date, "end_date": end_date, "days": window_days},
                    "evidence": evidence,
                })

            # Sort by excess capital tied up descending
            overstock_items.sort(key=lambda x: x["excess_capital_inr"], reverse=True)
            return overstock_items
        finally:
            conn.close()

    # --------------------------------------------------------------------------
    # 7. Fast-Moving and Slow-Moving Products
    # --------------------------------------------------------------------------

    def classify_product_velocities(self, window_days: Optional[int] = None) -> Dict[str, Any]:
        """Classify products into Fast, Medium, and Slow moving categories based on network demand."""
        start_date, end_date, actual_days = self.get_demand_window(window_days)

        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            query = """
            SELECT 
                p.product_id,
                p.product_name,
                p.category,
                p.unit_price,
                COALESCE(SUM(s.quantity), 0) as total_units_sold,
                COALESCE(SUM(s.revenue), 0.0) as total_revenue
            FROM products p
            LEFT JOIN sales s ON p.product_id = s.product_id AND s.date >= ? AND s.date <= ?
            GROUP BY p.product_id
            ORDER BY total_units_sold DESC;
            """
            cursor.execute(query, (start_date, end_date))
            rows = cursor.fetchall()

            fast_prods = []
            medium_prods = []
            slow_prods = []

            for r in rows:
                units = int(r["total_units_sold"])
                avg_daily = round(units / actual_days, 2) if actual_days > 0 else 0.0

                item = {
                    "product_id": r["product_id"],
                    "product_name": r["product_name"],
                    "category": r["category"],
                    "unit_price": float(r["unit_price"]),
                    "total_units_sold": units,
                    "total_revenue": round(float(r["total_revenue"]), 2),
                    "average_daily_sales": avg_daily,
                }

                if avg_daily >= VELOCITY_FAST_UNITS_PER_DAY:
                    item["velocity_tier"] = "FAST"
                    fast_prods.append(item)
                elif avg_daily < VELOCITY_SLOW_UNITS_PER_DAY:
                    item["velocity_tier"] = "SLOW"
                    slow_prods.append(item)
                else:
                    item["velocity_tier"] = "MEDIUM"
                    medium_prods.append(item)

            return {
                "fast_moving": fast_prods,
                "medium_moving": medium_prods,
                "slow_moving": slow_prods,
                "counts": {
                    "fast": len(fast_prods),
                    "medium": len(medium_prods),
                    "slow": len(slow_prods),
                    "total": len(rows),
                },
                "thresholds": {
                    "fast_units_per_day": VELOCITY_FAST_UNITS_PER_DAY,
                    "slow_units_per_day": VELOCITY_SLOW_UNITS_PER_DAY,
                },
                "analysis_period": {"start_date": start_date, "end_date": end_date, "days": actual_days},
            }
        finally:
            conn.close()

    # --------------------------------------------------------------------------
    # 8. Inventory Health Summary
    # --------------------------------------------------------------------------

    def get_inventory_health_summary(self, store_id: Optional[str] = None) -> Dict[str, Any]:
        """Compute portfolio-wide inventory health metrics and risk distributions."""
        if store_id and not get_store(store_id, db_path=self.db_path):
            raise EntityNotFoundError(f"Store '{store_id}' not found.")

        start_date, end_date, window_days = self.get_demand_window()

        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            query = """
            SELECT 
                i.store_id,
                i.product_id,
                p.unit_price,
                i.current_stock,
                COALESCE(SUM(s.quantity), 0) as units_sold
            FROM inventory i
            JOIN products p ON i.product_id = p.product_id
            LEFT JOIN sales s ON i.product_id = s.product_id 
                             AND i.store_id = s.store_id 
                             AND s.date >= ? AND s.date <= ?
            WHERE 1=1
            """
            params: List[Any] = [start_date, end_date]
            if store_id:
                query += " AND i.store_id = ?"
                params.append(store_id)

            query += " GROUP BY i.store_id, i.product_id;"
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()

            total_records = len(rows)
            total_stock_units = 0
            total_stock_value = 0.0

            critical_count = 0
            high_count = 0
            medium_count = 0
            low_count = 0
            overstocked_count = 0
            no_demand_count = 0

            for r in rows:
                stock = int(r["current_stock"])
                price = float(r["unit_price"])
                units_sold = int(r["units_sold"])

                total_stock_units += stock
                total_stock_value += stock * price

                avg_daily = round(units_sold / window_days, 2) if window_days > 0 else 0.0
                coverage, status = self.calculate_inventory_coverage(stock, avg_daily)
                risk_level, _ = self.assess_stockout_risk(coverage, stock, status)

                if risk_level == "CRITICAL":
                    critical_count += 1
                elif risk_level == "HIGH":
                    high_count += 1
                elif risk_level == "MEDIUM":
                    medium_count += 1
                elif risk_level == "NO_DEMAND":
                    no_demand_count += 1
                else:
                    low_count += 1

                if (coverage is not None and coverage > OVERSTOCK_THRESHOLD_DAYS) or (status == "no_recent_demand" and stock >= 25):
                    overstocked_count += 1

            velocity_summary = self.classify_product_velocities(window_days)

            critical_pct = round((critical_count / total_records) * 100.0, 1) if total_records > 0 else 0.0
            overstocked_pct = round((overstocked_count / total_records) * 100.0, 1) if total_records > 0 else 0.0
            healthy_pct = round((low_count / total_records) * 100.0, 1) if total_records > 0 else 0.0

            return {
                "total_inventory_records": total_records,
                "total_stock_units": total_stock_units,
                "total_stock_value_inr": round(total_stock_value, 2),
                "risk_distribution": {
                    "critical": critical_count,
                    "high": high_count,
                    "medium": medium_count,
                    "low": low_count,
                    "no_demand": no_demand_count,
                },
                "overstocked_records": overstocked_count,
                "percentages": {
                    "critical_risk_pct": critical_pct,
                    "overstocked_pct": overstocked_pct,
                    "healthy_pct": healthy_pct,
                },
                "product_velocity_counts": velocity_summary["counts"],
                "store_id": store_id,
                "analysis_period": {"start_date": start_date, "end_date": end_date, "days": window_days},
            }
        finally:
            conn.close()

    # --------------------------------------------------------------------------
    # 9. What Needs Attention?
    # --------------------------------------------------------------------------

    def get_attention_items(
        self, store_id: Optional[str] = None, limit: int = 15
    ) -> List[Dict[str, Any]]:
        """Combine deterministic inventory and sales signals into a prioritized action list."""
        stockout_items: List[Dict[str, Any]] = []
        overstock_items: List[Dict[str, Any]] = []
        spike_items: List[Dict[str, Any]] = []
        drop_items: List[Dict[str, Any]] = []

        # 1. Critical & High Stock-Out Risks
        risks = self.get_products_at_risk(store_id=store_id, min_severity="HIGH")
        for r in risks:
            p_name = r["product_name"]
            s_name = r["store_name"]
            stock = r["current_stock"]
            avg_sales = r["average_daily_sales"]
            cov = r["days_of_coverage"]
            reorder_qty = r["reorder_recommendation"]["recommended_reorder_quantity"]
            level = r["risk_level"]

            title = f"{p_name} at critical stock-out risk in {s_name}" if level == "CRITICAL" else f"{p_name} low stock warning in {s_name}"
            evidence_text = f"Current stock: {stock} units; average daily sales: {avg_sales} units/day; estimated coverage: {cov} days."
            rec_action = f"Review replenishment immediately and consider reordering approximately {reorder_qty} units."

            stockout_items.append({
                "type": "STOCK_OUT",
                "severity": level,
                "product_id": r["product_id"],
                "product_name": p_name,
                "store_id": r["store_id"],
                "store_name": s_name,
                "title": title,
                "evidence": evidence_text,
                "evidence_data": r["evidence"],
                "recommended_action": rec_action,
            })

        # 2. Severe Overstock Cases (Ranked by excess capital)
        overstocked = self.get_overstocked_products(store_id=store_id)
        for o in overstocked[:10]:
            p_name = o["product_name"]
            s_name = o["store_name"]
            stock = o["current_stock"]
            excess = o["excess_inventory_units"]
            excess_inr = o["excess_capital_inr"]
            cov = o["days_of_coverage"]

            cov_str = f"{cov} days" if cov is not None else "no recent sales"
            title = f"Significant overstock for {p_name} in {s_name}"
            evidence_text = f"Current stock: {stock} units; coverage: {cov_str}; estimated excess: {excess} units (₹{excess_inr:,.2f})."
            rec_action = f"Pause replenishment. Consider promotional markdown or rebalancing {excess} units to higher-velocity stores."

            overstock_items.append({
                "type": "OVERSTOCK",
                "severity": o["severity"],
                "product_id": o["product_id"],
                "product_name": p_name,
                "store_id": o["store_id"],
                "store_name": s_name,
                "title": title,
                "evidence": evidence_text,
                "evidence_data": o["evidence"],
                "recommended_action": rec_action,
            })

        # 3. Sales Spikes and Drops (Deterministic Detection)
        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT MIN(date) as min_date, MAX(date) as max_date FROM sales;")
            bounds = cursor.fetchone()
            if bounds and bounds["min_date"] and bounds["max_date"]:
                dt_max = datetime.strptime(bounds["max_date"], "%Y-%m-%d").date()
                dt_split = dt_max - timedelta(days=18)
                recent_start = dt_split.isoformat()
                recent_end = bounds["max_date"]
                baseline_start = bounds["min_date"]
                baseline_end = (dt_split - timedelta(days=1)).isoformat()

                days_recent = 18
                dt_base_start = datetime.strptime(baseline_start, "%Y-%m-%d").date()
                dt_base_end = datetime.strptime(baseline_end, "%Y-%m-%d").date()
                days_baseline = (dt_base_end - dt_base_start).days + 1

                if days_baseline > 20:
                    trend_query = """
                    SELECT 
                        p.product_id,
                        p.product_name,
                        p.category,
                        COALESCE(SUM(CASE WHEN s.date >= ? THEN s.quantity ELSE 0 END), 0) as recent_units,
                        COALESCE(SUM(CASE WHEN s.date < ? THEN s.quantity ELSE 0 END), 0) as baseline_units
                    FROM products p
                    JOIN sales s ON p.product_id = s.product_id
                    GROUP BY p.product_id;
                    """
                    cursor.execute(trend_query, (recent_start, recent_start))
                    trend_rows = cursor.fetchall()

                    for tr in trend_rows:
                        r_units = int(tr["recent_units"])
                        b_units = int(tr["baseline_units"])
                        r_rate = r_units / days_recent
                        b_rate = b_units / days_baseline if days_baseline > 0 else 0.1

                        if b_rate > 0.5 and (r_rate / b_rate) >= 1.8:
                            ratio = round(r_rate / b_rate, 1)
                            spike_items.append({
                                "type": "SALES_SPIKE",
                                "severity": "CRITICAL",
                                "product_id": tr["product_id"],
                                "product_name": tr["product_name"],
                                "store_id": None,
                                "store_name": "All Stores",
                                "title": f"Recent sales surge detected for {tr['product_name']}",
                                "evidence": f"Daily sales jumped to {r_rate:.1f} units/day over the last 18 days ({ratio}x historical rate of {b_rate:.1f} units/day).",
                                "evidence_data": {
                                    "recent_rate": round(r_rate, 2),
                                    "baseline_rate": round(b_rate, 2),
                                    "spike_ratio": ratio,
                                    "recent_window": {"start_date": recent_start, "end_date": recent_end},
                                },
                                "recommended_action": "Audit inventory coverage across all retail locations to prevent near-term stock-out risk.",
                            })
                        elif b_rate > 1.5 and (r_rate / b_rate) <= 0.4:
                            ratio = round(r_rate / b_rate, 2)
                            drop_items.append({
                                "type": "SALES_DROP",
                                "severity": "HIGH",
                                "product_id": tr["product_id"],
                                "product_name": tr["product_name"],
                                "store_id": None,
                                "store_name": "All Stores",
                                "title": f"Significant sales decline detected for {tr['product_name']}",
                                "evidence": f"Daily sales dropped to {r_rate:.1f} units/day over the last 18 days (baseline: {b_rate:.1f} units/day; {ratio*100:.0f}% of normal velocity).",
                                "evidence_data": {
                                    "recent_rate": round(r_rate, 2),
                                    "baseline_rate": round(b_rate, 2),
                                    "velocity_ratio": ratio,
                                    "recent_window": {"start_date": recent_start, "end_date": recent_end},
                                },
                                "recommended_action": "Investigate price changes, competitor activity, or store display visibility.",
                            })
        finally:
            conn.close()

        # Combine items with balanced representation across all signals
        all_items: List[Dict[str, Any]] = []
        all_items.extend(stockout_items)
        all_items.extend(spike_items)
        all_items.extend(drop_items)
        all_items.extend(overstock_items)

        # Priority ranking: CRITICAL > HIGH > MEDIUM > MODERATE
        priority_map = {"CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "MODERATE": 4, "LOW": 5}
        all_items.sort(key=lambda x: priority_map.get(x["severity"], 99))

        return all_items[:limit]

    # --------------------------------------------------------------------------
    # 10. Product Inventory Detail across Stores
    # --------------------------------------------------------------------------

    def get_product_inventory_detail(self, product_id: str) -> Dict[str, Any]:
        """Retrieve complete inventory and replenishment status for a product across all stores."""
        product = get_product(product_id, db_path=self.db_path)
        if not product:
            raise EntityNotFoundError(f"Product '{product_id}' not found.")

        start_date, end_date, window_days = self.get_demand_window()

        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            query = """
            SELECT 
                i.store_id,
                st.store_name,
                st.city,
                i.current_stock,
                i.reorder_level,
                COALESCE(SUM(s.quantity), 0) as units_sold_window
            FROM inventory i
            JOIN stores st ON i.store_id = st.store_id
            LEFT JOIN sales s ON i.product_id = s.product_id 
                             AND i.store_id = s.store_id 
                             AND s.date >= ? AND s.date <= ?
            WHERE i.product_id = ?
            GROUP BY i.store_id
            ORDER BY i.store_id;
            """
            cursor.execute(query, (start_date, end_date, product_id))
            rows = cursor.fetchall()

            stores_detail = []
            total_stock = 0
            total_window_units = 0

            for r in rows:
                stock = int(r["current_stock"])
                units = int(r["units_sold_window"])
                total_stock += stock
                total_window_units += units

                avg_daily = round(units / window_days, 2) if window_days > 0 else 0.0
                cov, status = self.calculate_inventory_coverage(stock, avg_daily)
                risk_level, thresh = self.assess_stockout_risk(cov, stock, status)

                reorder = self.get_reorder_recommendation(
                    current_stock=stock,
                    average_daily_sales=avg_daily,
                    reorder_level=int(r["reorder_level"]),
                )

                stores_detail.append({
                    "store_id": r["store_id"],
                    "store_name": r["store_name"],
                    "city": r["city"],
                    "current_stock": stock,
                    "average_daily_sales": avg_daily,
                    "days_of_coverage": cov,
                    "risk_level": risk_level,
                    "reorder_recommendation": reorder,
                })

            network_avg_daily = round(total_window_units / window_days, 2) if window_days > 0 else 0.0
            network_cov, _ = self.calculate_inventory_coverage(total_stock, network_avg_daily)

            return {
                "product_id": product["product_id"],
                "product_name": product["product_name"],
                "category": product["category"],
                "unit_price": product["unit_price"],
                "network_totals": {
                    "total_stock_units": total_stock,
                    "network_average_daily_sales": network_avg_daily,
                    "network_days_of_coverage": network_cov,
                },
                "stores": stores_detail,
                "analysis_period": {"start_date": start_date, "end_date": end_date, "days": window_days},
            }
        finally:
            conn.close()

    # --------------------------------------------------------------------------
    # 11. Evidence Builder
    # --------------------------------------------------------------------------

    def build_inventory_evidence(
        self,
        metric: str,
        current_stock: int,
        average_daily_sales: float,
        days_of_coverage: Optional[float],
        threshold: float,
        analysis_period: Dict[str, str],
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Construct a standardized evidence dictionary for decision auditability and copilot grounding."""
        evidence = {
            "metric": metric,
            "current_stock": current_stock,
            "average_daily_sales": average_daily_sales,
            "days_of_coverage": days_of_coverage,
            "threshold_days": threshold,
            "analysis_period": analysis_period,
            "calculation_formula": "Days of Coverage = Current Stock / Average Daily Sales",
        }
        if extra:
            evidence.update(extra)
        return evidence
