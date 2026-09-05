"""Gemini API client stub (placeholder for later integration)."""

from typing import Any, Dict, Optional


class GeminiClient:
    """Placeholder client for Gemini API.

    Will be implemented in a subsequent stage.
    No network requests or external calls are performed in Stage 1.
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key
        self.is_configured = bool(api_key)

    def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Placeholder for generating grounded copilot responses."""
        return {
            "text": "Gemini integration placeholder. Active integration will occur in later stages.",
            "status": "stub",
            "prompt_length": len(prompt),
        }
