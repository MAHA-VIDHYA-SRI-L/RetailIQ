"""API router definitions for RetailIQ."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from src.models import HealthResponse, CopilotQueryRequest, CopilotQueryResponse
from src.copilot import RetailCopilot
from src.analytics import SalesAnalyticsEngine, EntityNotFoundError, InvalidDateRangeError

router = APIRouter(prefix="/api", tags=["api"])
copilot = RetailCopilot()
analytics = SalesAnalyticsEngine()


@router.get("/health", response_model=HealthResponse)
async def api_health() -> HealthResponse:
    """API health status endpoint."""
    return HealthResponse(status="healthy")


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
