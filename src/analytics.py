"""Deterministic Sales Analytics Engine for RetailIQ.

All business-critical numerical calculations are performed deterministically in Python/SQL.
LLMs (e.g. Gemini) are never used to compute revenue, units, growth, averages, or rankings.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from src.config import DATABASE_PATH
from src.database import get_connection, get_product, get_store


class EntityNotFoundError(Exception):
    """Raised when a requested product or store does not exist."""
    pass


class InvalidDateRangeError(Exception):
    """Raised when a date range is invalid (e.g. start_date > end_date)."""
    pass


class SalesAnalyticsEngine:
    """Core deterministic analytics engine operating on SQLite retail sales data."""

    def __init__(self, db_path: str | Path = DATABASE_PATH) -> None:
        self.db_path = db_path

    # --------------------------------------------------------------------------
    # Date Bounds & Validation Helpers
    # --------------------------------------------------------------------------

    def get_dataset_date_bounds(self) -> Dict[str, Any]:
        """Retrieve min and max dates present in the sales database."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT MIN(date) as min_date, MAX(date) as max_date, COUNT(DISTINCT date) as total_days FROM sales;")
            row = cursor.fetchone()
            return {
                "min_date": row["min_date"] if row else None,
                "max_date": row["max_date"] if row else None,
                "total_days": row["total_days"] if row else 0,
            }
        finally:
            conn.close()

    def validate_date_range(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str], Dict[str, Any]]:
        """Validate and parse date parameters, returning normalized dates and completeness metadata."""
        if start_date and end_date:
            try:
                dt_start = datetime.strptime(start_date, "%Y-%m-%d").date()
                dt_end = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError as exc:
                raise InvalidDateRangeError(f"Invalid date format (must be YYYY-MM-DD): {exc}")

            if dt_start > dt_end:
                raise InvalidDateRangeError(
                    f"start_date '{start_date}' cannot be after end_date '{end_date}'."
                )

            expected_days = (dt_end - dt_start).days + 1
        else:
            expected_days = None

        bounds = self.get_dataset_date_bounds()
        min_avail = bounds["min_date"]
        max_avail = bounds["max_date"]

        is_partial = False
        if start_date and min_avail and start_date < min_avail:
            is_partial = True
        if end_date and max_avail and end_date > max_avail:
            is_partial = True

        metadata = {
            "expected_calendar_days": expected_days,
            "available_min_date": min_avail,
            "available_max_date": max_avail,
            "is_partial": is_partial,
        }
        return start_date, end_date, metadata

    # --------------------------------------------------------------------------
    # 1. Overall Sales Summary
    # --------------------------------------------------------------------------

    def get_sales_summary(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        store_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Calculate overall sales summary for a given date range and optional store filter."""
        start_date, end_date, meta = self.validate_date_range(start_date, end_date)

        if store_id:
            store = get_store(store_id, db_path=self.db_path)
            if not store:
                raise EntityNotFoundError(f"Store '{store_id}' not found.")

        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            query = """
            SELECT 
                COUNT(*) as total_transactions,
                COALESCE(SUM(quantity), 0) as total_units,
                COALESCE(SUM(revenue), 0.0) as total_revenue,
                COUNT(DISTINCT date) as active_selling_days,
                MIN(date) as first_sale_date,
                MAX(date) as last_sale_date
            FROM sales
            WHERE (date >= ? OR ? IS NULL)
              AND (date <= ? OR ? IS NULL)
              AND (store_id = ? OR ? IS NULL);
            """
            cursor.execute(query, (start_date, start_date, end_date, end_date, store_id, store_id))
            row = cursor.fetchone()

            total_transactions = int(row["total_transactions"])
            total_units = int(row["total_units"])
            total_revenue = round(float(row["total_revenue"]), 2)
            active_days = int(row["active_selling_days"])

            has_data = total_transactions > 0
            avg_daily_rev = round(total_revenue / active_days, 2) if active_days > 0 else 0.0
            avg_daily_units = round(total_units / active_days, 2) if active_days > 0 else 0.0
            avg_order_value = round(total_revenue / total_transactions, 2) if total_transactions > 0 else 0.0

            return {
                "has_data": has_data,
                "total_revenue": total_revenue,
                "total_units_sold": total_units,
                "total_transactions": total_transactions,
                "average_daily_revenue": avg_daily_rev,
                "average_daily_units_sold": avg_daily_units,
                "average_order_value": avg_order_value,
                "active_selling_days": active_days,
                "period": {
                    "start_date": start_date or row["first_sale_date"],
                    "end_date": end_date or row["last_sale_date"],
                    "expected_calendar_days": meta["expected_calendar_days"],
                    "is_partial": meta["is_partial"],
                },
                "store_id": store_id,
            }
        finally:
            conn.close()

    # --------------------------------------------------------------------------
    # 2. Product Performance
    # --------------------------------------------------------------------------

    def get_product_performance(
        self,
        product_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Calculate performance metrics for a specific product over a date range."""
        product = get_product(product_id, db_path=self.db_path)
        if not product:
            raise EntityNotFoundError(f"Product '{product_id}' not found.")

        start_date, end_date, meta = self.validate_date_range(start_date, end_date)

        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            query = """
            SELECT 
                COUNT(*) as total_transactions,
                COALESCE(SUM(quantity), 0) as total_units,
                COALESCE(SUM(revenue), 0.0) as total_revenue,
                COUNT(DISTINCT date) as selling_days
            FROM sales
            WHERE product_id = ?
              AND (date >= ? OR ? IS NULL)
              AND (date <= ? OR ? IS NULL);
            """
            cursor.execute(query, (product_id, start_date, start_date, end_date, end_date))
            row = cursor.fetchone()

            total_units = int(row["total_units"])
            total_revenue = round(float(row["total_revenue"]), 2)
            selling_days = int(row["selling_days"])
            total_trans = int(row["total_transactions"])

            has_data = total_trans > 0
            avg_daily_sales = round(total_units / selling_days, 2) if selling_days > 0 else 0.0

            return {
                "has_data": has_data,
                "product_id": product["product_id"],
                "product_name": product["product_name"],
                "category": product["category"],
                "unit_price": product["unit_price"],
                "total_units_sold": total_units,
                "total_revenue": total_revenue,
                "average_daily_sales": avg_daily_sales,
                "selling_days": selling_days,
                "total_transactions": total_trans,
                "period": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "expected_calendar_days": meta["expected_calendar_days"],
                    "is_partial": meta["is_partial"],
                },
            }
        finally:
            conn.close()

    # --------------------------------------------------------------------------
    # 3. Store Performance
    # --------------------------------------------------------------------------

    def get_store_performance(
        self,
        store_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Calculate performance metrics for a specific store over a date range."""
        store = get_store(store_id, db_path=self.db_path)
        if not store:
            raise EntityNotFoundError(f"Store '{store_id}' not found.")

        start_date, end_date, meta = self.validate_date_range(start_date, end_date)

        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            query = """
            SELECT 
                COUNT(*) as total_transactions,
                COALESCE(SUM(quantity), 0) as total_units,
                COALESCE(SUM(revenue), 0.0) as total_revenue,
                COUNT(DISTINCT date) as active_selling_days
            FROM sales
            WHERE store_id = ?
              AND (date >= ? OR ? IS NULL)
              AND (date <= ? OR ? IS NULL);
            """
            cursor.execute(query, (store_id, start_date, start_date, end_date, end_date))
            row = cursor.fetchone()

            total_units = int(row["total_units"])
            total_revenue = round(float(row["total_revenue"]), 2)
            active_days = int(row["active_selling_days"])
            total_trans = int(row["total_transactions"])

            avg_daily_rev = round(total_revenue / active_days, 2) if active_days > 0 else 0.0
            has_data = total_trans > 0

            return {
                "has_data": has_data,
                "store_id": store["store_id"],
                "store_name": store["store_name"],
                "city": store["city"],
                "total_revenue": total_revenue,
                "total_units_sold": total_units,
                "total_transactions": total_trans,
                "average_daily_revenue": avg_daily_rev,
                "active_selling_days": active_days,
                "period": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "expected_calendar_days": meta["expected_calendar_days"],
                    "is_partial": meta["is_partial"],
                },
            }
        finally:
            conn.close()

    # --------------------------------------------------------------------------
    # 4. Product Comparison
    # --------------------------------------------------------------------------

    def compare_products(
        self,
        product_ids: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compare performance across multiple products with rankings by revenue and units."""
        start_date, end_date, meta = self.validate_date_range(start_date, end_date)

        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            query = """
            SELECT 
                p.product_id,
                p.product_name,
                p.category,
                p.unit_price,
                COALESCE(SUM(s.quantity), 0) as units_sold,
                COALESCE(SUM(s.revenue), 0.0) as revenue,
                COUNT(s.sale_id) as transactions
            FROM products p
            LEFT JOIN sales s ON p.product_id = s.product_id
              AND (s.date >= ? OR ? IS NULL)
              AND (s.date <= ? OR ? IS NULL)
            """
            params: List[Any] = [start_date, start_date, end_date, end_date]

            if product_ids:
                placeholders = ",".join(["?"] * len(product_ids))
                query += f" WHERE p.product_id IN ({placeholders})"
                params.extend(product_ids)

            query += " GROUP BY p.product_id, p.product_name, p.category, p.unit_price;"
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()

            records = [
                {
                    "product_id": r["product_id"],
                    "product_name": r["product_name"],
                    "category": r["category"],
                    "unit_price": float(r["unit_price"]),
                    "units_sold": int(r["units_sold"]),
                    "revenue": round(float(r["revenue"]), 2),
                    "transactions": int(r["transactions"]),
                }
                for r in rows
            ]

            # Assign revenue ranking
            records.sort(key=lambda x: x["revenue"], reverse=True)
            for rank, rec in enumerate(records, start=1):
                rec["rank_revenue"] = rank

            # Assign units ranking
            records.sort(key=lambda x: x["units_sold"], reverse=True)
            for rank, rec in enumerate(records, start=1):
                rec["rank_units"] = rank

            # Default sort by revenue rank
            records.sort(key=lambda x: x["rank_revenue"])

            return {
                "total_products_compared": len(records),
                "products": records,
                "period": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "is_partial": meta["is_partial"],
                },
            }
        finally:
            conn.close()

    # --------------------------------------------------------------------------
    # 5. Store Comparison
    # --------------------------------------------------------------------------

    def compare_stores(
        self,
        store_ids: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compare performance across stores with rankings."""
        start_date, end_date, meta = self.validate_date_range(start_date, end_date)

        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            query = """
            SELECT 
                st.store_id,
                st.store_name,
                st.city,
                COALESCE(SUM(s.quantity), 0) as units_sold,
                COALESCE(SUM(s.revenue), 0.0) as revenue,
                COUNT(s.sale_id) as transactions
            FROM stores st
            LEFT JOIN sales s ON st.store_id = s.store_id
              AND (s.date >= ? OR ? IS NULL)
              AND (s.date <= ? OR ? IS NULL)
            """
            params: List[Any] = [start_date, start_date, end_date, end_date]

            if store_ids:
                placeholders = ",".join(["?"] * len(store_ids))
                query += f" WHERE st.store_id IN ({placeholders})"
                params.extend(store_ids)

            query += " GROUP BY st.store_id, st.store_name, st.city;"
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()

            records = [
                {
                    "store_id": r["store_id"],
                    "store_name": r["store_name"],
                    "city": r["city"],
                    "units_sold": int(r["units_sold"]),
                    "revenue": round(float(r["revenue"]), 2),
                    "transactions": int(r["transactions"]),
                }
                for r in rows
            ]

            records.sort(key=lambda x: x["revenue"], reverse=True)
            for rank, rec in enumerate(records, start=1):
                rec["rank_revenue"] = rank

            records.sort(key=lambda x: x["units_sold"], reverse=True)
            for rank, rec in enumerate(records, start=1):
                rec["rank_units"] = rank

            records.sort(key=lambda x: x["rank_revenue"])

            return {
                "total_stores_compared": len(records),
                "stores": records,
                "period": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "is_partial": meta["is_partial"],
                },
            }
        finally:
            conn.close()

    # --------------------------------------------------------------------------
    # 6. Category Performance
    # --------------------------------------------------------------------------

    def get_category_performance(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Calculate revenue, units sold, and percentage revenue contribution for each category."""
        start_date, end_date, meta = self.validate_date_range(start_date, end_date)

        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            query = """
            SELECT 
                p.category,
                COALESCE(SUM(s.quantity), 0) as units_sold,
                COALESCE(SUM(s.revenue), 0.0) as revenue,
                COUNT(s.sale_id) as transactions
            FROM products p
            JOIN sales s ON p.product_id = s.product_id
            WHERE (s.date >= ? OR ? IS NULL)
              AND (s.date <= ? OR ? IS NULL)
            GROUP BY p.category
            ORDER BY revenue DESC;
            """
            cursor.execute(query, (start_date, start_date, end_date, end_date))
            rows = cursor.fetchall()

            total_revenue = sum(float(r["revenue"]) for r in rows)
            total_units = sum(int(r["units_sold"]) for r in rows)

            categories = []
            for r in rows:
                rev = round(float(r["revenue"]), 2)
                pct = round((rev / total_revenue) * 100.0, 2) if total_revenue > 0 else 0.0
                categories.append({
                    "category": r["category"],
                    "units_sold": int(r["units_sold"]),
                    "revenue": rev,
                    "revenue_percentage": pct,
                    "transactions": int(r["transactions"]),
                })

            return {
                "total_revenue": round(total_revenue, 2),
                "total_units_sold": total_units,
                "categories": categories,
                "period": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "is_partial": meta["is_partial"],
                },
            }
        finally:
            conn.close()

    # --------------------------------------------------------------------------
    # 7. Period Comparison
    # --------------------------------------------------------------------------

    def compare_periods(
        self,
        current_start: str,
        current_end: str,
        previous_start: str,
        previous_end: str,
        store_id: Optional[str] = None,
        product_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compare performance across two distinct periods, safely calculating growth metrics."""
        self.validate_date_range(current_start, current_end)
        self.validate_date_range(previous_start, previous_end)

        current_summary = self.get_sales_summary(
            start_date=current_start, end_date=current_end, store_id=store_id
        )
        previous_summary = self.get_sales_summary(
            start_date=previous_start, end_date=previous_end, store_id=store_id
        )

        curr_rev = current_summary["total_revenue"]
        prev_rev = previous_summary["total_revenue"]
        curr_units = current_summary["total_units_sold"]
        prev_units = previous_summary["total_units_sold"]

        rev_change = round(curr_rev - prev_rev, 2)
        units_change = curr_units - prev_units

        # Safe growth calculations handling zero previous values without division by zero
        if prev_rev > 0:
            rev_growth_pct = round(((curr_rev - prev_rev) / prev_rev) * 100.0, 2)
            prev_revenue_is_zero = False
        else:
            rev_growth_pct = 100.0 if curr_rev > 0 else 0.0
            prev_revenue_is_zero = True

        if prev_units > 0:
            unit_growth_pct = round(((curr_units - prev_units) / prev_units) * 100.0, 2)
            prev_units_is_zero = False
        else:
            unit_growth_pct = 100.0 if curr_units > 0 else 0.0
            prev_units_is_zero = True

        return {
            "current_period": {
                "start_date": current_start,
                "end_date": current_end,
                "revenue": curr_rev,
                "units": curr_units,
                "transactions": current_summary["total_transactions"],
                "active_days": current_summary["active_selling_days"],
            },
            "previous_period": {
                "start_date": previous_start,
                "end_date": previous_end,
                "revenue": prev_rev,
                "units": prev_units,
                "transactions": previous_summary["total_transactions"],
                "active_days": previous_summary["active_selling_days"],
            },
            "revenue_change": rev_change,
            "revenue_growth_percentage": rev_growth_pct,
            "units_change": units_change,
            "unit_growth_percentage": unit_growth_pct,
            "zero_baseline": {
                "previous_revenue_is_zero": prev_revenue_is_zero,
                "previous_units_is_zero": prev_units_is_zero,
            },
        }

    # --------------------------------------------------------------------------
    # 8. Sales Trend
    # --------------------------------------------------------------------------

    def get_sales_trend(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        store_id: Optional[str] = None,
        product_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Aggregate daily sales chronologically for chart rendering."""
        start_date, end_date, meta = self.validate_date_range(start_date, end_date)

        if store_id and not get_store(store_id, db_path=self.db_path):
            raise EntityNotFoundError(f"Store '{store_id}' not found.")
        if product_id and not get_product(product_id, db_path=self.db_path):
            raise EntityNotFoundError(f"Product '{product_id}' not found.")

        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            query = """
            SELECT 
                date,
                COALESCE(SUM(revenue), 0.0) as revenue,
                COALESCE(SUM(quantity), 0) as units,
                COUNT(sale_id) as transactions
            FROM sales
            WHERE (date >= ? OR ? IS NULL)
              AND (date <= ? OR ? IS NULL)
              AND (store_id = ? OR ? IS NULL)
              AND (product_id = ? OR ? IS NULL)
            GROUP BY date
            ORDER BY date ASC;
            """
            cursor.execute(
                query,
                (start_date, start_date, end_date, end_date, store_id, store_id, product_id, product_id),
            )
            rows = cursor.fetchall()

            points = [
                {
                    "date": r["date"],
                    "revenue": round(float(r["revenue"]), 2),
                    "units": int(r["units"]),
                    "transactions": int(r["transactions"]),
                }
                for r in rows
            ]

            return {
                "total_points": len(points),
                "trend": points,
                "filters": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "store_id": store_id,
                    "product_id": product_id,
                },
                "is_partial": meta["is_partial"],
            }
        finally:
            conn.close()

    # --------------------------------------------------------------------------
    # 9. Top Products
    # --------------------------------------------------------------------------

    def get_top_products(
        self,
        by: str = "revenue",
        limit: int = 5,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        store_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve top products ranked by revenue or units sold."""
        if by not in ("revenue", "units"):
            raise ValueError(f"Invalid ranking metric '{by}'. Must be 'revenue' or 'units'.")
        if limit <= 0:
            limit = 5

        start_date, end_date, meta = self.validate_date_range(start_date, end_date)

        if store_id and not get_store(store_id, db_path=self.db_path):
            raise EntityNotFoundError(f"Store '{store_id}' not found.")

        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            order_col = "total_revenue" if by == "revenue" else "total_units"
            query = f"""
            SELECT 
                p.product_id,
                p.product_name,
                p.category,
                p.unit_price,
                COALESCE(SUM(s.quantity), 0) as total_units,
                COALESCE(SUM(s.revenue), 0.0) as total_revenue,
                COUNT(s.sale_id) as transactions
            FROM products p
            JOIN sales s ON p.product_id = s.product_id
            WHERE (s.date >= ? OR ? IS NULL)
              AND (s.date <= ? OR ? IS NULL)
              AND (s.store_id = ? OR ? IS NULL)
            GROUP BY p.product_id, p.product_name, p.category, p.unit_price
            ORDER BY {order_col} DESC
            LIMIT ?;
            """
            cursor.execute(query, (start_date, start_date, end_date, end_date, store_id, store_id, limit))
            rows = cursor.fetchall()

            products = [
                {
                    "rank": rank,
                    "product_id": r["product_id"],
                    "product_name": r["product_name"],
                    "category": r["category"],
                    "unit_price": float(r["unit_price"]),
                    "units_sold": int(r["total_units"]),
                    "revenue": round(float(r["total_revenue"]), 2),
                    "transactions": int(r["transactions"]),
                }
                for rank, r in enumerate(rows, start=1)
            ]

            return {
                "ranking_metric": by,
                "limit": limit,
                "top_products": products,
                "period": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "is_partial": meta["is_partial"],
                },
                "store_id": store_id,
            }
        finally:
            conn.close()

    # --------------------------------------------------------------------------
    # 10. Store-Product Performance ("Which store sells this product best?")
    # --------------------------------------------------------------------------

    def get_store_product_performance(
        self,
        product_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze store breakdown for a product to answer 'Which store sells this product best?'."""
        product = get_product(product_id, db_path=self.db_path)
        if not product:
            raise EntityNotFoundError(f"Product '{product_id}' not found.")

        start_date, end_date, meta = self.validate_date_range(start_date, end_date)

        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            query = """
            SELECT 
                st.store_id,
                st.store_name,
                st.city,
                COALESCE(SUM(s.quantity), 0) as units_sold,
                COALESCE(SUM(s.revenue), 0.0) as revenue,
                COUNT(s.sale_id) as transactions
            FROM stores st
            LEFT JOIN sales s ON st.store_id = s.store_id
              AND s.product_id = ?
              AND (s.date >= ? OR ? IS NULL)
              AND (s.date <= ? OR ? IS NULL)
            GROUP BY st.store_id, st.store_name, st.city;
            """
            cursor.execute(query, (product_id, start_date, start_date, end_date, end_date))
            rows = cursor.fetchall()

            stores = [
                {
                    "store_id": r["store_id"],
                    "store_name": r["store_name"],
                    "city": r["city"],
                    "units_sold": int(r["units_sold"]),
                    "revenue": round(float(r["revenue"]), 2),
                    "transactions": int(r["transactions"]),
                }
                for r in rows
            ]

            # Rank by units sold
            stores.sort(key=lambda x: x["units_sold"], reverse=True)
            for rank, s in enumerate(stores, start=1):
                s["rank_units"] = rank

            # Rank by revenue
            stores.sort(key=lambda x: x["revenue"], reverse=True)
            for rank, s in enumerate(stores, start=1):
                s["rank_revenue"] = rank

            stores.sort(key=lambda x: x["rank_units"])

            best_by_units = stores[0] if stores and stores[0]["units_sold"] > 0 else None
            best_by_revenue = max(stores, key=lambda x: x["revenue"]) if stores and stores[0]["revenue"] > 0 else None

            return {
                "product_id": product["product_id"],
                "product_name": product["product_name"],
                "category": product["category"],
                "best_store_by_units": best_by_units["store_name"] if best_by_units else None,
                "best_store_by_revenue": best_by_revenue["store_name"] if best_by_revenue else None,
                "stores": stores,
                "period": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "is_partial": meta["is_partial"],
                },
            }
        finally:
            conn.close()


# Compatibility alias for earlier stages
AnalyticsEngine = SalesAnalyticsEngine
