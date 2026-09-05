"""Evidence building and data grounding layer for RetailIQ.

Provides structured, deterministic factual citations directly from the analytics engines.
LLMs must strictly explain these verified records without modification.
"""

from typing import Any, Dict, List, Optional


class EvidenceBuilder:
    """Builds structured, auditable evidence records for copilot answers."""

    @staticmethod
    def for_stockout_risks(
        risks: List[Dict[str, Any]],
        analysis_period: Dict[str, Any],
        threshold: float,
    ) -> List[Dict[str, Any]]:
        """Construct evidence records for products at stock-out risk."""
        evidence: List[Dict[str, Any]] = []
        for r in risks:
            evidence.append({
                "metric": "inventory_coverage",
                "product_id": r["product_id"],
                "product_name": r["product_name"],
                "store_id": r["store_id"],
                "store_name": r["store_name"],
                "current_stock": r["current_stock"],
                "average_daily_sales": r["average_daily_sales"],
                "days_of_coverage": r["days_of_coverage"],
                "risk_level": r["risk_level"],
                "threshold_days": threshold,
                "reorder_quantity": r.get("reorder_recommendation", {}).get("recommended_reorder_quantity", 0),
                "analysis_period": analysis_period,
                "calculation_formula": "Days of Coverage = Current Stock / Average Daily Sales",
                "verified": True,
            })
        return evidence

    @staticmethod
    def for_sales_summary(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Construct evidence for overall sales summary."""
        return [
            {
                "metric": "sales_summary",
                "total_revenue": summary["total_revenue"],
                "total_units_sold": summary["total_units_sold"],
                "total_transactions": summary["total_transactions"],
                "average_daily_revenue": summary["average_daily_revenue"],
                "average_daily_units_sold": summary["average_daily_units_sold"],
                "average_order_value": summary["average_order_value"],
                "active_selling_days": summary["active_selling_days"],
                "analysis_period": summary.get("period", {}),
                "calculation_formula": "Total Revenue = sum(Quantity * Unit Price)",
                "verified": True,
            }
        ]

    @staticmethod
    def for_product_performance(perf: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Construct evidence for individual product performance."""
        return [
            {
                "metric": "product_sales_performance",
                "product_id": perf["product_id"],
                "product_name": perf["product_name"],
                "category": perf["category"],
                "unit_price": perf["unit_price"],
                "total_units_sold": perf["total_units_sold"],
                "total_revenue": perf["total_revenue"],
                "average_daily_sales": perf["average_daily_sales"],
                "selling_days": perf["selling_days"],
                "analysis_period": perf.get("period", {}),
                "calculation_formula": "Revenue = Units Sold * Unit Price",
                "verified": True,
            }
        ]

    @staticmethod
    def for_store_performance(perf: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Construct evidence for store sales performance."""
        return [
            {
                "metric": "store_sales_performance",
                "store_id": perf["store_id"],
                "store_name": perf["store_name"],
                "city": perf["city"],
                "total_revenue": perf["total_revenue"],
                "total_units_sold": perf["total_units_sold"],
                "average_daily_revenue": perf["average_daily_revenue"],
                "active_selling_days": perf["active_selling_days"],
                "analysis_period": perf.get("period", {}),
                "verified": True,
            }
        ]

    @staticmethod
    def for_overstock(
        items: List[Dict[str, Any]],
        analysis_period: Dict[str, Any],
        threshold_days: float,
    ) -> List[Dict[str, Any]]:
        """Construct evidence for overstocked items."""
        evidence: List[Dict[str, Any]] = []
        for o in items:
            evidence.append({
                "metric": "overstock_excess",
                "product_id": o["product_id"],
                "product_name": o["product_name"],
                "store_id": o["store_id"],
                "store_name": o["store_name"],
                "current_stock": o["current_stock"],
                "average_daily_sales": o["average_daily_sales"],
                "days_of_coverage": o["days_of_coverage"],
                "overstock_threshold_days": threshold_days,
                "excess_inventory_units": o["excess_inventory_units"],
                "excess_capital_inr": o["excess_capital_inr"],
                "severity": o["severity"],
                "analysis_period": analysis_period,
                "calculation_formula": "Excess Units = max(0, Current Stock - (Avg Daily Sales * Threshold Days))",
                "verified": True,
            })
        return evidence

    @staticmethod
    def for_store_comparison(
        stores_data: List[Dict[str, Any]],
        product_name: Optional[str] = None,
        analysis_period: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Construct evidence comparing store performance."""
        evidence: List[Dict[str, Any]] = []
        for s in stores_data:
            rec = {
                "metric": "store_ranking",
                "store_id": s["store_id"],
                "store_name": s["store_name"],
                "city": s.get("city"),
                "units_sold": s["units_sold"],
                "revenue": s["revenue"],
                "rank_units": s.get("rank_units"),
                "rank_revenue": s.get("rank_revenue"),
                "product_analyzed": product_name,
                "analysis_period": analysis_period,
                "verified": True,
            }
            evidence.append(rec)
        return evidence

    @staticmethod
    def for_product_comparison(
        products_data: List[Dict[str, Any]],
        analysis_period: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Construct evidence comparing products."""
        evidence: List[Dict[str, Any]] = []
        for p in products_data:
            evidence.append({
                "metric": "product_ranking",
                "product_id": p["product_id"],
                "product_name": p["product_name"],
                "category": p.get("category"),
                "units_sold": p.get("units_sold", p.get("total_units", 0)),
                "revenue": p.get("revenue", p.get("total_revenue", 0.0)),
                "rank_revenue": p.get("rank_revenue", p.get("rank")),
                "rank_units": p.get("rank_units"),
                "analysis_period": analysis_period,
                "verified": True,
            })
        return evidence

    @staticmethod
    def for_attention(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Construct evidence for executive attention items."""
        evidence: List[Dict[str, Any]] = []
        for it in items:
            evidence.append({
                "metric": f"attention_{it['type'].lower()}",
                "type": it["type"],
                "severity": it["severity"],
                "product_id": it.get("product_id"),
                "product_name": it.get("product_name"),
                "store_name": it.get("store_name"),
                "evidence_summary": it.get("evidence"),
                "supporting_data": it.get("evidence_data"),
                "recommended_action": it.get("recommended_action"),
                "verified": True,
            })
        return evidence


# Backwards compatibility alias
EvidenceExtractor = EvidenceBuilder
