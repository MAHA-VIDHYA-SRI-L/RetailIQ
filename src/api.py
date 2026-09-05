"""API router definitions for RetailIQ."""

from fastapi import APIRouter
from src.models import HealthResponse, StatusResponse, CopilotQueryRequest, CopilotQueryResponse
from src.copilot import RetailCopilot

router = APIRouter(prefix="/api", tags=["api"])
copilot = RetailCopilot()


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
