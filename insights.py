from __future__ import annotations

from calendar import monthrange
from datetime import datetime
from typing import Any

import pandas as pd


def _round_currency(value: float) -> float:
    """Round currency values to two decimals for clean display."""
    return round(float(value), 2)


def calculate_total_monthly_spending(expenses_df: pd.DataFrame) -> float:
    """Calculate the total spending amount for the provided expense data."""
    if expenses_df.empty:
        return 0.0
    return _round_currency(expenses_df["amount"].sum())


def calculate_category_spending(expenses_df: pd.DataFrame) -> list[dict[str, Any]]:
    """Return category-wise spending with amount and percentage contribution."""
    if expenses_df.empty:
        return []

    total_spent = float(expenses_df["amount"].sum())
    category_totals = (
        expenses_df.groupby("category")["amount"].sum().sort_values(ascending=False).reset_index()
    )

    results: list[dict[str, Any]] = []
    for row in category_totals.itertuples(index=False):
        percentage = (float(row.amount) / total_spent * 100) if total_spent else 0.0
        results.append(
            {
                "category": row.category,
                "amount": _round_currency(row.amount),
                "percentage": round(percentage, 2),
            }
        )
    return results


def identify_top_category(category_spending: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the highest spending category entry."""
    if not category_spending:
        return None
    return category_spending[0]


def detect_high_spending_days(expenses_df: pd.DataFrame) -> list[str]:
    """Find dates where spending is more than 1.5 times the average daily spend."""
    if expenses_df.empty:
        return []

    daily_spend = (
        expenses_df.assign(expense_day=pd.to_datetime(expenses_df["date"]).dt.date)
        .groupby("expense_day")["amount"]
        .sum()
        .sort_index()
    )

    if daily_spend.empty:
        return []

    average_daily_spending = float(daily_spend.mean())
    threshold = average_daily_spending * 1.5
    high_days: list[str] = []

    for spend_day, amount in daily_spend.items():
        if float(amount) > threshold:
            high_days.append(
                f"📅 {spend_day} was a high-spending day at ₹{_round_currency(amount):,.2f}, which is above your usual daily pattern."
            )
    return high_days


def estimate_end_of_month_spending(expenses_df: pd.DataFrame) -> str:
    """Estimate month-end spending using average daily spending in the current dataset month."""
    if expenses_df.empty:
        return "🔮 Add a few expenses to see an end-of-month spending prediction."

    expense_dates = pd.to_datetime(expenses_df["date"])
    latest_date = expense_dates.max()
    total_spent = float(expenses_df["amount"].sum())

    current_day = int(latest_date.day)
    total_days_in_month = monthrange(int(latest_date.year), int(latest_date.month))[1]
    average_daily_spending = total_spent / current_day if current_day else 0.0
    predicted_total = _round_currency(average_daily_spending * total_days_in_month)

    month_name = datetime(int(latest_date.year), int(latest_date.month), 1).strftime("%B")
    return (
        f"🔮 Based on your current spending pattern, you may spend ₹{predicted_total:,.2f} "
        f"by the end of {month_name}."
    )


def generate_human_insights(
    total_spent: float,
    category_spending: list[dict[str, Any]],
    budget_amount: float | None,
    high_spending_days: list[str],
) -> tuple[list[str], list[str]]:
    """Generate friendly insights and budget warnings for direct UI display."""
    insights: list[str] = []
    warnings: list[str] = []

    top_category = identify_top_category(category_spending)
    budget = float(budget_amount or 0.0)

    if top_category:
        top_name = str(top_category["category"])
        top_amount = float(top_category["amount"])
        top_percentage = float(top_category["percentage"])
        lower_savings = _round_currency(top_amount * 0.10)
        upper_savings = _round_currency(top_amount * 0.20)

        insights.append(
            f"📊 Your biggest spending area is {top_name}, which accounts for {top_percentage:.2f}% of your total spending."
        )
        if top_percentage > 30:
            warnings.append(f"⚠️ You are spending too much on {top_name} ({top_percentage:.2f}%).")
        insights.append(
            f"💡 Cutting {top_name} expenses by 10-20% can save ₹{lower_savings:,.2f}-₹{upper_savings:,.2f} per month."
        )

    if budget > 0:
        usage_percentage = round((total_spent / budget) * 100, 2) if budget else 0.0
        if total_spent > budget:
            warnings.append("🚨 You have exceeded your budget!")
        elif usage_percentage > 80:
            warnings.append("⚠️ You have used more than 80% of your budget.")
        else:
            insights.append(
                f"✅ You have used {usage_percentage:.2f}% of your budget, so your spending is still under control."
            )
    else:
        insights.append("📝 Set a monthly budget to unlock smarter budget warnings and tracking.")

    insights.extend(high_spending_days)
    return insights, warnings


def analyze_finances(expenses_df: pd.DataFrame, budget_amount: float | None) -> dict[str, Any]:
    """Return structured, human-friendly financial analysis for Streamlit display."""
    if expenses_df.empty:
        return {
            "summary": {
                "total_spent": 0.0,
                "top_category": "N/A",
                "percentage": 0.0,
            },
            "insights": ["📝 Add a few expenses to start receiving smart financial insights."],
            "warnings": [],
            "prediction": "🔮 Add a few expenses to see an end-of-month spending prediction.",
        }

    total_spent = calculate_total_monthly_spending(expenses_df)
    category_spending = calculate_category_spending(expenses_df)
    top_category = identify_top_category(category_spending)
    high_spending_days = detect_high_spending_days(expenses_df)
    insights, warnings = generate_human_insights(
        total_spent=total_spent,
        category_spending=category_spending,
        budget_amount=budget_amount,
        high_spending_days=high_spending_days,
    )

    return {
        "summary": {
            "total_spent": total_spent,
            "top_category": top_category["category"] if top_category else "N/A",
            "percentage": float(top_category["percentage"]) if top_category else 0.0,
        },
        "insights": insights,
        "warnings": warnings,
        "prediction": estimate_end_of_month_spending(expenses_df),
    }
