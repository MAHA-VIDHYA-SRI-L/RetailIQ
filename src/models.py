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


class CopilotQueryRequest(BaseModel):
    """Placeholder schema for incoming copilot queries."""
    query: str = Field(..., description="User question or analysis request")
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional search/aggregation filters")


class CopilotQueryResponse(BaseModel):
    """Placeholder schema for copilot responses."""
    answer: str = Field(..., description="Synthesized answer")
    intent: Optional[str] = Field(default=None, description="Identified user intent")
    evidence: List[Dict[str, Any]] = Field(default_factory=list, description="Grounding evidence records")
