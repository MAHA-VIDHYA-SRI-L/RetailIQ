"""API router definitions for RetailIQ."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from src.models import (
    HealthResponse,
    CopilotQueryRequest,
    CopilotQueryResponse,
    CopilotQuestionRequest,
    CopilotResponse,
    IntentRequest,
    StructuredIntent,
)
from src.copilot import RetailCopilot
from src.analytics import SalesAnalyticsEngine, EntityNotFoundError, InvalidDateRangeError
from src.inventory import InventoryIntelligenceEngine
from src.intent import IntentClassifier
from src.database import get_products, get_stores

router = APIRouter(prefix="/api", tags=["api"])
copilot = RetailCopilot()
analytics = SalesAnalyticsEngine()
inventory = InventoryIntelligenceEngine()


@router.get("/health", response_model=HealthResponse)
async def api_health() -> HealthResponse:
    """API health status endpoint."""
    return HealthResponse(status="healthy")


@router.get("/catalog/products")
async def list_catalog_products(category: Optional[str] = Query(None)) -> List[Dict[str, Any]]:
    """Retrieve product catalog for UI selection."""
    return get_products(category=category)


@router.get("/catalog/stores")
async def list_catalog_stores() -> List[Dict[str, Any]]:
    """Retrieve store locations for UI selection."""
    return get_stores()


intent_classifier = IntentClassifier()


@router.post("/copilot", response_model=CopilotResponse)
async def ask_copilot(request: CopilotQuestionRequest) -> CopilotResponse:
    """End-to-end RetailIQ AI Copilot query endpoint.
    
    Coordinates intent detection, deterministic SQL analytics, verified evidence
    generation, and safe natural-language explanation.
    """
    if not request.question or not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty or whitespace only."
        )
    if len(request.question) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Question is excessively large (max 1000 characters allowed)."
        )
    try:
        response = copilot.answer_question(request.question)
        return response
    except Exception as exc:
        # Never expose stack traces or credentials
        return CopilotResponse(
            answer="An unexpected error occurred while processing your question.",
            intent="UNKNOWN",
            data_status="unavailable",
            needs_clarification=False,
            error="Internal processing error.",
        )


@router.post("/copilot/intent", response_model=StructuredIntent)
async def analyze_intent(request: IntentRequest) -> StructuredIntent:
    """Analyze a natural-language question and return the validated structured intent."""
    return intent_classifier.classify(request.question)


@router.post("/query", response_model=CopilotQueryResponse)
async def api_query(request: CopilotQueryRequest) -> CopilotQueryResponse:
    """Placeholder endpoint for querying the Retail Copilot."""
    result = copilot.process_query(request.query, request.filters)
    return CopilotQueryResponse(
        answer=result["answer"],
        intent=result["intent"],
        evidence=result["evidence"],
    )


# --------------------------------------------------------------------------
# Deterministic Sales Analytics Endpoints
# --------------------------------------------------------------------------

@router.get("/analytics/summary")
async def get_summary(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    store_id: Optional[str] = Query(None, description="Optional store filter"),
) -> Dict[str, Any]:
    """Retrieve overall sales summary."""
    try:
        return analytics.get_sales_summary(start_date=start_date, end_date=end_date, store_id=store_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidDateRangeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/analytics/products/{product_id}")
async def get_product_analytics(
    product_id: str,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
) -> Dict[str, Any]:
    """Retrieve sales performance for a specific product."""
    try:
        return analytics.get_product_performance(product_id=product_id, start_date=start_date, end_date=end_date)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidDateRangeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/analytics/products/{product_id}/stores")
async def get_product_stores_analytics(
    product_id: str,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
) -> Dict[str, Any]:
    """Retrieve store-by-store sales comparison for a product ('Which store sells this best?')."""
    try:
        return analytics.get_store_product_performance(product_id=product_id, start_date=start_date, end_date=end_date)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidDateRangeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/analytics/stores/{store_id}")
async def get_store_analytics(
    store_id: str,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
) -> Dict[str, Any]:
    """Retrieve sales performance for a specific store."""
    try:
        return analytics.get_store_performance(store_id=store_id, start_date=start_date, end_date=end_date)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidDateRangeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/analytics/trend")
async def get_sales_trend(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    store_id: Optional[str] = Query(None, description="Optional store filter"),
    product_id: Optional[str] = Query(None, description="Optional product filter"),
) -> Dict[str, Any]:
    """Retrieve chronological daily sales trend data suitable for charts."""
    try:
        return analytics.get_sales_trend(
            start_date=start_date, end_date=end_date, store_id=store_id, product_id=product_id
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidDateRangeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/analytics/top-products")
async def get_top_products(
    by: str = Query("revenue", description="Ranking metric: 'revenue' or 'units'"),
    limit: int = Query(5, ge=1, le=50, description="Number of items to return"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    store_id: Optional[str] = Query(None, description="Optional store filter"),
) -> Dict[str, Any]:
    """Retrieve top-performing products ranked by revenue or units."""
    try:
        return analytics.get_top_products(
            by=by, limit=limit, start_date=start_date, end_date=end_date, store_id=store_id
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except (ValueError, InvalidDateRangeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/analytics/categories")
async def get_category_analytics(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
) -> Dict[str, Any]:
    """Retrieve category-level revenue, units, and percentage contributions."""
    try:
        return analytics.get_category_performance(start_date=start_date, end_date=end_date)
    except InvalidDateRangeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/analytics/compare-periods")
async def compare_periods_endpoint(
    current_start: str = Query(..., description="Current period start date (YYYY-MM-DD)"),
    current_end: str = Query(..., description="Current period end date (YYYY-MM-DD)"),
    previous_start: str = Query(..., description="Previous period start date (YYYY-MM-DD)"),
    previous_end: str = Query(..., description="Previous period end date (YYYY-MM-DD)"),
    store_id: Optional[str] = Query(None, description="Optional store filter"),
    product_id: Optional[str] = Query(None, description="Optional product filter"),
) -> Dict[str, Any]:
    """Compare performance across two distinct periods with growth percentage calculations."""
    try:
        return analytics.compare_periods(
            current_start=current_start,
            current_end=current_end,
            previous_start=previous_start,
            previous_end=previous_end,
            store_id=store_id,
            product_id=product_id,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidDateRangeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# --------------------------------------------------------------------------
# Deterministic Inventory Intelligence Endpoints
# --------------------------------------------------------------------------

@router.get("/inventory/health")
async def get_inventory_health(
    store_id: Optional[str] = Query(None, description="Optional store filter"),
) -> Dict[str, Any]:
    """Retrieve overall inventory health summary, risk distribution, and portfolio metrics."""
    try:
        return inventory.get_inventory_health_summary(store_id=store_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/inventory/risks")
async def get_inventory_risks(
    store_id: Optional[str] = Query(None, description="Optional store filter"),
    risk_level: Optional[str] = Query(None, description="Filter by exact risk level: CRITICAL, HIGH, MEDIUM"),
    category: Optional[str] = Query(None, description="Optional category filter"),
    min_severity: Optional[str] = Query(None, description="Minimum severity filter: CRITICAL, HIGH"),
) -> List[Dict[str, Any]]:
    """Retrieve items currently at stock-out risk sorted by urgency."""
    try:
        return inventory.get_products_at_risk(
            store_id=store_id, risk_level=risk_level, category=category, min_severity=min_severity
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/inventory/overstock")
async def get_inventory_overstock(
    store_id: Optional[str] = Query(None, description="Optional store filter"),
    category: Optional[str] = Query(None, description="Optional category filter"),
    threshold_days: Optional[float] = Query(None, description="Custom overstock coverage threshold in days"),
) -> List[Dict[str, Any]]:
    """Retrieve items flagged for overstock with excess inventory and capital estimates."""
    try:
        kwargs = {}
        if threshold_days is not None:
            kwargs["threshold_days"] = threshold_days
        return inventory.get_overstocked_products(store_id=store_id, category=category, **kwargs)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/inventory/attention")
async def get_inventory_attention(
    store_id: Optional[str] = Query(None, description="Optional store filter"),
    limit: int = Query(15, ge=1, le=50, description="Max attention items to return"),
) -> List[Dict[str, Any]]:
    """Retrieve prioritized attention items combining stock-out, overstock, spike, and drop signals."""
    try:
        return inventory.get_attention_items(store_id=store_id, limit=limit)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/inventory/velocity")
async def get_inventory_velocity(
    window_days: Optional[int] = Query(None, description="Historical demand window days"),
) -> Dict[str, Any]:
    """Classify products into Fast, Medium, and Slow moving tiers."""
    return inventory.classify_product_velocities(window_days=window_days)


@router.get("/inventory/{product_id}")
async def get_product_inventory_route(product_id: str) -> Dict[str, Any]:
    """Retrieve detailed store-level inventory and replenishment recommendations for a product."""
    try:
        return inventory.get_product_inventory_detail(product_id=product_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
