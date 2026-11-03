"""
Tests for restocking recommendation and restock order endpoints.
"""
import re
from datetime import datetime

import pytest

import mock_data


@pytest.fixture(autouse=True)
def clear_restock_orders():
    """restock_orders is a module-level list that persists across tests in one process."""
    mock_data.restock_orders.clear()
    yield
    mock_data.restock_orders.clear()


def get_inventory_by_sku(client):
    """Helper: inventory items indexed by SKU for cross-endpoint checks."""
    return {item["sku"]: item for item in client.get("/api/inventory").json()}


class TestRestockRecommendations:
    """Test suite for GET /api/restock/recommendations."""

    def test_get_recommendations_structure(self, client):
        """Test recommendation response has items and totals with expected fields."""
        response = client.get("/api/restock/recommendations?budget=25000")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data["items"], list)
        assert len(data["items"]) > 0

        totals = data["totals"]
        for key in ["budget", "total_cost", "remaining_budget", "items_skipped"]:
            assert key in totals

        item = data["items"][0]
        for key in ["sku", "name", "category", "warehouse", "quantity_on_hand", "reorder_point",
                    "forecasted_demand", "shortfall", "recommended_quantity", "unit_cost",
                    "line_total", "priority_score", "trend", "lead_time_days"]:
            assert key in item

    def test_recommendations_respect_budget(self, client):
        """Test that total cost never exceeds the budget and totals add up."""
        budget = 25000
        data = client.get(f"/api/restock/recommendations?budget={budget}").json()

        line_sum = sum(item["line_total"] for item in data["items"])
        assert data["totals"]["total_cost"] <= budget
        assert abs(data["totals"]["total_cost"] - line_sum) < 0.01
        assert abs(data["totals"]["remaining_budget"] - (budget - line_sum)) < 0.01

    def test_recommendations_sorted_by_priority_score(self, client):
        """Test that items are returned with non-increasing priority scores."""
        data = client.get("/api/restock/recommendations?budget=100000").json()
        scores = [item["priority_score"] for item in data["items"]]
        assert scores == sorted(scores, reverse=True)

    def test_recommended_quantity_never_exceeds_shortfall(self, client):
        """Test that recommended quantity is at most the shortfall and at least one."""
        data = client.get("/api/restock/recommendations?budget=25000").json()
        for item in data["items"]:
            assert 1 <= item["recommended_quantity"] <= item["shortfall"]
            assert abs(item["line_total"] - item["recommended_quantity"] * item["unit_cost"]) < 0.01

    def test_zero_budget_returns_empty_list(self, client):
        """Test that a zero budget recommends nothing but reports skipped items."""
        data = client.get("/api/restock/recommendations?budget=0").json()
        assert data["items"] == []
        assert data["totals"]["total_cost"] == 0
        assert data["totals"]["items_skipped"] > 0

    def test_large_budget_fills_all_shortfalls(self, client):
        """Test that a large budget covers every shortfall in full."""
        data = client.get("/api/restock/recommendations?budget=100000").json()
        assert data["totals"]["items_skipped"] == 0
        for item in data["items"]:
            assert item["recommended_quantity"] == item["shortfall"]

    def test_recommendations_only_include_positive_shortfall(self, client):
        """Test that shortfall equals forecast minus stock and is positive."""
        data = client.get("/api/restock/recommendations?budget=100000").json()
        for item in data["items"]:
            assert item["shortfall"] > 0
            assert item["shortfall"] == item["forecasted_demand"] - item["quantity_on_hand"]

    def test_recommendations_filter_by_category(self, client):
        """Test filtering recommendations by category (case-insensitive)."""
        data = client.get("/api/restock/recommendations?budget=100000&category=actuators").json()
        assert len(data["items"]) > 0
        for item in data["items"]:
            assert item["category"].lower() == "actuators"

    def test_recommendations_filter_by_warehouse(self, client):
        """Test filtering recommendations by warehouse."""
        data = client.get("/api/restock/recommendations?budget=100000&warehouse=Tokyo").json()
        for item in data["items"]:
            assert item["warehouse"] == "Tokyo"

    def test_negative_budget_returns_400(self, client):
        """Test that a negative budget is rejected."""
        response = client.get("/api/restock/recommendations?budget=-1")
        assert response.status_code == 400
        assert "detail" in response.json()


class TestRestockOrders:
    """Test suite for GET/POST /api/restock-orders."""

    def test_get_restock_orders_initially_empty(self, client):
        """Test that no restock orders exist before any are placed."""
        response = client.get("/api/restock-orders")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_restock_order_and_get(self, client):
        """Test placing an order and reading it back."""
        payload = {"budget": 25000, "items": [{"sku": "TMP-201", "quantity": 10}]}
        response = client.post("/api/restock-orders", json=payload)
        assert response.status_code == 201

        order = response.json()
        assert re.fullmatch(r"RST-\d{4}-\d{4}", order["order_number"])
        assert order["status"] == "Submitted"
        assert order["budget"] == 25000
        assert len(order["items"]) == 1

        listed = client.get("/api/restock-orders").json()
        assert len(listed) == 1
        assert listed[0]["id"] == order["id"]

    def test_create_restock_order_recomputes_cost(self, client):
        """Test that line totals come from inventory unit cost, not the client."""
        inventory = get_inventory_by_sku(client)
        payload = {"budget": 5000, "items": [{"sku": "PCB-001", "quantity": 10}]}
        order = client.post("/api/restock-orders", json=payload).json()

        line = order["items"][0]
        assert line["unit_cost"] == inventory["PCB-001"]["unit_cost"]
        assert abs(line["line_total"] - 10 * inventory["PCB-001"]["unit_cost"]) < 0.01
        assert abs(order["total_cost"] - line["line_total"]) < 0.01

    def test_create_restock_order_empty_items_returns_400(self, client):
        """Test that an order without items is rejected."""
        response = client.post("/api/restock-orders", json={"budget": 1, "items": []})
        assert response.status_code == 400

    def test_create_restock_order_unknown_sku_returns_400(self, client):
        """Test that an unknown SKU is rejected."""
        payload = {"budget": 1, "items": [{"sku": "NOPE-000", "quantity": 1}]}
        response = client.post("/api/restock-orders", json=payload)
        assert response.status_code == 400
        assert "NOPE-000" in response.json()["detail"]

    def test_create_restock_order_zero_quantity_returns_400(self, client):
        """Test that a zero quantity is rejected."""
        payload = {"budget": 1, "items": [{"sku": "PCB-001", "quantity": 0}]}
        response = client.post("/api/restock-orders", json=payload)
        assert response.status_code == 400

    def test_order_lead_time_is_max_of_items(self, client):
        """Test that order lead time is the slowest item's lead time."""
        payload = {"budget": 5000, "items": [
            {"sku": "PCB-001", "quantity": 1},  # Circuit Boards: 14 days
            {"sku": "TMP-201", "quantity": 1},  # Sensors: 7 days
        ]}
        order = client.post("/api/restock-orders", json=payload).json()

        by_sku = {line["sku"]: line for line in order["items"]}
        assert by_sku["PCB-001"]["lead_time_days"] == 14
        assert by_sku["TMP-201"]["lead_time_days"] == 7
        assert order["lead_time_days"] == 14

    def test_expected_delivery_is_order_date_plus_lead_time(self, client):
        """Test that expected delivery is order date plus lead time days."""
        payload = {"budget": 5000, "items": [{"sku": "TMP-201", "quantity": 1}]}
        order = client.post("/api/restock-orders", json=payload).json()

        order_date = datetime.fromisoformat(order["order_date"])
        expected = datetime.fromisoformat(order["expected_delivery"])
        assert (expected - order_date).days == order["lead_time_days"]

    def test_order_numbers_increment(self, client):
        """Test that consecutive orders get sequential order numbers."""
        payload = {"budget": 5000, "items": [{"sku": "TMP-201", "quantity": 1}]}
        first = client.post("/api/restock-orders", json=payload).json()
        second = client.post("/api/restock-orders", json=payload).json()
        assert first["order_number"].endswith("-0001")
        assert second["order_number"].endswith("-0002")

    def test_create_order_does_not_change_inventory(self, client):
        """Test that placing an order leaves stock levels untouched."""
        before = get_inventory_by_sku(client)["TMP-201"]["quantity_on_hand"]
        client.post("/api/restock-orders", json={"budget": 5000, "items": [{"sku": "TMP-201", "quantity": 50}]})
        after = get_inventory_by_sku(client)["TMP-201"]["quantity_on_hand"]
        assert before == after
