from __future__ import annotations

from typing import Dict

import matplotlib.pyplot as plt
import pandas as pd


def calculate_summary(expenses_df: pd.DataFrame, budget_amount: float | None) -> Dict[str, float]:
    """Return key dashboard figures from the filtered expenses."""
    total_spent = float(expenses_df["amount"].sum()) if not expenses_df.empty else 0.0
    budget = float(budget_amount or 0.0)
    remaining_budget = budget - total_spent
    spent_percentage = (total_spent / budget * 100) if budget > 0 else 0.0

    return {
        "total_spent": round(total_spent, 2),
        "budget": round(budget, 2),
        "remaining_budget": round(remaining_budget, 2),
        "spent_percentage": round(spent_percentage, 2),
    }


def category_breakdown(expenses_df: pd.DataFrame) -> pd.Series:
    """Aggregate expense totals by category."""
    if expenses_df.empty:
        return pd.Series(dtype=float)
    return expenses_df.groupby("category")["amount"].sum().sort_values(ascending=False)


def daily_spending(expenses_df: pd.DataFrame) -> pd.Series:
    """Aggregate expense totals by day."""
    if expenses_df.empty:
        return pd.Series(dtype=float)

    daily_df = expenses_df.copy()
    daily_df["expense_day"] = pd.to_datetime(daily_df["date"]).dt.date
    return daily_df.groupby("expense_day")["amount"].sum().sort_index()


def create_pie_chart(category_totals: pd.Series):
    """Build a pie chart figure for category-level spending."""
    figure, axis = plt.subplots(figsize=(6, 4))
    axis.pie(
        category_totals.values,
        labels=category_totals.index,
        autopct="%1.1f%%",
        startangle=140,
    )
    axis.set_title("Category-wise Spending")
    axis.axis("equal")
    figure.tight_layout()
    return figure


def create_line_chart(daily_totals: pd.Series):
    """Build a line chart figure for daily spending trend."""
    figure, axis = plt.subplots(figsize=(7, 4))
    axis.plot(daily_totals.index, daily_totals.values, marker="o", linewidth=2, color="#2563eb")
    axis.set_title("Daily Spending Trend")
    axis.set_xlabel("Date")
    axis.set_ylabel("Amount (INR)")
    axis.grid(alpha=0.3)
    figure.autofmt_xdate(rotation=30)
    figure.tight_layout()
    return figure
