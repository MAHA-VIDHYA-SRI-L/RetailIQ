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


class Product(BaseModel):
    """Retail product schema."""
    product_id: str = Field(..., description="Unique product identifier")
    product_name: str = Field(..., description="Human-readable product name")
    category: str = Field(..., description="Product category")
    unit_price: float = Field(..., description="Unit price in INR")
    reorder_level: int = Field(..., description="Inventory reorder threshold")


class Store(BaseModel):
    """Retail store schema."""
    store_id: str = Field(..., description="Unique store identifier")
    store_name: str = Field(..., description="Store location name")
    city: str = Field(..., description="City where store is situated")


class Sale(BaseModel):
    """Sales transaction record schema."""
    sale_id: str = Field(..., description="Unique transaction identifier")
    date: str = Field(..., description="Transaction date (YYYY-MM-DD)")
    store_id: str = Field(..., description="Store where sale occurred")
    product_id: str = Field(..., description="Product sold")
    quantity: int = Field(..., description="Quantity sold")
    unit_price: float = Field(..., description="Unit price at time of sale")
    revenue: float = Field(..., description="Total line revenue (quantity * unit_price)")


class Inventory(BaseModel):
    """Store inventory record schema."""
    store_id: str = Field(..., description="Store identifier")
    product_id: str = Field(..., description="Product identifier")
    current_stock: int = Field(..., description="Current on-hand inventory units")
    reorder_level: int = Field(..., description="Reorder threshold for this product/store")


class IntentRequest(BaseModel):
    """Input query request for intent classification."""
    question: str = Field(..., description="Natural-language question from retail operator")


class StructuredIntent(BaseModel):
    """Validated structured intent extracted from natural language."""
    intent: str = Field(..., description="Selected application intent enum")
    product: Optional[str] = Field(default=None, description="Extracted product name")
    product_id: Optional[str] = Field(default=None, description="Verified database product ID")
    store: Optional[str] = Field(default=None, description="Extracted store name or city")
    store_id: Optional[str] = Field(default=None, description="Verified database store ID")
    category: Optional[str] = Field(default=None, description="Extracted category")
    start_date: Optional[str] = Field(default=None, description="Resolved start date YYYY-MM-DD")
    end_date: Optional[str] = Field(default=None, description="Resolved end date YYYY-MM-DD")
    comparison: Optional[str] = Field(default=None, description="Comparison type if requested")
    limit: Optional[int] = Field(default=None, description="Requested top/bottom item limit")
    needs_clarification: bool = Field(default=False, description="Whether ambiguity requires user clarification")
    clarification_question: Optional[str] = Field(default=None, description="Clarification prompt for ambiguous query")
    confidence: float = Field(default=0.95, description="Model confidence score")
    raw_query: Optional[str] = Field(default=None, description="Original user query")
    date_resolution_note: Optional[str] = Field(default=None, description="Audit note on date mapping")


class EvidenceFirstResponse(BaseModel):
    """Grounding-backed copilot response structure."""
    answer: str = Field(..., description="Natural-language synthesized explanation")
    intent: str = Field(..., description="Recognized intent")
    evidence: List[Dict[str, Any]] = Field(default_factory=list, description="Verified supporting records")
    assumptions: List[str] = Field(default_factory=list, description="Applied heuristics and thresholds")
    needs_clarification: bool = Field(default=False, description="Whether question was ambiguous")
    data_status: str = Field(default="complete", description="complete | partial | no_data")
    error: Optional[str] = Field(default=None, description="Application error message if any")


class CopilotQueryRequest(BaseModel):
    """Schema for copilot question requests."""
    query: str = Field(..., description="User question or analysis request")
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional search/aggregation filters")


class CopilotQueryResponse(BaseModel):
    """Schema for copilot responses."""
    answer: str = Field(..., description="Synthesized answer")
    intent: Optional[str] = Field(default=None, description="Identified user intent")
    evidence: List[Dict[str, Any]] = Field(default_factory=list, description="Grounding evidence records")
