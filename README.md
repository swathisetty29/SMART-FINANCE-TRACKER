# Personal Finance Tracker

A modular personal finance tracker built with Python, Streamlit, SQLite, pandas, and matplotlib.

## Features

- Set a monthly budget
- Add daily expenses with amount, category, date, and optional note
- Persist budget and expense data in SQLite
- View a dashboard with total spent, remaining budget, category chart, and daily trend
- Filter expenses by date and category
- Get rule-based smart suggestions from spending behavior

## Project Structure

- `app.py` - Streamlit app entry point
- `database.py` - SQLite setup and data access helpers
- `analytics.py` - Summary calculations and chart generation
- `insights.py` - Rule-based financial suggestions
- `finance_tracker.db` - SQLite database file created automatically on first run

## Install

```bash
pip install streamlit pandas matplotlib
```

## Run

```bash
streamlit run app.py
```

## Notes

- Budget is stored month-wise using the `YYYY-MM` format.
- Charts and insights respect the selected filters.
- The application creates the SQLite database automatically if it does not exist.
