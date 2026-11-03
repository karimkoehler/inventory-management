from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from datetime import date, datetime, timedelta
from mock_data import inventory_items, orders, demand_forecasts, backlog_items, spending_summary, monthly_spending, category_spending, recent_transactions, purchase_orders, restock_orders, tasks

app = FastAPI(title="Factory Inventory Management System")

# Quarter mapping for date filtering
QUARTER_MAP = {
    'Q1-2025': ['2025-01', '2025-02', '2025-03'],
    'Q2-2025': ['2025-04', '2025-05', '2025-06'],
    'Q3-2025': ['2025-07', '2025-08', '2025-09'],
    'Q4-2025': ['2025-10', '2025-11', '2025-12']
}

# Supplier lead time in days per inventory category. A restock order's lead time
# is the maximum over its items, since the order is only complete when the
# slowest line arrives.
CATEGORY_LEAD_TIME_DAYS = {
    "Circuit Boards": 14,
    "Sensors": 7,
    "Actuators": 10,
    "Controllers": 12,
    "Power Supplies": 9,
}
DEFAULT_LEAD_TIME_DAYS = 10

# Restock priority score weights (max total 100). Stock risk dominates: an item
# already at or below its reorder point outranks any trend or shortfall signal.
PRIORITY_BELOW_REORDER = 50
PRIORITY_TREND = {"increasing": 30, "stable": 15, "decreasing": 0}
PRIORITY_SHORTFALL_MAX = 20

def filter_by_month(items: list, month: Optional[str]) -> list:
    """Filter items by month/quarter based on order_date field"""
    if not month or month == 'all':
        return items

    if month.startswith('Q'):
        # Handle quarters
        if month in QUARTER_MAP:
            months = QUARTER_MAP[month]
            return [item for item in items if any(m in item.get('order_date', '') for m in months)]
    else:
        # Direct month match
        return [item for item in items if month in item.get('order_date', '')]

    return items

def apply_filters(items: list, warehouse: Optional[str] = None, category: Optional[str] = None,
                 status: Optional[str] = None) -> list:
    """Apply common filters to a list of items"""
    filtered = items

    if warehouse and warehouse != 'all':
        filtered = [item for item in filtered if item.get('warehouse') == warehouse]

    if category and category != 'all':
        filtered = [item for item in filtered if item.get('category', '').lower() == category.lower()]

    if status and status != 'all':
        filtered = [item for item in filtered if item.get('status', '').lower() == status.lower()]

    return filtered

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class InventoryItem(BaseModel):
    id: str
    sku: str
    name: str
    category: str
    warehouse: str
    quantity_on_hand: int
    reorder_point: int
    unit_cost: float
    location: str
    last_updated: str

class Order(BaseModel):
    id: str
    order_number: str
    customer: str
    items: List[dict]
    status: str
    order_date: str
    expected_delivery: str
    total_value: float
    actual_delivery: Optional[str] = None
    warehouse: Optional[str] = None
    category: Optional[str] = None

class DemandForecast(BaseModel):
    id: str
    item_sku: str
    item_name: str
    current_demand: int
    forecasted_demand: int
    trend: str
    period: str

class BacklogItem(BaseModel):
    id: str
    order_id: str
    item_sku: str
    item_name: str
    quantity_needed: int
    quantity_available: int
    days_delayed: int
    priority: str
    has_purchase_order: Optional[bool] = False

class PurchaseOrder(BaseModel):
    id: str
    backlog_item_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    expected_delivery_date: str
    status: str
    created_date: str
    notes: Optional[str] = None

class CreatePurchaseOrderRequest(BaseModel):
    backlog_item_id: str
    supplier_name: str = Field(min_length=1)
    quantity: int = Field(ge=1)
    unit_cost: float = Field(gt=0)
    # Parsed as a date so malformed values are rejected with 422; stored back as "YYYY-MM-DD"
    expected_delivery_date: date
    notes: Optional[str] = None

class Task(BaseModel):
    id: str
    title: str
    priority: Literal["high", "medium", "low"]
    dueDate: str
    status: Literal["pending", "completed"]

class CreateTaskRequest(BaseModel):
    # Field names mirror what TasksModal.vue sends (camelCase dueDate)
    title: str = Field(min_length=1)
    priority: Literal["high", "medium", "low"] = "medium"
    dueDate: date

class RestockRecommendationItem(BaseModel):
    sku: str
    name: str
    category: str
    warehouse: str
    quantity_on_hand: int
    reorder_point: int
    forecasted_demand: int
    shortfall: int
    recommended_quantity: int
    unit_cost: float
    line_total: float
    priority_score: float
    trend: str
    lead_time_days: int

class RestockRecommendationTotals(BaseModel):
    budget: float
    total_cost: float
    remaining_budget: float
    items_skipped: int

class RestockRecommendationResponse(BaseModel):
    items: List[RestockRecommendationItem]
    totals: RestockRecommendationTotals

class RestockOrderItemRequest(BaseModel):
    sku: str
    quantity: int

class CreateRestockOrderRequest(BaseModel):
    budget: float
    items: List[RestockOrderItemRequest]

class RestockOrderItem(BaseModel):
    sku: str
    name: str
    category: str
    quantity: int
    unit_cost: float
    line_total: float
    lead_time_days: int

class RestockOrder(BaseModel):
    id: str
    order_number: str
    status: str
    order_date: str
    lead_time_days: int
    expected_delivery: str
    total_cost: float
    budget: float
    items: List[RestockOrderItem]

# Restocking helpers

def get_lead_time_days(category: str) -> int:
    return CATEGORY_LEAD_TIME_DAYS.get(category, DEFAULT_LEAD_TIME_DAYS)

def calculate_priority_score(item: dict, forecast: dict, shortfall: int) -> float:
    """0-100 score: below reorder point (50) + trend (0/15/30) + relative shortfall (0-20)."""
    below_reorder = PRIORITY_BELOW_REORDER if item["quantity_on_hand"] <= item["reorder_point"] else 0
    trend = PRIORITY_TREND.get(forecast.get("trend", "").lower(), 0)
    forecasted = forecast["forecasted_demand"]
    # Shortfall is scored relative to demand so a 50-unit gap on a 60-unit forecast
    # counts more than a 50-unit gap on a 900-unit forecast.
    ratio = shortfall / forecasted if forecasted > 0 else 0
    shortfall_component = min(PRIORITY_SHORTFALL_MAX, PRIORITY_SHORTFALL_MAX * ratio)
    return round(below_reorder + trend + shortfall_component, 1)

def build_restock_candidates(warehouse: Optional[str] = None, category: Optional[str] = None) -> list:
    """Join demand forecasts to inventory by SKU and keep only items with a positive shortfall."""
    inventory = apply_filters(inventory_items, warehouse, category)
    by_sku = {item["sku"]: item for item in inventory}
    candidates = []
    for forecast in demand_forecasts:
        item = by_sku.get(forecast["item_sku"])
        if not item:
            continue
        shortfall = max(0, forecast["forecasted_demand"] - item["quantity_on_hand"])
        if shortfall == 0:
            continue
        candidates.append({
            "sku": item["sku"],
            "name": item["name"],
            "category": item["category"],
            "warehouse": item["warehouse"],
            "quantity_on_hand": item["quantity_on_hand"],
            "reorder_point": item["reorder_point"],
            "forecasted_demand": forecast["forecasted_demand"],
            "shortfall": shortfall,
            "unit_cost": item["unit_cost"],
            "trend": forecast["trend"],
            "priority_score": calculate_priority_score(item, forecast, shortfall),
            "lead_time_days": get_lead_time_days(item["category"]),
        })
    # Deterministic order: highest priority first, larger shortfall breaks ties, then SKU
    candidates.sort(key=lambda c: (-c["priority_score"], -c["shortfall"], c["sku"]))
    return candidates

def greedy_fill(candidates: list, budget: float):
    """Walk candidates in priority order and spend the budget until it runs out."""
    remaining = round(budget, 2)
    selected = []
    skipped = 0
    for candidate in candidates:
        full_cost = candidate["shortfall"] * candidate["unit_cost"]
        if full_cost <= remaining:
            quantity = candidate["shortfall"]
        else:
            # Partial fill: buy as many units as the remaining budget allows
            quantity = int(remaining // candidate["unit_cost"])
        if quantity < 1:
            # Do not stop here: a cheaper item further down the list may still fit
            skipped += 1
            continue
        line_total = round(quantity * candidate["unit_cost"], 2)
        selected.append({**candidate, "recommended_quantity": quantity, "line_total": line_total})
        remaining = round(remaining - line_total, 2)
    totals = {
        "budget": budget,
        "total_cost": round(budget - remaining, 2),
        "remaining_budget": remaining,
        "items_skipped": skipped,
    }
    return selected, totals

# API endpoints
@app.get("/")
def root():
    return {"message": "Factory Inventory Management System API", "version": "1.0.0"}

@app.get("/api/inventory", response_model=List[InventoryItem])
def get_inventory(
    warehouse: Optional[str] = None,
    category: Optional[str] = None
):
    """Get all inventory items with optional filtering"""
    return apply_filters(inventory_items, warehouse, category)

@app.get("/api/inventory/{item_id}", response_model=InventoryItem)
def get_inventory_item(item_id: str):
    """Get a specific inventory item"""
    item = next((item for item in inventory_items if item["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.get("/api/orders", response_model=List[Order])
def get_orders(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get all orders with optional filtering"""
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)
    return filtered_orders

@app.get("/api/orders/{order_id}", response_model=Order)
def get_order(order_id: str):
    """Get a specific order"""
    order = next((order for order in orders if order["id"] == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.get("/api/demand", response_model=List[DemandForecast])
def get_demand_forecasts():
    """Get demand forecasts"""
    return demand_forecasts

@app.get("/api/backlog", response_model=List[BacklogItem])
def get_backlog():
    """Get backlog items with purchase order status"""
    # Add has_purchase_order flag to each backlog item
    result = []
    for item in backlog_items:
        item_dict = dict(item)
        # Check if this backlog item has a purchase order
        has_po = any(po["backlog_item_id"] == item["id"] for po in purchase_orders)
        item_dict["has_purchase_order"] = has_po
        result.append(item_dict)
    return result

@app.post("/api/purchase-orders", response_model=PurchaseOrder, status_code=201)
def create_purchase_order(request: CreatePurchaseOrderRequest):
    """Create a purchase order for a backlog item (at most one PO per item)"""
    if not any(item["id"] == request.backlog_item_id for item in backlog_items):
        raise HTTPException(status_code=404, detail="Backlog item not found")
    if any(po["backlog_item_id"] == request.backlog_item_id for po in purchase_orders):
        raise HTTPException(status_code=409, detail="A purchase order already exists for this backlog item")
    # Mirrors the modal's client-side rule; today itself is allowed
    if request.expected_delivery_date < date.today():
        raise HTTPException(status_code=400, detail="expected_delivery_date cannot be in the past")

    purchase_order = {
        "id": f"PO-{len(purchase_orders) + 1:04d}",
        "backlog_item_id": request.backlog_item_id,
        "supplier_name": request.supplier_name.strip(),
        "quantity": request.quantity,
        "unit_cost": request.unit_cost,
        "expected_delivery_date": request.expected_delivery_date.isoformat(),
        "status": "Pending",
        "created_date": datetime.now().replace(microsecond=0).isoformat(),
        "notes": request.notes,
    }
    # Append in place so GET /api/backlog's has_purchase_order flag sees it and tests can reset it
    purchase_orders.append(purchase_order)
    return purchase_order

@app.get("/api/purchase-orders/{backlog_item_id}", response_model=PurchaseOrder)
def get_purchase_order_by_backlog_item(backlog_item_id: str):
    """Get the purchase order for a backlog item"""
    purchase_order = next((po for po in purchase_orders if po["backlog_item_id"] == backlog_item_id), None)
    if not purchase_order:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return purchase_order

@app.get("/api/tasks", response_model=List[Task])
def get_tasks():
    """Get all user-created tasks, newest first"""
    return list(reversed(tasks))

@app.post("/api/tasks", response_model=Task, status_code=201)
def create_task(request: CreateTaskRequest):
    """Create a task"""
    # IDs are prefixed strings because the client merges these with its seeded demo
    # tasks, which use plain integer IDs; a bare counter would collide with them.
    next_number = max((int(t["id"].split("-")[1]) for t in tasks), default=0) + 1
    task = {
        "id": f"task-{next_number}",
        "title": request.title.strip(),
        "priority": request.priority,
        "dueDate": request.dueDate.isoformat(),
        "status": "pending",
    }
    tasks.append(task)
    return task

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: str):
    """Delete a task"""
    index = next((i for i, t in enumerate(tasks) if t["id"] == task_id), None)
    if index is None:
        raise HTTPException(status_code=404, detail="Task not found")
    tasks.pop(index)
    return {"deleted": task_id}

@app.patch("/api/tasks/{task_id}", response_model=Task)
def toggle_task(task_id: str):
    """Toggle a task between pending and completed"""
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task["status"] = "completed" if task["status"] == "pending" else "pending"
    return task

@app.get("/api/restock/recommendations", response_model=RestockRecommendationResponse)
def get_restock_recommendations(
    budget: float = 25000,
    warehouse: Optional[str] = None,
    category: Optional[str] = None
):
    """Recommend which forecast items to restock within a budget"""
    if budget < 0:
        raise HTTPException(status_code=400, detail="budget must be >= 0")
    candidates = build_restock_candidates(warehouse, category)
    items, totals = greedy_fill(candidates, budget)
    return {"items": items, "totals": totals}

@app.get("/api/restock-orders", response_model=List[RestockOrder])
def get_restock_orders():
    """Get all submitted restock orders"""
    return restock_orders

@app.post("/api/restock-orders", response_model=RestockOrder, status_code=201)
def create_restock_order(request: CreateRestockOrderRequest):
    """Submit a restock order. Costs are recomputed from inventory, never trusted from the client."""
    if not request.items:
        raise HTTPException(status_code=400, detail="Order must contain at least one item")

    by_sku = {item["sku"]: item for item in inventory_items}
    order_items = []
    for requested in request.items:
        item = by_sku.get(requested.sku)
        if not item:
            raise HTTPException(status_code=400, detail=f"Unknown sku: {requested.sku}")
        if requested.quantity < 1:
            raise HTTPException(status_code=400, detail=f"Quantity must be >= 1 for {requested.sku}")
        order_items.append({
            "sku": item["sku"],
            "name": item["name"],
            "category": item["category"],
            "quantity": requested.quantity,
            "unit_cost": item["unit_cost"],
            "line_total": round(requested.quantity * item["unit_cost"], 2),
            "lead_time_days": get_lead_time_days(item["category"]),
        })

    lead_time_days = max(entry["lead_time_days"] for entry in order_items)
    order_date = datetime.now().replace(microsecond=0)
    sequence = len(restock_orders) + 1
    order = {
        "id": str(sequence),
        "order_number": f"RST-{order_date.year}-{sequence:04d}",
        "status": "Submitted",
        "order_date": order_date.isoformat(),
        "lead_time_days": lead_time_days,
        "expected_delivery": (order_date + timedelta(days=lead_time_days)).isoformat(),
        "total_cost": round(sum(entry["line_total"] for entry in order_items), 2),
        "budget": request.budget,
        "items": order_items,
    }
    # Append in place so tests can reset the list through the mock_data module.
    # Inventory is deliberately not decremented: demo stock stays stable, so the
    # recommendations do not change after an order is placed.
    restock_orders.append(order)
    return order

@app.get("/api/dashboard/summary")
def get_dashboard_summary(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get summary statistics for dashboard with optional filtering"""
    # Filter inventory
    filtered_inventory = apply_filters(inventory_items, warehouse, category)

    # Filter orders
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)

    total_inventory_value = sum(item["quantity_on_hand"] * item["unit_cost"] for item in filtered_inventory)
    low_stock_items = len([item for item in filtered_inventory if item["quantity_on_hand"] <= item["reorder_point"]])
    pending_orders = len([order for order in filtered_orders if order["status"] in ["Processing", "Backordered"]])
    total_backlog_items = len(backlog_items)

    return {
        "total_inventory_value": round(total_inventory_value, 2),
        "low_stock_items": low_stock_items,
        "pending_orders": pending_orders,
        "total_backlog_items": total_backlog_items,
        "total_orders_value": sum(order["total_value"] for order in filtered_orders)
    }

@app.get("/api/spending/summary")
def get_spending_summary():
    """Get spending summary statistics"""
    return spending_summary

@app.get("/api/spending/monthly")
def get_monthly_spending():
    """Get monthly spending breakdown"""
    return monthly_spending

@app.get("/api/spending/categories")
def get_category_spending():
    """Get spending by category"""
    return category_spending

@app.get("/api/spending/transactions")
def get_recent_transactions():
    """Get recent transactions"""
    return recent_transactions

class QuarterlyReport(BaseModel):
    quarter: str
    total_orders: int
    total_revenue: float
    delivered_orders: int
    avg_order_value: float
    fulfillment_rate: float

class MonthlyTrend(BaseModel):
    month: str
    order_count: int
    revenue: float
    delivered_count: int

def get_report_orders(warehouse, category, status, month) -> list:
    """Orders matching the global filter bar, shared by both report endpoints"""
    filtered = apply_filters(orders, warehouse, category, status)
    return filter_by_month(filtered, month)

def is_delivered(order: dict) -> bool:
    # Case-insensitive to match apply_filters' status comparison
    return order.get('status', '').lower() == 'delivered'

@app.get("/api/reports/quarterly", response_model=List[QuarterlyReport])
def get_quarterly_reports(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get quarterly performance reports, optionally filtered like /api/orders"""
    quarters = {}

    for order in get_report_orders(warehouse, category, status, month):
        order_date = order.get('order_date', '')
        try:
            parsed = datetime.fromisoformat(order_date)
        except ValueError:
            continue
        # Derived from the date rather than a hardcoded 2025 month list, so other years aren't dropped
        quarter = f"Q{(parsed.month - 1) // 3 + 1}-{parsed.year}"

        data = quarters.setdefault(quarter, {
            'quarter': quarter,
            'total_orders': 0,
            'total_revenue': 0,
            'delivered_orders': 0,
        })
        data['total_orders'] += 1
        data['total_revenue'] += order.get('total_value', 0)
        if is_delivered(order):
            data['delivered_orders'] += 1

    result = []
    for data in quarters.values():
        data['total_revenue'] = round(data['total_revenue'], 2)
        data['avg_order_value'] = round(data['total_revenue'] / data['total_orders'], 2)
        data['fulfillment_rate'] = round(data['delivered_orders'] / data['total_orders'] * 100, 1)
        result.append(data)

    # "Q<n>-<year>" doesn't sort chronologically as a string across years, so sort by (year, quarter)
    result.sort(key=lambda x: (x['quarter'].split('-')[1], x['quarter']))
    return result

@app.get("/api/reports/monthly-trends", response_model=List[MonthlyTrend])
def get_monthly_trends(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get month-over-month trends, optionally filtered like /api/orders"""
    months = {}

    for order in get_report_orders(warehouse, category, status, month):
        order_date = order.get('order_date', '')
        if len(order_date) < 7:
            continue
        key = order_date[:7]  # YYYY-MM

        data = months.setdefault(key, {
            'month': key,
            'order_count': 0,
            'revenue': 0,
            'delivered_count': 0,
        })
        data['order_count'] += 1
        data['revenue'] += order.get('total_value', 0)
        if is_delivered(order):
            data['delivered_count'] += 1

    result = sorted(months.values(), key=lambda x: x['month'])
    for data in result:
        # Summing floats leaves noise like 818446.6500000001
        data['revenue'] = round(data['revenue'], 2)
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
