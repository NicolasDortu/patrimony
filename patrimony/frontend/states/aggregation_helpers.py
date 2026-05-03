"""Shared aggregation helpers for cash state computations."""

from ..utils import get_pie_color


def add_percentages(
    rows: list[dict], value_key: str = "value", out_key: str = "percentage"
) -> list[dict]:
    """Add a percentage field to each row based on its share of the total."""
    total = sum(r.get(value_key, 0) for r in rows) or 1.0
    for r in rows:
        r[out_key] = round(r.get(value_key, 0) / total * 100, 1)
    return rows


def aggregate_monthly_income_expense(operations: list[dict]) -> list[dict]:
    """Aggregate operations into monthly income vs expense totals."""
    monthly: dict[str, dict[str, float]] = {}
    for op in operations:
        date_str = str(op.get("operation_date", ""))[:7]
        if not date_str:
            continue
        if date_str not in monthly:
            monthly[date_str] = {"month": date_str, "income": 0.0, "expense": 0.0}
        amount = float(op.get("amount", 0))
        if amount >= 0:
            monthly[date_str]["income"] += amount
        else:
            monthly[date_str]["expense"] += abs(amount)
    return [
        {
            "month": m["month"],
            "income": round(m["income"], 2),
            "expense": round(m["expense"], 2),
        }
        for m in sorted(monthly.values(), key=lambda x: x["month"])
    ]


def aggregate_expenses_by_category(operations: list[dict]) -> list[dict]:
    """Aggregate expenses by category for pie chart."""
    categories: dict[str, float] = {}
    for op in operations:
        amount = float(op.get("amount", 0))
        if amount >= 0:
            continue
        cat = op.get("category", "Uncategorized") or "Uncategorized"
        categories[cat] = categories.get(cat, 0.0) + abs(amount)
    rows = [
        {"name": k, "value": round(v, 2), "fill": get_pie_color(i)}
        for i, (k, v) in enumerate(
            sorted(categories.items(), key=lambda x: x[1], reverse=True)
        )
    ]
    return add_percentages(rows)
