"""Data models and schemas for RetailIQ."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str = Field(default="healthy", description="Application health status")


class StatusResponse(BaseModel):
    """Root status response schema."""
    message: str = Field(default="RetailIQ is running", description="Status message")
    status: str = Field(default="ok", description="Operational status")
    app: str = Field(default="RetailIQ", description="Application name")
    track: str = Field(default="PS03", description="Hackathon track identifier")
    version: str = Field(default="0.1.0", description="Application version")


class CopilotQueryRequest(BaseModel):
    """Placeholder schema for incoming copilot queries."""
    query: str = Field(..., description="User question or analysis request")
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional search/aggregation filters")


class CopilotQueryResponse(BaseModel):
    """Placeholder schema for copilot responses."""
    answer: str = Field(..., description="Synthesized answer")
    intent: Optional[str] = Field(default=None, description="Identified user intent")
    evidence: List[Dict[str, Any]] = Field(default_factory=list, description="Grounding evidence records")
