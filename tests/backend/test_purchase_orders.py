"""
Tests for purchase order endpoints.
"""
from datetime import date, timedelta

import pytest

import mock_data


@pytest.fixture(autouse=True)
def clear_purchase_orders():
    """purchase_orders is a module-level list that persists across tests in one process."""
    mock_data.purchase_orders.clear()
    yield
    mock_data.purchase_orders.clear()


def make_po_payload(backlog_item_id="1", **overrides):
    payload = {
        "backlog_item_id": backlog_item_id,
        "supplier_name": "Acme Components",
        "quantity": 350,
        "unit_cost": 12.5,
        "expected_delivery_date": (date.today() + timedelta(days=14)).isoformat(),
        "notes": "Expedite if possible",
    }
    payload.update(overrides)
    return payload


class TestPurchaseOrderEndpoints:
    """Test suite for purchase order endpoints."""

    def test_create_purchase_order(self, client):
        """Test creating a purchase order for a backlog item."""
        payload = make_po_payload()
        response = client.post("/api/purchase-orders", json=payload)
        assert response.status_code == 201

        po = response.json()
        assert po["id"] == "PO-0001"
        assert po["backlog_item_id"] == "1"
        assert po["supplier_name"] == "Acme Components"
        assert po["quantity"] == 350
        assert abs(po["unit_cost"] - 12.5) < 0.01
        assert po["expected_delivery_date"] == payload["expected_delivery_date"]
        assert po["status"] == "Pending"
        assert "T" in po["created_date"]
        assert po["notes"] == "Expedite if possible"

    def test_get_purchase_order_by_backlog_item(self, client):
        """Test fetching a created purchase order by its backlog item ID."""
        created = client.post("/api/purchase-orders", json=make_po_payload("2")).json()

        response = client.get("/api/purchase-orders/2")
        assert response.status_code == 200
        assert response.json() == created

    def test_get_nonexistent_purchase_order(self, client):
        """Test fetching a purchase order for a backlog item without one."""
        response = client.get("/api/purchase-orders/1")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_backlog_reflects_purchase_order(self, client):
        """Test that GET /api/backlog flags items that have a purchase order."""
        client.post("/api/purchase-orders", json=make_po_payload("3"))

        backlog = {item["id"]: item for item in client.get("/api/backlog").json()}
        assert backlog["3"]["has_purchase_order"] is True
        assert backlog["1"]["has_purchase_order"] is False

    def test_create_duplicate_purchase_order(self, client):
        """Test that a second purchase order for the same backlog item is rejected."""
        assert client.post("/api/purchase-orders", json=make_po_payload()).status_code == 201

        response = client.post("/api/purchase-orders", json=make_po_payload())
        assert response.status_code == 409
        assert len(mock_data.purchase_orders) == 1

    def test_create_purchase_order_unknown_backlog_item(self, client):
        """Test creating a purchase order for a backlog item that doesn't exist."""
        response = client.post("/api/purchase-orders", json=make_po_payload("nonexistent-999"))
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_purchase_order_past_delivery_date(self, client):
        """Test that a delivery date in the past is rejected."""
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        response = client.post("/api/purchase-orders", json=make_po_payload(expected_delivery_date=yesterday))
        assert response.status_code == 400
        assert mock_data.purchase_orders == []

    @pytest.mark.parametrize("overrides", [
        {"quantity": 0},
        {"unit_cost": 0},
        {"supplier_name": ""},
        {"expected_delivery_date": "not-a-date"},
    ])
    def test_create_purchase_order_invalid_input(self, client, overrides):
        """Test that invalid purchase order fields are rejected."""
        response = client.post("/api/purchase-orders", json=make_po_payload(**overrides))
        assert response.status_code == 422
        assert mock_data.purchase_orders == []
