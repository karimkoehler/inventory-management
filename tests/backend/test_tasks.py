"""
Tests for task endpoints.
"""
import pytest

import mock_data


@pytest.fixture(autouse=True)
def clear_tasks():
    """tasks is a module-level list that persists across tests in one process."""
    mock_data.tasks.clear()
    yield
    mock_data.tasks.clear()


def create_task(client, title="Review Q4 stock", priority="high", due_date="2025-12-01"):
    response = client.post("/api/tasks", json={"title": title, "priority": priority, "dueDate": due_date})
    assert response.status_code == 201
    return response.json()


class TestTaskEndpoints:
    """Test suite for task endpoints."""

    def test_get_tasks_initially_empty(self, client):
        """Test that no tasks exist before any are created."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_task(self, client):
        """Test creating a task."""
        task = create_task(client, title="  Review Q4 stock  ")
        assert task == {
            "id": "task-1",
            "title": "Review Q4 stock",
            "priority": "high",
            "dueDate": "2025-12-01",
            "status": "pending",
        }

    def test_task_ids_do_not_collide_with_demo_tasks(self, client):
        """Test that API task IDs are strings, unlike the client's integer demo task IDs."""
        first = create_task(client)
        second = create_task(client)
        assert first["id"] != second["id"]
        assert all(isinstance(t["id"], str) and t["id"].startswith("task-") for t in (first, second))

    def test_get_tasks_newest_first(self, client):
        """Test that tasks are listed newest first."""
        create_task(client, title="First")
        create_task(client, title="Second")

        titles = [t["title"] for t in client.get("/api/tasks").json()]
        assert titles == ["Second", "First"]

    def test_toggle_task(self, client):
        """Test toggling a task between pending and completed."""
        task_id = create_task(client)["id"]

        response = client.patch(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "completed"

        response = client.patch(f"/api/tasks/{task_id}")
        assert response.json()["status"] == "pending"

    def test_delete_task(self, client):
        """Test deleting a task."""
        task_id = create_task(client)["id"]

        response = client.delete(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        assert client.get("/api/tasks").json() == []

    def test_id_not_reused_after_delete(self, client):
        """Test that deleting a task does not cause the next task to reuse a live ID."""
        create_task(client)
        second = create_task(client)
        client.delete("/api/tasks/task-1")

        third = create_task(client)
        assert third["id"] != second["id"]

    @pytest.mark.parametrize("method", ["patch", "delete"])
    def test_nonexistent_task(self, client, method):
        """Test toggling or deleting a task that doesn't exist."""
        response = getattr(client, method)("/api/tasks/nonexistent-999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.parametrize("payload", [
        {"title": "", "priority": "high", "dueDate": "2025-12-01"},
        {"title": "Task", "priority": "urgent", "dueDate": "2025-12-01"},
        {"title": "Task", "priority": "high", "dueDate": "tomorrow"},
    ])
    def test_create_task_invalid_input(self, client, payload):
        """Test that invalid task fields are rejected."""
        response = client.post("/api/tasks", json=payload)
        assert response.status_code == 422
