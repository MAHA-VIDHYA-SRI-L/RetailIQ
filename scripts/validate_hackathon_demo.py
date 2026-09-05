"""Comprehensive hackathon demo validator for Prompt 10."""
import sys
import httpx
import json

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_URL = "http://localhost:8000"

def run_validation():
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)
    print("=== 1. Testing Health and Core Endpoints ===")
    
    # 1. Health
    r = client.get("/health")
    assert r.status_code == 200, f"/health failed: {r.status_code}"
    health_data = r.json()
    print("Health response:", health_data)
    assert health_data.get("app") == "RetailIQ", "App name must be RetailIQ"
    assert health_data.get("track_id") == "PS03", "Track ID must be PS03"
    assert health_data.get("status") == "healthy", "Status must be healthy"
    
    # 2. Root (HTML SPA Serving)
    r_html = client.get("/", headers={"Accept": "text/html"})
    assert r_html.status_code == 200
    assert "<!doctype html>" in r_html.text.lower() or "<html" in r_html.text.lower()
    print("Root (SPA HTML) serves successfully.")

    # 3. Analytics Endpoints
    print("\n=== 2. Testing Analytics & Inventory Endpoints ===")
    for endpoint in [
        "/api/analytics/summary",
        "/api/analytics/trend",
        "/api/analytics/top-products",
        "/api/analytics/categories",
        "/api/catalog/stores",
        "/api/catalog/products",
        "/api/inventory/health",
        "/api/inventory/risks",
        "/api/inventory/overstock",
        "/api/inventory/attention",
        "/api/inventory/velocity",
    ]:
        resp = client.get(endpoint)
        assert resp.status_code == 200, f"Endpoint {endpoint} failed with {resp.status_code}"
        data = resp.json()
        assert isinstance(data, (dict, list)), f"Invalid JSON type for {endpoint}"
        count = len(data) if isinstance(data, list) else len(data.keys())
        print(f"  [OK] {endpoint:30} -> {resp.status_code} (keys/items: {count})")

    # 4. Demo Questions for Copilot
    print("\n=== 3. Testing Real Demo Questions (Sections 6-9) ===")
    demo_questions = [
        ("Which products are likely to run out soon?", "INVENTORY_RISK", "complete"),
        ("Which store generated the most revenue?", "STORE_COMPARISON", "complete"),
        ("Which products are overstocked?", "OVERSTOCK", "complete"),
        ("Show me the sales trend.", "SALES_TREND", ["complete", "incomplete"]),
        ("What should I reorder?", "REORDER_RECOMMENDATION", "complete"),
        ("How are Electronics performing?", "CATEGORY_PERFORMANCE", "complete"),
    ]

    for q, expected_intent, expected_status in demo_questions:
        resp = client.post("/api/copilot", json={"question": q})
        assert resp.status_code == 200, f"Query '{q}' failed with {resp.status_code}"
        res = resp.json()
        print(f"\nQuestion: {q}")
        print(f"  Intent:       {res.get('intent')} (expected: {expected_intent})")
        print(f"  Data Status:  {res.get('data_status')} (expected: {expected_status})")
        print(f"  Evidence:     {len(res.get('evidence', []))} items")
        print(f"  Answer Snippet: {res.get('answer', '')[:100]}...")
        assert res.get("intent") == expected_intent or expected_intent in res.get("intent", ""), f"Intent mismatch for {q}"
        if isinstance(expected_status, list):
            assert res.get("data_status") in expected_status
        else:
            assert res.get("data_status") == expected_status
        assert len(res.get("evidence", [])) > 0, f"Evidence must not be empty for {q}"

    # 5. Ambiguous Questions (Section 7)
    print("\n=== 4. Testing Ambiguous Query (Section 7) ===")
    q_ambig = "How are the headphones doing?"
    resp_ambig = client.post("/api/copilot", json={"question": q_ambig})
    assert resp_ambig.status_code == 200
    res_ambig = resp_ambig.json()
    print(f"Question: {q_ambig}")
    print(f"  Needs Clarification: {res_ambig.get('needs_clarification')}")
    print(f"  Data Status:         {res_ambig.get('data_status')}")
    print(f"  Answer:              {res_ambig.get('answer')}")
    assert res_ambig.get("needs_clarification") is True, "Ambiguous query must require clarification"
    assert res_ambig.get("data_status") == "ambiguous"

    # 6. Unknown Entities (Section 8)
    print("\n=== 5. Testing Unknown Entities (Section 8) ===")
    q_unknown_prod = "How is the XYZ Ultra Phone performing?"
    resp_unk_p = client.post("/api/copilot", json={"question": q_unknown_prod})
    assert resp_unk_p.status_code == 200
    res_unk_p = resp_unk_p.json()
    print(f"Question: {q_unknown_prod}")
    print(f"  Data Status: {res_unk_p.get('data_status')}")
    print(f"  Answer:      {res_unk_p.get('answer')}")
    assert res_unk_p.get("data_status") == "no_data"
    assert "XYZ Ultra Phone" in res_unk_p.get("answer", "")

    q_unknown_store = "How is Store 999 performing?"
    resp_unk_s = client.post("/api/copilot", json={"question": q_unknown_store})
    assert resp_unk_s.status_code == 200
    res_unk_s = resp_unk_s.json()
    print(f"\nQuestion: {q_unknown_store}")
    print(f"  Data Status: {res_unk_s.get('data_status')}")
    print(f"  Answer:      {res_unk_s.get('answer')}")
    assert res_unk_s.get("data_status") == "no_data"
    assert "Store 999" in res_unk_s.get("answer", "")

    # 7. Insufficient Data (Section 9)
    print("\n=== 6. Testing Insufficient Data / Future Dates (Section 9) ===")
    q_future = "Show sales from January 2030."
    resp_future = client.post("/api/copilot", json={"question": q_future})
    assert resp_future.status_code == 200
    res_future = resp_future.json()
    print(f"Question: {q_future}")
    print(f"  Data Status: {res_future.get('data_status')}")
    print(f"  Answer:      {res_future.get('answer')}")
    assert res_future.get("data_status") == "no_data"
    assert "No sales data found" in res_future.get("answer", "")

    # 8. Invalid Inputs (Section 10)
    print("\n=== 7. Testing Invalid Inputs (Section 10) ===")
    r_empty = client.post("/api/copilot", json={"question": ""})
    assert r_empty.status_code in (400, 422)
    print(f"  [OK] Empty question rejected with HTTP {r_empty.status_code}")

    r_spaces = client.post("/api/copilot", json={"question": "   "})
    assert r_spaces.status_code in (400, 422)
    print(f"  [OK] Whitespace question rejected with HTTP {r_spaces.status_code}")

    r_missing = client.post("/api/copilot", json={})
    assert r_missing.status_code == 422
    print("  [OK] Missing question payload rejected with HTTP 422")

    r_null = client.post("/api/copilot", json={"question": None})
    assert r_null.status_code == 422
    print("  [OK] Null question rejected with HTTP 422")

    r_number = client.post("/api/copilot", json={"question": 12345})
    assert r_number.status_code == 422
    print("  [OK] Numeric question rejected with HTTP 422")

    print("\n=== ALL HACKATHON DEMO VALIDATIONS PASSED CLEANLY! ===")

if __name__ == "__main__":
    run_validation()
