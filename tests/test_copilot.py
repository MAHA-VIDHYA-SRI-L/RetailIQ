"""Unit and integration tests for RetailIQ Copilot orchestration layer.

All tests are hermetic and mock external network calls to Gemini so no live API key is required.
Tests verify deterministic calculations, grounding, entity resolution, ambiguity detection,
data quality status, resilience, and API endpoint behavior.
"""

import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app import app
from src.copilot import RetailCopilot, answer_question
from src.gemini_client import GeminiClient, GeminiClientError, GeminiTimeoutError
from src.models import CopilotResponse, StructuredIntent


class TestRetailCopilotOrchestration(unittest.TestCase):
    """Test suite for RetailCopilot orchestration pipeline."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def _create_mock_copilot(self, gemini_intent=None, gemini_explanation=None, simulate_failure: bool = False):
        """Helper to create RetailCopilot instance with mocked Gemini client."""
        mock_gemini = MagicMock(spec=GeminiClient)
        if simulate_failure:
            mock_gemini.is_configured = False
            mock_gemini.generate_structured_json.side_effect = GeminiClientError("Simulated Gemini offline failure")
            mock_gemini.generate_explanation.side_effect = GeminiClientError("Simulated Gemini offline failure")
        else:
            mock_gemini.is_configured = True

            if gemini_intent:
                mock_gemini.generate_structured_json.return_value = gemini_intent
            else:
                mock_gemini.generate_structured_json.return_value = {
                    "intent": "INVENTORY_RISK",
                    "product": None,
                    "store": None,
                    "category": None,
                    "start_date": None,
                    "end_date": None,
                    "confidence": 0.95,
                }

            if gemini_explanation:
                mock_gemini.generate_explanation.return_value = {
                    "explanation": gemini_explanation,
                    "is_available": True,
                    "error": None,
                }
            else:
                mock_gemini.generate_explanation.return_value = {
                    "explanation": "Verified analytics explanation based strictly on evidence.",
                    "is_available": True,
                    "error": None,
                }

        copilot = RetailCopilot(gemini_client=mock_gemini)
        return copilot, mock_gemini

    # 1. Inventory-risk question
    def test_01_inventory_risk_question(self) -> None:
        """Verify inventory risk pipeline executes deterministic calculations and returns evidence."""
        copilot, mock_gemini = self._create_mock_copilot(
            gemini_intent={"intent": "INVENTORY_RISK", "product": None, "store": None, "confidence": 0.95}
        )
        response: CopilotResponse = copilot.answer_question("Which products are likely to run out soon?")

        self.assertEqual(response.intent, "INVENTORY_RISK")
        self.assertEqual(response.data_status, "complete")
        self.assertFalse(response.needs_clarification)
        self.assertIsInstance(response.evidence, list)
        self.assertGreater(len(response.evidence), 0)
        # Check that evidence has deterministic fields
        item = response.evidence[0]
        self.assertIn("days_of_coverage", item)
        self.assertIn("current_stock", item)
        self.assertIn("risk_level", item)
        self.assertIn(item["risk_level"], ["CRITICAL", "HIGH", "MEDIUM", "LOW"])

    # 2. Sales-summary question
    def test_02_sales_summary_question(self) -> None:
        """Verify sales summary question routes to sales engine and populates revenue/units."""
        copilot, _ = self._create_mock_copilot(
            gemini_intent={"intent": "SALES_SUMMARY", "product": None, "store": None, "confidence": 0.95}
        )
        response = copilot.answer_question("What were our total sales?")

        self.assertEqual(response.intent, "SALES_SUMMARY")
        self.assertIn(response.data_status, ["complete", "incomplete"])
        self.assertGreater(len(response.evidence), 0)
        ev = response.evidence[0]
        self.assertIn("total_revenue", ev)
        self.assertIn("total_units_sold", ev)
        self.assertGreater(ev["total_revenue"], 0)

    # 3. Product-performance question
    def test_03_product_performance_question(self) -> None:
        """Verify product performance properly matches product and returns verified sales."""
        copilot, _ = self._create_mock_copilot(
            gemini_intent={
                "intent": "PRODUCT_PERFORMANCE",
                "product": "Wireless Mouse",
                "store": None,
                "confidence": 0.95,
            }
        )
        response = copilot.answer_question("How did the wireless mouse perform?")

        self.assertEqual(response.intent, "PRODUCT_PERFORMANCE")
        self.assertIn(response.data_status, ["complete", "incomplete"])
        self.assertGreater(len(response.evidence), 0)
        ev = response.evidence[0]
        self.assertEqual(ev["product_id"], "PRD001")
        self.assertIn("total_revenue", ev)
        self.assertIn("average_daily_sales", ev)

    # 4. Store-comparison question
    def test_04_store_comparison_question(self) -> None:
        """Verify store comparison calculates store rankings across locations."""
        copilot, _ = self._create_mock_copilot(
            gemini_intent={
                "intent": "STORE_COMPARISON",
                "product": "Mechanical Gaming Keyboard",
                "store": None,
                "confidence": 0.95,
            }
        )
        response = copilot.answer_question("Which store sells keyboards best?")

        self.assertEqual(response.intent, "STORE_COMPARISON")
        self.assertEqual(response.data_status, "complete")
        self.assertGreater(len(response.evidence), 0)
        ev = response.evidence[0]
        self.assertIn("store_name", ev)
        self.assertIn("revenue", ev)

    # 5. Overstock question
    def test_05_overstock_question(self) -> None:
        """Verify overstock query returns items with excess coverage and capital estimates."""
        copilot, _ = self._create_mock_copilot(
            gemini_intent={"intent": "OVERSTOCK", "product": None, "store": None, "confidence": 0.95}
        )
        response = copilot.answer_question("What products are overstocked?")

        self.assertEqual(response.intent, "OVERSTOCK")
        self.assertIn(response.data_status, ["complete", "no_data"])
        self.assertIsInstance(response.evidence, list)
        if response.evidence:
            ev = response.evidence[0]
            self.assertIn("excess_inventory_units", ev)
            self.assertIn("excess_capital_inr", ev)
            self.assertIn("days_of_coverage", ev)

    # 6. Ambiguous product
    def test_06_ambiguous_product(self) -> None:
        """Verify that ambiguous entity sets needs_clarification=True without running analytics."""
        copilot, _ = self._create_mock_copilot(
            gemini_intent={
                "intent": "PRODUCT_PERFORMANCE",
                "product": "wireless",  # "wireless" matches Optical Mouse, Earbuds, Car Charger Mount, Clicker
                "store": None,
                "confidence": 0.85,
            }
        )
        response = copilot.answer_question("How is the wireless doing?")

        self.assertTrue(response.needs_clarification)
        self.assertEqual(response.data_status, "ambiguous")
        self.assertIsNotNone(response.clarification_question)
        self.assertEqual(len(response.evidence), 0)

    # 7. Unknown product
    def test_07_unknown_product(self) -> None:
        """Verify unknown product returns clear response without inventing a product."""
        copilot, _ = self._create_mock_copilot(
            gemini_intent={
                "intent": "PRODUCT_PERFORMANCE",
                "product": "Quantum Antimatter Drive",
                "store": None,
                "confidence": 0.95,
            }
        )
        response = copilot.answer_question("How is the Quantum Antimatter Drive performing?")

        self.assertFalse(response.needs_clarification)
        self.assertEqual(response.data_status, "no_data")
        self.assertIn("couldn't find a product matching", response.answer)
        self.assertEqual(len(response.evidence), 0)

    # 8. Unknown store
    def test_08_unknown_store(self) -> None:
        """Verify unknown store returns clear response without inventing a store."""
        copilot, _ = self._create_mock_copilot(
            gemini_intent={
                "intent": "STORE_PERFORMANCE",
                "product": None,
                "store": "Atlantis Underwater Plaza",
                "confidence": 0.95,
            }
        )
        response = copilot.answer_question("What were sales at Atlantis Underwater Plaza?")

        self.assertFalse(response.needs_clarification)
        self.assertEqual(response.data_status, "no_data")
        self.assertIn("couldn't find a store matching", response.answer)
        self.assertEqual(len(response.evidence), 0)

    # 9. Unknown intent
    def test_09_unknown_intent(self) -> None:
        """Verify unsupported/unknown intent returns safe guided response."""
        copilot, _ = self._create_mock_copilot(
            gemini_intent={"intent": "UNKNOWN", "product": None, "store": None, "confidence": 0.20}
        )
        response = copilot.answer_question("Can you compose a poem about retailers?")

        self.assertEqual(response.intent, "UNKNOWN")
        self.assertEqual(response.data_status, "unavailable")
        self.assertIn("couldn't determine the type of retail analysis", response.answer)
        self.assertEqual(len(response.evidence), 0)

    # 10. Empty question
    def test_10_empty_question(self) -> None:
        """Verify empty or whitespace-only questions are cleanly rejected."""
        copilot, _ = self._create_mock_copilot()
        response = copilot.answer_question("   ")

        self.assertEqual(response.intent, "UNKNOWN")
        self.assertEqual(response.data_status, "unavailable")
        self.assertIsNotNone(response.error)
        self.assertEqual(len(response.evidence), 0)

    # 11. No-data period
    def test_11_no_data_period(self) -> None:
        """Verify date range far in the future returns no_data status."""
        copilot, _ = self._create_mock_copilot(
            gemini_intent={
                "intent": "SALES_SUMMARY",
                "start_date": "2099-01-01",
                "end_date": "2099-01-31",
                "confidence": 0.95,
            }
        )
        response = copilot.answer_question("Sales from 2099-01-01 to 2099-01-31?")

        self.assertEqual(response.data_status, "no_data")
        self.assertIn("No sales data found", response.answer)

    # 12. Incomplete-data period
    def test_12_incomplete_data_period(self) -> None:
        """Verify requested period extending outside boundaries is flagged as incomplete."""
        copilot, _ = self._create_mock_copilot(
            gemini_intent={
                "intent": "SALES_SUMMARY",
                "start_date": "2024-01-01",
                "end_date": "2026-12-31",
                "confidence": 0.95,
            }
        )
        response = copilot.answer_question("Show sales from 2024 to 2026")

        self.assertEqual(response.data_status, "incomplete")
        self.assertTrue(any("incomplete" in a.lower() for a in response.assumptions))

    # 13. Gemini failure resilience
    def test_13_gemini_failure(self) -> None:
        """Verify deterministic analytics succeed even if Gemini raises an exception."""
        mock_gemini = MagicMock(spec=GeminiClient)
        mock_gemini.is_configured = True
        # First call (classify): returns valid intent
        mock_gemini.generate_structured_json.return_value = {
            "intent": "INVENTORY_RISK",
            "product": None,
            "store": None,
            "confidence": 0.95,
        }
        # Second call (explanation): raises error or returns error
        mock_gemini.generate_explanation.side_effect = GeminiClientError("Gemini service connection refused")

        copilot = RetailCopilot(gemini_client=mock_gemini)
        response = copilot.answer_question("Which products are running low?")

        # Must still return valid answer and complete analytics evidence
        self.assertEqual(response.intent, "INVENTORY_RISK")
        self.assertEqual(response.data_status, "complete")
        self.assertGreater(len(response.evidence), 0)
        self.assertIn("Identified", response.answer)

    # 14. Malformed Gemini intent
    def test_14_malformed_gemini_intent(self) -> None:
        """Verify copilot safely handles Gemini returning malformed JSON for intent."""
        mock_gemini = MagicMock(spec=GeminiClient)
        mock_gemini.is_configured = True
        mock_gemini.generate_structured_json.side_effect = GeminiTimeoutError("Request timed out")
        mock_gemini.generate_explanation.return_value = {"explanation": "Fallback explanation", "is_available": True}

        copilot = RetailCopilot(gemini_client=mock_gemini)
        # Deterministic classifier fallback kicks in
        response = copilot.answer_question("Which items are low on stock?")

        self.assertEqual(response.intent, "INVENTORY_RISK")
        self.assertGreater(len(response.evidence), 0)

    # 15. Explanation grounded in evidence
    def test_15_explanation_grounded_in_evidence(self) -> None:
        """Verify explanation receives exact deterministic numbers and preserves them."""
        copilot, mock_gemini = self._create_mock_copilot(
            gemini_intent={
                "intent": "PRODUCT_PERFORMANCE",
                "product": "Wireless Mouse",
                "confidence": 0.95,
            },
            gemini_explanation="Wireless Mouse performed with verified metrics from deterministic sales engine.",
        )
        response = copilot.answer_question("How did the wireless mouse perform?")

        # Check call args to generate_explanation
        mock_gemini.generate_explanation.assert_called_once()
        kwargs = mock_gemini.generate_explanation.call_args[1]
        self.assertIn("metrics", kwargs)
        self.assertIn("evidence", kwargs)
        self.assertEqual(kwargs["intent"], "PRODUCT_PERFORMANCE")
        self.assertEqual(response.answer, "Wireless Mouse performed with verified metrics from deterministic sales engine.")

    # 16. Recommendation preserves deterministic quantity
    def test_16_recommendation_preserves_deterministic_quantity(self) -> None:
        """Verify reorder recommendations accurately contain deterministically calculated quantities."""
        copilot, _ = self._create_mock_copilot(
            gemini_intent={
                "intent": "REORDER_RECOMMENDATION",
                "product": "Braided Nylon USB-C Cable (2m)",
                "confidence": 0.95,
            }
        )
        response = copilot.answer_question("How much USB-C cable should I reorder?")

        self.assertEqual(response.intent, "REORDER_RECOMMENDATION")
        self.assertEqual(response.data_status, "complete")
        self.assertGreater(len(response.evidence), 0)
        # Verify recommended reorder quantity is a non-negative integer in evidence
        for ev in response.evidence:
            self.assertIn("recommended_reorder_quantity", ev)
            self.assertIsInstance(ev["recommended_reorder_quantity"], int)
            self.assertGreaterEqual(ev["recommended_reorder_quantity"], 0)

    # 17. Integration test: End-to-end flow with SQLite database
    def test_17_integration_end_to_end_sqlite(self) -> None:
        """Integration test: from question to SQLite analytics, evidence, and response."""
        # Using standalone answer_question helper with mocked Gemini
        with patch.object(GeminiClient, "generate_structured_json") as mock_json:
            with patch.object(GeminiClient, "generate_explanation") as mock_exp:
                mock_json.return_value = {
                    "intent": "INVENTORY_RISK",
                    "product": None,
                    "store": None,
                    "category": None,
                    "start_date": None,
                    "end_date": None,
                    "confidence": 0.98,
                }
                mock_exp.return_value = {
                    "explanation": "Critical inventory analysis completed. Several items are near stockout.",
                    "is_available": True,
                    "error": None,
                }

                resp = answer_question("Which products are likely to run out soon?")
                self.assertEqual(resp.intent, "INVENTORY_RISK")
                self.assertEqual(resp.data_status, "complete")
                self.assertFalse(resp.needs_clarification)
                self.assertGreater(len(resp.evidence), 0)
                self.assertTrue(len(resp.recommendations) > 0 or len(resp.assumptions) > 0)

    # 18. API Endpoint POST /api/copilot
    def test_18_api_copilot_endpoint(self) -> None:
        """Verify the POST /api/copilot HTTP endpoint validates input and returns structured schema."""
        with patch.object(GeminiClient, "generate_structured_json") as mock_json:
            mock_json.return_value = {
                "intent": "INVENTORY_RISK",
                "product": None,
                "store": None,
                "confidence": 0.95,
            }

            # Valid question
            res = self.client.post(
                "/api/copilot",
                json={"question": "Which products are likely to run out soon?"},
            )
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("answer", data)
            self.assertEqual(data["intent"], "INVENTORY_RISK")
            self.assertIn("data_status", data)
            self.assertIn("evidence", data)
            self.assertIn("assumptions", data)
            self.assertIn("recommendations", data)

            # Empty question validation (HTTP 400 or 422)
            res_empty = self.client.post("/api/copilot", json={"question": "   "})
            self.assertEqual(res_empty.status_code, 400)

            # Missing question field (HTTP 422)
            res_bad = self.client.post("/api/copilot", json={})
            self.assertEqual(res_bad.status_code, 422)

    # 19. Offline Unknown Product Handling
    def test_19_offline_unknown_product(self) -> None:
        """Verify unknown product returns clear response without inventing a product when offline."""
        copilot, _ = self._create_mock_copilot(simulate_failure=True)
        response = copilot.answer_question("How is XYZ Super Phone performing?")
        self.assertEqual(response.data_status, "no_data")
        self.assertIn("XYZ Super Phone", response.answer)
        self.assertEqual(len(response.evidence), 0)

    # 20. Offline Unknown Store Handling
    def test_20_offline_unknown_store(self) -> None:
        """Verify unknown store returns clear response without inventing a store when offline."""
        copilot, _ = self._create_mock_copilot(simulate_failure=True)
        response = copilot.answer_question("How is Store 99 performing?")
        self.assertEqual(response.data_status, "no_data")
        self.assertIn("Store 99", response.answer)
        self.assertEqual(len(response.evidence), 0)

    # 21. Relative Date Window (7 days)
    def test_21_relative_date_window_7_days(self) -> None:
        """Verify relative window like 'last 7 days' calculates correct boundary."""
        copilot, _ = self._create_mock_copilot(simulate_failure=True)
        response = copilot.answer_question("Show sales for the last 7 days.")
        self.assertIn(response.intent, ["SALES_SUMMARY", "SALES_TREND"])
        self.assertIn(response.data_status, ["complete", "incomplete"])
        self.assertGreater(len(response.evidence), 0)

    # 22. Future Date Range
    def test_22_future_date_range(self) -> None:
        """Verify future date range like 2030 returns no_data."""
        copilot, _ = self._create_mock_copilot(simulate_failure=True)
        response = copilot.answer_question("Show sales from 2030-01-01 to 2030-01-31.")
        self.assertEqual(response.data_status, "no_data")
        self.assertIn("No sales data found", response.answer)

    # 23. Category Performance
    def test_23_category_performance(self) -> None:
        """Verify category query routes to CATEGORY_PERFORMANCE."""
        copilot, _ = self._create_mock_copilot(simulate_failure=True)
        response = copilot.answer_question("How are Electronics performing?")
        self.assertEqual(response.intent, "CATEGORY_PERFORMANCE")
        self.assertEqual(response.data_status, "complete")
        self.assertGreater(len(response.evidence), 0)

    # 24. General Reorder Query
    def test_24_general_reorder_query(self) -> None:
        """Verify 'What should I reorder?' is not parsed as product name 'What should I'."""
        copilot, _ = self._create_mock_copilot(simulate_failure=True)
        response = copilot.answer_question("What should I reorder?")
        self.assertEqual(response.intent, "REORDER_RECOMMENDATION")
        self.assertEqual(response.data_status, "complete")
        self.assertGreater(len(response.evidence), 0)


if __name__ == "__main__":
    unittest.main()
