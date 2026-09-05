"""Complete RetailIQ AI Copilot orchestration pipeline.

Coordinates:
1. Natural language question processing
2. Intent extraction & validation
3. Entity resolution & database verification
4. Ambiguity & insufficient-data handling
5. Routing to deterministic sales and inventory analytics
6. Grounded evidence construction
7. Gemini natural-language explanation
8. Typed structured response packaging
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from src.config import (
    DATABASE_PATH,
    OVERSTOCK_THRESHOLD_DAYS,
    RISK_THRESHOLD_CRITICAL,
    RISK_THRESHOLD_HIGH,
    RISK_THRESHOLD_MEDIUM,
    TARGET_REORDER_COVERAGE_DAYS,
)
from src.database import get_product, get_store
from src.analytics import SalesAnalyticsEngine, EntityNotFoundError, InvalidDateRangeError
from src.inventory import InventoryIntelligenceEngine
from src.evidence import EvidenceBuilder
from src.gemini_client import GeminiClient
from src.intent import IntentClassifier, SUPPORTED_INTENTS
from src.models import CopilotResponse, StructuredIntent

logger = logging.getLogger(__name__)


class RetailCopilot:
    """Evidence-first retail copilot orchestrator."""

    def __init__(
        self,
        db_path: str = DATABASE_PATH,
        gemini_client: Optional[GeminiClient] = None,
    ) -> None:
        self.db_path = db_path
        self.gemini = gemini_client or GeminiClient()
        self.intent_classifier = IntentClassifier(gemini_client=self.gemini)
        self.sales = SalesAnalyticsEngine(db_path=self.db_path)
        self.inventory = InventoryIntelligenceEngine(db_path=self.db_path)
        self.evidence_builder = EvidenceBuilder()

    # --------------------------------------------------------------------------
    # Main Entry Point
    # --------------------------------------------------------------------------

    def answer_question(self, question: str) -> CopilotResponse:
        """Execute the end-to-end copilot intelligence pipeline."""
        # 1. Input validation
        if not question or not question.strip():
            return CopilotResponse(
                answer="Please ask a retail question about sales, inventory, products, stores, or stock risks.",
                intent="UNKNOWN",
                data_status="unavailable",
                needs_clarification=False,
                error="Empty question provided.",
            )

        clean_question = question.strip()
        if len(clean_question) > 1000:
            clean_question = clean_question[:1000]

        # 2. Intent extraction
        intent_info = self.intent_classifier.classify(clean_question)

        # 3. Intent validation
        if intent_info.intent not in SUPPORTED_INTENTS or intent_info.intent == "UNKNOWN":
            return CopilotResponse(
                answer="I couldn't determine the type of retail analysis you need. Please ask about sales, inventory, products, stores, trends, or stock risk.",
                intent="UNKNOWN",
                data_status="unavailable",
                needs_clarification=False,
                evidence=[],
                assumptions=[],
                recommendations=[],
            )

        # 4. Ambiguity handling
        if intent_info.needs_clarification:
            return CopilotResponse(
                answer=intent_info.clarification_question or "Your question was ambiguous. Please specify which product or store you mean.",
                intent=intent_info.intent,
                data_status="ambiguous",
                needs_clarification=True,
                clarification_question=intent_info.clarification_question,
                evidence=[],
                assumptions=[],
                recommendations=[],
            )

        # 5. Unknown entity handling
        if intent_info.product and not intent_info.product_id:
            # An entity was mentioned by the user that does not exist in the database
            return CopilotResponse(
                answer=f"I couldn't find a product matching '{intent_info.product}' in the available retail data.",
                intent=intent_info.intent,
                data_status="no_data",
                needs_clarification=False,
                evidence=[],
                assumptions=[],
                recommendations=[],
            )

        if intent_info.store and not intent_info.store_id:
            return CopilotResponse(
                answer=f"I couldn't find a store matching '{intent_info.store}' in the available retail data.",
                intent=intent_info.intent,
                data_status="no_data",
                needs_clarification=False,
                evidence=[],
                assumptions=[],
                recommendations=[],
            )

        # 6. Route to deterministic analytics
        try:
            return self._execute_intent(clean_question, intent_info)
        except Exception as exc:
            logger.warning("Deterministic analytics execution error: %s", exc)
            return CopilotResponse(
                answer="An error occurred while processing the analytics for your request.",
                intent=intent_info.intent,
                data_status="unavailable",
                error=str(exc),
            )

    # --------------------------------------------------------------------------
    # Intent Routing & Execution
    # --------------------------------------------------------------------------

    def _execute_intent(self, question: str, intent: StructuredIntent) -> CopilotResponse:
        """Route to appropriate analytics function and build evidence & explanation."""
        routing_map = {
            "INVENTORY_RISK": self._handle_inventory_risk,
            "OVERSTOCK": self._handle_overstock,
            "REORDER_RECOMMENDATION": self._handle_reorder_recommendation,
            "INVENTORY_HEALTH": self._handle_inventory_health,
            "ATTENTION_ITEMS": self._handle_attention_items,
            "SALES_SUMMARY": self._handle_sales_summary,
            "PRODUCT_PERFORMANCE": self._handle_product_performance,
            "STORE_PERFORMANCE": self._handle_store_performance,
            "STORE_COMPARISON": self._handle_store_comparison,
            "PRODUCT_COMPARISON": self._handle_product_comparison,
            "CATEGORY_PERFORMANCE": self._handle_category_performance,
            "SALES_TREND": self._handle_sales_trend,
        }

        handler = routing_map.get(intent.intent)
        if not handler:
            return CopilotResponse(
                answer="Analysis type not supported.",
                intent=intent.intent,
                data_status="unavailable",
            )

        return handler(question, intent)

    # --------------------------------------------------------------------------
    # Individual Intent Handlers
    # --------------------------------------------------------------------------

    def _handle_inventory_risk(self, question: str, intent: StructuredIntent) -> CopilotResponse:
        risks = self.inventory.get_products_at_risk(
            store_id=intent.store_id, category=intent.category
        )
        period = {"window_days": 30}
        threshold = RISK_THRESHOLD_CRITICAL
        evidence = self.evidence_builder.for_stockout_risks(risks, period, threshold)

        assumptions = [
            f"Demand window: last 30 days of sales history",
            f"Critical coverage threshold: < {RISK_THRESHOLD_CRITICAL} days",
            f"High risk coverage threshold: {RISK_THRESHOLD_CRITICAL} to {RISK_THRESHOLD_HIGH} days",
        ]

        recommendations = []
        for r in risks[:5]:
            reorder_qty = r.get("reorder_recommendation", {}).get("recommended_reorder_quantity", 0)
            if reorder_qty > 0:
                recommendations.append(
                    f"Reorder {reorder_qty} units of {r['product_name']} for {r['store_name']} (coverage: {r['days_of_coverage']} days)."
                )

        # Generate grounded explanation
        metrics_summary = {
            "total_at_risk": len(risks),
            "critical_risks": [r["product_name"] for r in risks if r["risk_level"] == "CRITICAL"],
            "top_risks": [
                {"product": r["product_name"], "store": r["store_name"], "coverage_days": r["days_of_coverage"]}
                for r in risks[:3]
            ],
        }

        explanation = self._get_explanation(
            question=question,
            intent=intent.intent,
            metrics=metrics_summary,
            evidence=evidence[:5],
            assumptions=assumptions,
            period=period,
            fallback=(
                f"Identified {len(risks)} product/store combinations at stock-out risk. "
                + (f"Top critical risk: {risks[0]['product_name']} in {risks[0]['store_name']} has only {risks[0]['days_of_coverage']} days of coverage." if risks else "No critical stock-out risks found.")
            ),
        )

        return CopilotResponse(
            answer=explanation,
            intent=intent.intent,
            data_status="complete" if risks else "no_data",
            needs_clarification=False,
            evidence=evidence[:10],
            assumptions=assumptions,
            recommendations=recommendations,
        )

    def _handle_overstock(self, question: str, intent: StructuredIntent) -> CopilotResponse:
        overstocked = self.inventory.get_overstocked_products(
            store_id=intent.store_id, category=intent.category
        )
        period = {"window_days": 30}
        evidence = self.evidence_builder.for_overstock(overstocked, period, OVERSTOCK_THRESHOLD_DAYS)

        assumptions = [
            f"Overstock threshold: > {OVERSTOCK_THRESHOLD_DAYS} days of coverage",
            f"Excess Units = Current Stock - (Avg Daily Sales × {OVERSTOCK_THRESHOLD_DAYS} days)",
        ]

        recommendations = []
        for o in overstocked[:5]:
            recommendations.append(
                f"Pause replenishment for {o['product_name']} at {o['store_name']}. Estimated excess: {o['excess_inventory_units']} units (₹{o['excess_capital_inr']:,.2f} capital)."
            )

        metrics_summary = {
            "total_overstocked_items": len(overstocked),
            "top_excess": [
                {"product": o["product_name"], "store": o["store_name"], "coverage_days": o["days_of_coverage"], "excess_units": o["excess_inventory_units"]}
                for o in overstocked[:3]
            ],
        }

        explanation = self._get_explanation(
            question=question,
            intent=intent.intent,
            metrics=metrics_summary,
            evidence=evidence[:5],
            assumptions=assumptions,
            period=period,
            fallback=(
                f"Detected {len(overstocked)} overstocked product/store records. "
                + (f"Highest excess: {overstocked[0]['product_name']} in {overstocked[0]['store_name']} with {overstocked[0]['days_of_coverage']} days of coverage." if overstocked else "No overstock detected.")
            ),
        )

        return CopilotResponse(
            answer=explanation,
            intent=intent.intent,
            data_status="complete" if overstocked else "no_data",
            evidence=evidence[:10],
            assumptions=assumptions,
            recommendations=recommendations,
        )

    def _handle_reorder_recommendation(self, question: str, intent: StructuredIntent) -> CopilotResponse:
        if intent.product_id:
            detail = self.inventory.get_product_inventory_detail(intent.product_id)
            stores_need = [s for s in detail["stores"] if s["reorder_recommendation"]["replenishment_needed"]]
            assumptions = [
                f"Target buffer coverage: {TARGET_REORDER_COVERAGE_DAYS} days",
                "Reorder Quantity = max(0, Target Stock - Current Stock)",
            ]
            recommendations = [
                f"Reorder {s['reorder_recommendation']['recommended_reorder_quantity']} units for {s['store_name']} (stock: {s['current_stock']}, avg daily sales: {s['average_daily_sales']})."
                for s in stores_need
            ]
            evidence = [
                {
                    "product_name": detail["product_name"],
                    "store_name": s["store_name"],
                    "current_stock": s["current_stock"],
                    "recommended_reorder_quantity": s["reorder_recommendation"]["recommended_reorder_quantity"],
                }
                for s in detail["stores"]
            ]
            fallback = (
                f"Reorder analysis for {detail['product_name']}: "
                + (f"Replenishment needed in {len(stores_need)} stores. " + "; ".join(recommendations[:2]) if stores_need else "Stock levels are healthy across all stores.")
            )
            explanation = self._get_explanation(
                question=question, intent=intent.intent, metrics=detail, evidence=evidence, assumptions=assumptions, period=detail["analysis_period"], fallback=fallback
            )
            return CopilotResponse(
                answer=explanation, intent=intent.intent, data_status="complete", evidence=evidence, assumptions=assumptions, recommendations=recommendations
            )
        else:
            return self._handle_inventory_risk(question, intent)

    def _handle_inventory_health(self, question: str, intent: StructuredIntent) -> CopilotResponse:
        summary = self.inventory.get_inventory_health_summary(store_id=intent.store_id)
        assumptions = [
            f"Coverage thresholds: Critical < {RISK_THRESHOLD_CRITICAL}d, High {RISK_THRESHOLD_CRITICAL}-{RISK_THRESHOLD_HIGH}d, Overstock > {OVERSTOCK_THRESHOLD_DAYS}d",
        ]
        evidence = [summary]
        dist = summary["risk_distribution"]
        fallback = (
            f"Inventory Health Summary: Total stock is {summary['total_stock_units']} units (₹{summary['total_stock_value_inr']:,.2f}). "
            f"Portfolio status: {dist['critical']} critical stock-out risks, {dist['high']} high risks, {summary['overstocked_records']} overstocked items, and {dist['low']} healthy items ({summary['percentages']['healthy_pct']}% healthy)."
        )
        explanation = self._get_explanation(
            question=question, intent=intent.intent, metrics=summary, evidence=evidence, assumptions=assumptions, period=summary["analysis_period"], fallback=fallback
        )
        return CopilotResponse(
            answer=explanation, intent=intent.intent, data_status="complete", evidence=evidence, assumptions=assumptions
        )

    def _handle_attention_items(self, question: str, intent: StructuredIntent) -> CopilotResponse:
        items = self.inventory.get_attention_items(store_id=intent.store_id, limit=intent.limit or 10)
        evidence = self.evidence_builder.for_attention(items)
        recommendations = [it["recommended_action"] for it in items if it.get("recommended_action")]
        assumptions = [
            "Attention items prioritize Critical stock-outs, severe sales surges (>=1.8x), sales drops (<=0.4x), and high overstock capital."
        ]
        fallback = (
            f"Attention Feed: Found {len(items)} priority items requiring review. "
            + (f"Top action: {items[0]['title']} — {items[0]['recommended_action']}" if items else "No immediate critical alerts.")
        )
        explanation = self._get_explanation(
            question=question, intent=intent.intent, metrics={"items_count": len(items)}, evidence=evidence[:5], assumptions=assumptions, period={}, fallback=fallback
        )
        return CopilotResponse(
            answer=explanation, intent=intent.intent, data_status="complete", evidence=evidence, assumptions=assumptions, recommendations=recommendations
        )

    def _handle_sales_summary(self, question: str, intent: StructuredIntent) -> CopilotResponse:
        summary = self.sales.get_sales_summary(
            start_date=intent.start_date, end_date=intent.end_date, store_id=intent.store_id
        )
        evidence = self.evidence_builder.for_sales_summary(summary)
        is_partial = summary.get("period", {}).get("is_partial", False)
        
        assumptions = ["Sales figures calculated directly from recorded transaction receipts."]
        if not summary["has_data"]:
            return CopilotResponse(
                answer="No sales data found for the specified period.",
                intent=intent.intent,
                data_status="no_data",
                evidence=[],
                assumptions=assumptions,
            )

        data_status = "incomplete" if is_partial else "complete"
        if is_partial:
            assumptions.append("Incomplete data: The requested time window extends beyond available dataset dates.")

        partial_suffix = " (Note: The requested period is incomplete; results reflect available records)." if is_partial else ""
        fallback = (
            f"Sales Summary: Total revenue is ₹{summary['total_revenue']:,.2f} across {summary['total_units_sold']} units sold in {summary['total_transactions']} transactions "
            f"(Average daily revenue: ₹{summary['average_daily_revenue']:,.2f}).{partial_suffix}"
        )
        explanation = self._get_explanation(
            question=question, intent=intent.intent, metrics=summary, evidence=evidence, assumptions=assumptions, period=summary.get("period", {}), fallback=fallback
        )
        return CopilotResponse(
            answer=explanation, intent=intent.intent, data_status=data_status, evidence=evidence, assumptions=assumptions
        )

    def _handle_product_performance(self, question: str, intent: StructuredIntent) -> CopilotResponse:
        perf = self.sales.get_product_performance(
            product_id=intent.product_id, start_date=intent.start_date, end_date=intent.end_date
        )
        evidence = self.evidence_builder.for_product_performance(perf)
        is_partial = perf.get("period", {}).get("is_partial", False)
        
        assumptions = []
        if not perf["has_data"]:
            return CopilotResponse(
                answer=f"No sales recorded for {perf['product_name']} in the requested period.",
                intent=intent.intent,
                data_status="no_data",
                evidence=[],
                assumptions=assumptions,
            )

        data_status = "incomplete" if is_partial else "complete"
        if is_partial:
            assumptions.append("Incomplete data: The requested date range extends beyond available transaction boundaries.")

        partial_suffix = " (Note: The requested period is incomplete; results reflect available transaction dates)." if is_partial else ""
        fallback = (
            f"Performance for {perf['product_name']} ({perf['category']}): "
            f"Generated ₹{perf['total_revenue']:,.2f} in revenue ({perf['total_units_sold']} units sold) across {perf['selling_days']} selling days "
            f"(Average daily sales: {perf['average_daily_sales']} units/day).{partial_suffix}"
        )
        explanation = self._get_explanation(
            question=question, intent=intent.intent, metrics=perf, evidence=evidence, assumptions=assumptions, period=perf.get("period", {}), fallback=fallback
        )
        return CopilotResponse(
            answer=explanation, intent=intent.intent, data_status=data_status, evidence=evidence, assumptions=assumptions
        )

    def _handle_store_performance(self, question: str, intent: StructuredIntent) -> CopilotResponse:
        perf = self.sales.get_store_performance(
            store_id=intent.store_id, start_date=intent.start_date, end_date=intent.end_date
        )
        evidence = self.evidence_builder.for_store_performance(perf)
        is_partial = perf.get("period", {}).get("is_partial", False)
        
        assumptions = []
        if not perf["has_data"]:
            return CopilotResponse(
                answer=f"No sales recorded for {perf['store_name']} in the requested period.",
                intent=intent.intent,
                data_status="no_data",
                evidence=[],
                assumptions=assumptions,
            )

        data_status = "incomplete" if is_partial else "complete"
        if is_partial:
            assumptions.append("Incomplete data: The requested date range extends beyond available store transaction boundaries.")

        partial_suffix = " (Note: The requested period is incomplete; results reflect available transaction dates)." if is_partial else ""
        fallback = (
            f"Performance for {perf['store_name']} ({perf['city']}): "
            f"Total revenue: ₹{perf['total_revenue']:,.2f}, Units sold: {perf['total_units_sold']}, Transactions: {perf['total_transactions']} "
            f"(Average daily revenue: ₹{perf['average_daily_revenue']:,.2f}).{partial_suffix}"
        )
        explanation = self._get_explanation(
            question=question, intent=intent.intent, metrics=perf, evidence=evidence, assumptions=assumptions, period=perf.get("period", {}), fallback=fallback
        )
        return CopilotResponse(
            answer=explanation, intent=intent.intent, data_status=data_status, evidence=evidence, assumptions=assumptions
        )

    def _handle_store_comparison(self, question: str, intent: StructuredIntent) -> CopilotResponse:
        if intent.product_id:
            res = self.sales.get_store_product_performance(
                product_id=intent.product_id, start_date=intent.start_date, end_date=intent.end_date
            )
            evidence = self.evidence_builder.for_store_comparison(
                res["stores"], product_name=res["product_name"], analysis_period=res.get("period")
            )
            fallback = (
                f"For {res['product_name']}, the top-performing location by unit volume is {res['best_store_by_units']}. "
                f"Top location by revenue is {res['best_store_by_revenue']}."
            )
            explanation = self._get_explanation(
                question=question, intent=intent.intent, metrics=res, evidence=evidence, assumptions=[], period=res.get("period", {}), fallback=fallback
            )
            return CopilotResponse(
                answer=explanation, intent=intent.intent, data_status="complete", evidence=evidence
            )
        else:
            comp = self.sales.compare_stores(start_date=intent.start_date, end_date=intent.end_date)
            evidence = self.evidence_builder.for_store_comparison(comp["stores"], analysis_period=comp.get("period"))
            top_store = comp["stores"][0] if comp["stores"] else None
            fallback = (
                f"Store Comparison: Evaluated {comp['total_stores_compared']} stores. "
                + (f"Top store is {top_store['store_name']} with ₹{top_store['revenue']:,.2f} revenue ({top_store['units_sold']} units)." if top_store else "")
            )
            explanation = self._get_explanation(
                question=question, intent=intent.intent, metrics=comp, evidence=evidence, assumptions=[], period=comp.get("period", {}), fallback=fallback
            )
            return CopilotResponse(
                answer=explanation, intent=intent.intent, data_status="complete", evidence=evidence
            )

    def _handle_product_comparison(self, question: str, intent: StructuredIntent) -> CopilotResponse:
        top_prods = self.sales.get_top_products(
            by="revenue", limit=intent.limit or 5, start_date=intent.start_date, end_date=intent.end_date, store_id=intent.store_id
        )
        evidence = self.evidence_builder.for_product_comparison(top_prods["top_products"], analysis_period=top_prods.get("period"))
        top_1 = top_prods["top_products"][0] if top_prods["top_products"] else None
        fallback = (
            f"Top Products: Ranked by revenue. "
            + (f"#1 product is {top_1['product_name']} with ₹{top_1['revenue']:,.2f} revenue ({top_1['units_sold']} units sold)." if top_1 else "")
        )
        explanation = self._get_explanation(
            question=question, intent=intent.intent, metrics=top_prods, evidence=evidence, assumptions=[], period=top_prods.get("period", {}), fallback=fallback
        )
        return CopilotResponse(
            answer=explanation, intent=intent.intent, data_status="complete", evidence=evidence
        )

    def _handle_category_performance(self, question: str, intent: StructuredIntent) -> CopilotResponse:
        res = self.sales.get_category_performance(start_date=intent.start_date, end_date=intent.end_date)
        evidence = res["categories"]
        top_cat = res["categories"][0] if res["categories"] else None
        fallback = (
            f"Category Performance: Total revenue across categories is ₹{res['total_revenue']:,.2f}. "
            + (f"Leading category is {top_cat['category']} contributing ₹{top_cat['revenue']:,.2f} ({top_cat['revenue_percentage']}% of revenue)." if top_cat else "")
        )
        explanation = self._get_explanation(
            question=question, intent=intent.intent, metrics=res, evidence=evidence, assumptions=[], period=res.get("period", {}), fallback=fallback
        )
        return CopilotResponse(
            answer=explanation, intent=intent.intent, data_status="complete", evidence=evidence
        )

    def _handle_sales_trend(self, question: str, intent: StructuredIntent) -> CopilotResponse:
        trend = self.sales.get_sales_trend(
            start_date=intent.start_date, end_date=intent.end_date, store_id=intent.store_id, product_id=intent.product_id
        )
        evidence = trend["trend"][:15]
        points = trend["trend"]
        total_rev = sum(p["revenue"] for p in points)
        fallback = (
            f"Sales Trend: Aggregated {len(points)} daily sales data points totaling ₹{total_rev:,.2f}."
            if points else "No trend points available for the selected range."
        )
        explanation = self._get_explanation(
            question=question, intent=intent.intent, metrics={"points": len(points), "total_revenue": total_rev}, evidence=evidence, assumptions=[], period=trend["filters"], fallback=fallback
        )
        return CopilotResponse(
            answer=explanation, intent=intent.intent, data_status="complete" if points else "no_data", evidence=evidence
        )

    # --------------------------------------------------------------------------
    # Explanation Fallback Wrapper
    # --------------------------------------------------------------------------

    def _get_explanation(
        self,
        question: str,
        intent: str,
        metrics: Dict[str, Any],
        evidence: List[Dict[str, Any]],
        assumptions: List[str],
        period: Dict[str, Any],
        fallback: str,
    ) -> str:
        """Call Gemini explanation engine with safe fallback to deterministic text."""
        if not self.gemini.is_configured:
            return fallback

        try:
            result = self.gemini.generate_explanation(
                question=question,
                intent=intent,
                metrics=metrics,
                evidence=evidence,
                assumptions=assumptions,
                period=period,
            )
            explanation_text = result.get("explanation")
            if explanation_text and not result.get("error") and result.get("is_available"):
                return explanation_text
            return fallback
        except Exception as exc:
            logger.warning("Gemini explanation failed: %s", exc)
            return fallback

    # Backwards compatibility
    def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Backwards compatibility adapter returning dict."""
        resp = self.answer_question(query)
        return {
            "query": query,
            "intent": resp.intent,
            "answer": resp.answer,
            "evidence": resp.evidence,
        }


# Global helper function matching specifications
def answer_question(question: str) -> CopilotResponse:
    """Standalone helper function to answer retail questions through the copilot."""
    copilot = RetailCopilot()
    return copilot.answer_question(question)
