"""Google Gemini API client for RetailIQ.

Handles:
- Structured JSON output generation
- Grounded explanation generation from verified application data
- Graceful failure handling, timeouts, and missing API key resilience
- Strict security: API keys are never logged or exposed
"""

import json
import logging
from typing import Any, Dict, List, Optional
import httpx

from src.config import (
    GEMINI_API_KEY,
    GEMINI_BASE_URL,
    GEMINI_MODEL,
    GEMINI_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)


class GeminiClientError(Exception):
    """Base exception for Gemini client errors."""
    pass


class GeminiTimeoutError(GeminiClientError):
    """Raised when a Gemini API request times out."""
    pass


class GeminiResponseError(GeminiClientError):
    """Raised when Gemini returns malformed JSON or an error response."""
    pass


class GeminiClient:
    """Client for interacting with Google Gemini API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else GEMINI_API_KEY
        self.model = model or GEMINI_MODEL
        self.timeout = timeout if timeout is not None else GEMINI_TIMEOUT_SECONDS
        self.base_url = (base_url or GEMINI_BASE_URL).rstrip("/")
        self.is_configured = bool(self.api_key and self.api_key.strip())

    def _get_api_url(self) -> str:
        """Construct the Gemini generateContent API URL."""
        return f"{self.base_url}/models/{self.model}:generateContent"

    def generate_structured_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.1,
    ) -> Dict[str, Any]:
        """Send prompt to Gemini requesting structured JSON output.

        Returns parsed dictionary.
        Raises GeminiClientError subclasses on timeout, failure, or malformed JSON.
        """
        if not self.is_configured:
            return {
                "error": "Gemini API key is not configured.",
                "is_available": False,
                "status": "unavailable",
            }

        headers = {
            "Content-Type": "application/json",
        }
        params = {
            "key": self.api_key,
        }

        payload: Dict[str, Any] = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": temperature,
            },
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    self._get_api_url(),
                    headers=headers,
                    params=params,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

            # Extract generated content text
            candidates = data.get("candidates", [])
            if not candidates:
                raise GeminiResponseError("Gemini response contained no candidates.")

            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts or "text" not in parts[0]:
                raise GeminiResponseError("Gemini response candidate contained no text part.")

            raw_text = parts[0]["text"].strip()

            # Clean markdown fences if Gemini added ```json ... ```
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()

            parsed_json = json.loads(raw_text)
            return parsed_json

        except httpx.TimeoutException as exc:
            logger.warning("Gemini request timed out.")
            raise GeminiTimeoutError("Gemini API request timed out.") from exc
        except json.JSONDecodeError as exc:
            logger.warning("Gemini returned invalid JSON.")
            raise GeminiResponseError("Malformed JSON in Gemini response.") from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            logger.warning("Gemini HTTP error %s", status)
            raise GeminiClientError(f"Gemini API returned HTTP status {status}.") from exc
        except Exception as exc:
            if not isinstance(exc, GeminiClientError):
                logger.warning("Gemini unexpected error: %s", type(exc).__name__)
                raise GeminiClientError(f"Gemini request failed: {type(exc).__name__}") from exc
            raise

    def generate_explanation(
        self,
        question: str,
        intent: str,
        metrics: Dict[str, Any],
        evidence: List[Dict[str, Any]],
        assumptions: List[str],
        period: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate a grounded natural-language explanation from verified application metrics.

        The model is strictly instructed NOT to invent numbers, products, stores, or outside claims.
        """
        if not self.is_configured:
            return {
                "explanation": "AI explanation is temporarily unavailable (Gemini API key not configured). The verified analytics are displayed directly from local data.",
                "is_available": False,
                "grounded": True,
                "status": "offline_mode",
            }

        system_instruction = (
            "You are RetailIQ's Grounded Explanation Engine. "
            "You explain verified sales analytics and inventory intelligence.\n"
            "STRICT GROUNDING RULES:\n"
            "1. Use ONLY the provided verified metrics, evidence, and assumptions.\n"
            "2. NEVER invent additional numbers, percentages, quantities, or metrics.\n"
            "3. NEVER invent products, stores, or dates not in the input.\n"
            "4. NEVER claim causal factors that are not directly supported by the data.\n"
            "5. If data is partial or insufficient, explicitly acknowledge the limitation.\n"
            "6. Always state the relevant time period.\n"
            "7. Be concise, professional, and actionable for retail decision-makers."
        )

        prompt = (
            f"User Question: {question}\n"
            f"Identified Intent: {intent}\n"
            f"Analysis Period: {json.dumps(period)}\n"
            f"Verified Metrics: {json.dumps(metrics)}\n"
            f"Grounding Evidence: {json.dumps(evidence)}\n"
            f"Configured Assumptions: {json.dumps(assumptions)}\n\n"
            "Provide a concise, grounded explanation of these results in JSON format:\n"
            "{\n"
            '  "summary": "Direct answer to the user\'s question based only on the numbers above",\n'
            '  "key_findings": ["Bullet point 1 using supplied metrics", "Bullet point 2"],\n'
            '  "actionable_recommendation": "Recommendation directly reflecting the supplied reorder/action"\n'
            "}"
        )

        try:
            result = self.generate_structured_json(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=0.1,
            )
            if "error" in result:
                return {
                    "explanation": "AI explanation is temporarily unavailable. The verified analytics are still available.",
                    "is_available": False,
                    "grounded": True,
                    "raw_error": result.get("error"),
                }

            # Synthesize text answer from JSON structure
            summary = result.get("summary", "")
            findings = "\n".join([f"• {f}" for f in result.get("key_findings", [])])
            rec = result.get("actionable_recommendation", "")

            full_explanation = summary
            if findings:
                full_explanation += f"\n\nKey Findings:\n{findings}"
            if rec:
                full_explanation += f"\n\nRecommendation: {rec}"

            return {
                "explanation": full_explanation,
                "summary": summary,
                "key_findings": result.get("key_findings", []),
                "recommendation": rec,
                "is_available": True,
                "grounded": True,
            }
        except GeminiClientError as exc:
            return {
                "explanation": "AI explanation is temporarily unavailable. The verified analytics are still available.",
                "is_available": False,
                "grounded": True,
                "error": str(exc),
            }
