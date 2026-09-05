"""Unit tests for RetailIQ Gemini client and natural language intent layer.

All tests are hermetic and mock external network calls to Gemini so no live API key is required.
"""

import json
import unittest
from unittest.mock import MagicMock, patch
import httpx
from fastapi.testclient import TestClient

from app import app
from src.gemini_client import (
    GeminiClient,
    GeminiClientError,
    GeminiResponseError,
    GeminiTimeoutError,
)
from src.intent import IntentClassifier


class TestGeminiIntelligenceLayer(unittest.TestCase):
    """Test suite for Gemini client, intent extraction, entity matching, and error resilience."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    # 1. Valid Intent Response from Gemini
    def test_01_valid_intent_response(self) -> None:
        """Verify structured intent when Gemini returns a valid JSON response."""
        mock_gemini = GeminiClient(api_key="mock_test_key")
        mock_gemini.generate_structured_json = MagicMock(
            return_value={
                "intent": "INVENTORY_RISK",
                "product": "Braided Nylon USB-C Cable (2m)",
                "store": "Bengaluru",
                "category": "Accessories",
                "start_date": None,
                "end_date": None,
                "confidence": 0.96,
            }
        )

        classifier = IntentClassifier(gemini_client=mock_gemini)
        intent = classifier.classify("Is the USB-C cable running low in Bengaluru?")

        self.assertEqual(intent.intent, "INVENTORY_RISK")
        self.assertEqual(intent.product_id, "PRD009")
        self.assertEqual(intent.store_id, "STR001")
        self.assertEqual(intent.confidence, 0.96)
        self.assertFalse(intent.needs_clarification)

    # 2. Malformed JSON Response from Gemini
    def test_02_malformed_json_response(self) -> None:
        """Verify that malformed JSON from Gemini triggers safe fallback without crashing."""
        client = GeminiClient(api_key="mock_test_key")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "NOT VALID JSON {broken"}]}}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client.post", return_value=mock_response):
            with self.assertRaises(GeminiResponseError):
                client.generate_structured_json("test prompt")

        # Intent classifier falls back to deterministic rule when Gemini raises GeminiResponseError
        failing_gemini = GeminiClient(api_key="mock_test_key")
        failing_gemini.generate_structured_json = MagicMock(
            side_effect=GeminiResponseError("Malformed JSON")
        )

        classifier = IntentClassifier(gemini_client=failing_gemini)
        intent = classifier.classify("Which products are likely to run out soon?")
        self.assertEqual(intent.intent, "INVENTORY_RISK")

    # 3. Unknown Intent from Model
    def test_03_unknown_intent(self) -> None:
        """Verify unsupported or unknown intents are caught and handled safely."""
        mock_gemini = GeminiClient(api_key="mock_test_key")
        mock_gemini.generate_structured_json = MagicMock(
            return_value={"intent": "TELL_A_JOKE", "confidence": 0.99}
        )

        classifier = IntentClassifier(gemini_client=mock_gemini)
        intent = classifier.classify("Tell me a funny retail joke.")
        # Rejects TELL_A_JOKE and sets UNKNOWN
        self.assertEqual(intent.intent, "UNKNOWN")

    # 4. Ambiguous Product Request
    def test_04_ambiguous_product_request(self) -> None:
        """Verify ambiguity is detected when multiple products match a vague reference."""
        mock_gemini = GeminiClient(api_key="mock_test_key")
        mock_gemini.generate_structured_json = MagicMock(
            return_value={"intent": "PRODUCT_PERFORMANCE", "product": "wireless"}
        )

        classifier = IntentClassifier(gemini_client=mock_gemini)
        intent = classifier.classify("How is the wireless performing?")

        self.assertTrue(intent.needs_clarification)
        self.assertIsNone(intent.product_id)
        self.assertIsNotNone(intent.clarification_question)
        self.assertIn("multiple products matching", intent.clarification_question)

    # 5. Missing API Key Resilience
    def test_05_missing_api_key(self) -> None:
        """Verify that an unconfigured API key does not crash the client or classifier."""
        unconfigured_client = GeminiClient(api_key="")
        self.assertFalse(unconfigured_client.is_configured)

        res = unconfigured_client.generate_structured_json("prompt")
        self.assertFalse(res["is_available"])
        self.assertEqual(res["status"], "unavailable")

        expl = unconfigured_client.generate_explanation(
            question="q", intent="i", metrics={}, evidence=[], assumptions=[], period={}
        )
        self.assertFalse(expl["is_available"])
        self.assertIn("temporarily unavailable", expl["explanation"])

        # Intent classifier functions fully in deterministic offline mode
        classifier = IntentClassifier(gemini_client=unconfigured_client)
        intent = classifier.classify("Which store performs best for keyboards?")
        self.assertEqual(intent.intent, "STORE_COMPARISON")

    # 6. Gemini API Failure (HTTP Error)
    def test_06_gemini_api_failure(self) -> None:
        """Verify handling of Gemini API 500 error."""
        client = GeminiClient(api_key="mock_test_key")

        mock_req = MagicMock()
        mock_resp = MagicMock(status_code=500)
        http_error = httpx.HTTPStatusError("Server Error", request=mock_req, response=mock_resp)

        with patch("httpx.Client.post", side_effect=http_error):
            with self.assertRaises(GeminiClientError):
                client.generate_structured_json("prompt")

    # 7. Request Timeout Handling
    def test_07_gemini_timeout(self) -> None:
        """Verify that timeout exceptions are converted into GeminiTimeoutError."""
        client = GeminiClient(api_key="mock_test_key", timeout=0.1)

        with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Timeout")):
            with self.assertRaises(GeminiTimeoutError):
                client.generate_structured_json("prompt")

    # 8. Invalid / Non-Existent Entity
    def test_08_invalid_entity(self) -> None:
        """Verify non-existent products/stores are not accepted into database IDs."""
        mock_gemini = GeminiClient(api_key="mock_test_key")
        mock_gemini.generate_structured_json = MagicMock(
            return_value={
                "intent": "PRODUCT_PERFORMANCE",
                "product": "Quantum Teleporter 3000",
                "store": "Atlantis",
            }
        )

        classifier = IntentClassifier(gemini_client=mock_gemini)
        intent = classifier.classify("Check sales for Quantum Teleporter 3000 in Atlantis.")

        self.assertIsNone(intent.product_id)
        self.assertIsNone(intent.store_id)
        self.assertEqual(intent.product, "Quantum Teleporter 3000")
        self.assertEqual(intent.store, "Atlantis")

    # 9. Explanation with Verified Evidence
    def test_09_explanation_with_verified_evidence(self) -> None:
        """Verify explanation generator packages grounded summary from metrics."""
        mock_gemini = GeminiClient(api_key="mock_test_key")
        mock_gemini.generate_structured_json = MagicMock(
            return_value={
                "summary": "Braided USB-C Cable has only 2.7 days of inventory coverage in Bengaluru.",
                "key_findings": [
                    "Current stock is 12 units against average daily sales of 4.37 units.",
                    "Coverage is below the 3-day critical threshold.",
                ],
                "actionable_recommendation": "Review replenishment and reorder 80 units immediately.",
            }
        )

        result = mock_gemini.generate_explanation(
            question="Why is the USB-C cable at risk in Bengaluru?",
            intent="INVENTORY_RISK",
            metrics={"current_stock": 12, "days_of_coverage": 2.7},
            evidence=[{"product_id": "PRD009", "store_id": "STR001"}],
            assumptions=["Critical threshold: < 3.0 days"],
            period={"start_date": "2026-08-06", "end_date": "2026-09-04"},
        )

        self.assertTrue(result["is_available"])
        self.assertTrue(result["grounded"])
        self.assertIn("2.7 days", result["explanation"])
        self.assertIn("80 units", result["explanation"])

    # 10. Explanation Error Fallback
    def test_10_explanation_error_fallback(self) -> None:
        """Verify explanation returns safe fallback message on API failure without crashing."""
        mock_gemini = GeminiClient(api_key="mock_test_key")
        mock_gemini.generate_structured_json = MagicMock(
            side_effect=GeminiClientError("API connection reset")
        )

        result = mock_gemini.generate_explanation(
            question="Explain risk",
            intent="INVENTORY_RISK",
            metrics={},
            evidence=[],
            assumptions=[],
            period={},
        )

        self.assertFalse(result["is_available"])
        self.assertIn("AI explanation is temporarily unavailable", result["explanation"])
        self.assertIn("verified analytics are still available", result["explanation"])

    # 11. API Copilot Intent Endpoint
    def test_11_api_copilot_intent_endpoint(self) -> None:
        """Verify POST /api/copilot/intent returns 200 with structured JSON."""
        response = self.client.post(
            "/api/copilot/intent",
            json={"question": "Which products are likely to run out soon?"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["intent"], "INVENTORY_RISK")
        self.assertIn("confidence", data)
        self.assertFalse(data["needs_clarification"])


if __name__ == "__main__":
    unittest.main()
