"""Tests for frontend static serving, SPA routing, and catalog endpoints."""

import re
import unittest
from fastapi.testclient import TestClient
from app import app


class TestFrontendServing(unittest.TestCase):
    """Test suite for FastAPI frontend static assets and SPA delivery."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_browser_root_serves_html(self) -> None:
        """Verify that browser requests (Accept: text/html) receive the SPA index.html."""
        res = self.client.get(
            "/",
            headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/html", res.headers.get("content-type", ""))
        self.assertIn("RetailIQ", res.text)
        self.assertIn("<div id=\"root\"></div>", res.text)

    def test_api_root_serves_status_json(self) -> None:
        """Verify that API callers and test runners receive the StatusResponse schema."""
        res = self.client.get("/", headers={"Accept": "application/json"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(data.get("app"), "RetailIQ")
        self.assertEqual(data.get("track"), "PS03")

    def test_spa_routes_serve_html(self) -> None:
        """Verify client-side routes serve the SPA index.html."""
        for route in ["/dashboard", "/sales", "/inventory", "/copilot"]:
            res = self.client.get(route, headers={"Accept": "text/html"})
            self.assertEqual(res.status_code, 200)
            self.assertIn("text/html", res.headers.get("content-type", ""))
            self.assertIn("<div id=\"root\"></div>", res.text)

    def test_catalog_endpoints(self) -> None:
        """Verify catalog endpoints return valid products and stores."""
        res_prods = self.client.get("/api/catalog/products")
        self.assertEqual(res_prods.status_code, 200)
        prods = res_prods.json()
        self.assertIsInstance(prods, list)
        self.assertEqual(len(prods), 40)
        self.assertIn("product_id", prods[0])

        res_stores = self.client.get("/api/catalog/stores")
        self.assertEqual(res_stores.status_code, 200)
        stores = res_stores.json()
        self.assertIsInstance(stores, list)
        self.assertEqual(len(stores), 4)
        self.assertIn("store_id", stores[0])


if __name__ == "__main__":
    unittest.main()
