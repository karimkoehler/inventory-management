"""
Tests for report endpoints.
"""
import pytest

import mock_data


ENDPOINTS = ["/api/reports/quarterly", "/api/reports/monthly-trends"]


def quarter_of(order_date):
    month = int(order_date[5:7])
    return f"Q{(month - 1) // 3 + 1}-{order_date[:4]}"


class TestReportEndpoints:
    """Test suite for quarterly and monthly report endpoints."""

    def test_get_quarterly_reports(self, client):
        """Test quarterly report structure and types."""
        response = client.get("/api/reports/quarterly")
        assert response.status_code == 200

        data = response.json()
        assert [q["quarter"] for q in data] == ["Q1-2025", "Q2-2025", "Q3-2025", "Q4-2025"]
        for q in data:
            assert isinstance(q["total_orders"], int)
            assert isinstance(q["delivered_orders"], int)
            assert isinstance(q["total_revenue"], (int, float))
            assert 0 <= q["fulfillment_rate"] <= 100
            assert abs(q["avg_order_value"] - q["total_revenue"] / q["total_orders"]) < 0.01

    def test_get_monthly_trends(self, client):
        """Test monthly trend structure, ordering and rounding."""
        response = client.get("/api/reports/monthly-trends")
        assert response.status_code == 200

        data = response.json()
        months = [m["month"] for m in data]
        assert months == sorted(months)
        assert len(months) == 12
        for m in data:
            assert isinstance(m["order_count"], int)
            assert round(m["revenue"], 2) == m["revenue"]

    def test_quarterly_matches_orders(self, client):
        """Test that quarterly totals match the raw orders endpoint."""
        all_orders = client.get("/api/orders").json()
        quarterly = client.get("/api/reports/quarterly").json()

        assert sum(q["total_orders"] for q in quarterly) == len(all_orders)
        for q in quarterly:
            in_quarter = [o for o in all_orders if quarter_of(o["order_date"]) == q["quarter"]]
            assert q["total_orders"] == len(in_quarter)
            assert abs(q["total_revenue"] - sum(o["total_value"] for o in in_quarter)) < 0.01
            assert q["delivered_orders"] == sum(1 for o in in_quarter if o["status"].lower() == "delivered")

    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    @pytest.mark.parametrize("query", [
        "warehouse=Tokyo",
        "category=Sensors",
        "status=Delivered",
        "month=2025-03",
        "month=Q2-2025",
        "warehouse=London&category=Actuators&status=Shipped",
    ])
    def test_reports_respect_filters(self, client, endpoint, query):
        """Test that report totals match /api/orders for the same filters."""
        filtered_orders = client.get(f"/api/orders?{query}").json()
        data = client.get(f"{endpoint}?{query}").json()

        count_key = "total_orders" if "quarterly" in endpoint else "order_count"
        revenue_key = "total_revenue" if "quarterly" in endpoint else "revenue"
        assert sum(row[count_key] for row in data) == len(filtered_orders)
        assert abs(sum(row[revenue_key] for row in data) - sum(o["total_value"] for o in filtered_orders)) < 0.05

    def test_month_filter_limits_rows(self, client):
        """Test that a month filter returns only that month and its quarter."""
        assert [m["month"] for m in client.get("/api/reports/monthly-trends?month=2025-03").json()] == ["2025-03"]
        assert [q["quarter"] for q in client.get("/api/reports/quarterly?month=2025-03").json()] == ["Q1-2025"]

    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    def test_reports_all_filter_values_ignored(self, client, endpoint):
        """Test that 'all' filter values return the unfiltered report."""
        unfiltered = client.get(endpoint).json()
        assert client.get(f"{endpoint}?warehouse=all&category=all&status=all&month=all").json() == unfiltered

    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    def test_reports_no_matching_orders(self, client, endpoint):
        """Test that filters matching nothing return an empty list."""
        response = client.get(f"{endpoint}?warehouse=Nowhere")
        assert response.status_code == 200
        assert response.json() == []

    def test_quarterly_includes_other_years(self, client, monkeypatch):
        """Test that orders outside 2025 are not dropped and sort chronologically."""
        extra = dict(mock_data.orders[0], id="extra", order_date="2024-11-15T09:00:00")
        monkeypatch.setattr("main.orders", mock_data.orders + [extra])

        quarters = [q["quarter"] for q in client.get("/api/reports/quarterly").json()]
        assert quarters[0] == "Q4-2024"
        assert quarters[1:] == ["Q1-2025", "Q2-2025", "Q3-2025", "Q4-2025"]
