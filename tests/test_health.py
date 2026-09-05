"""Tests for root and health endpoints."""

import unittest
from fastapi.testclient import TestClient
from app import app


class TestHealthEndpoints(unittest.TestCase):
    """Test suite for core application health and root endpoints."""

    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_root_endpoint(self) -> None:
        """Test GET / returns 200 and confirms RetailIQ is running."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertIn("RetailIQ is running", data.get("message", ""))
        self.assertEqual(data.get("track"), "PS03")

    def test_health_endpoint(self) -> None:
        """Test GET /health returns 200 and status healthy."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "healthy")


if __name__ == "__main__":
    unittest.main()
