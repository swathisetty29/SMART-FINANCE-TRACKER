from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd


DB_PATH = Path(__file__).resolve().parent / "finance.db"


def _get_connection() -> sqlite3.Connection:
    """Create a SQLite connection with row access by column name."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _hash_password(password: str) -> str:
    """Hash a password before storing it in the database."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _column_exists(connection: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    """Check whether a given column exists on a table."""
    columns = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(column["name"] == column_name for column in columns)


def init_db() -> None:
    """Initialize the SQLite database and required tables."""
    try:
        with _get_connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    date TEXT NOT NULL,
                    note TEXT,
                    FOREIGN KEY(username) REFERENCES users(username)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS budget (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    monthly_budget REAL NOT NULL,
                    year INTEGER,
                    month INTEGER,
                    FOREIGN KEY(username) REFERENCES users(username)
                )
                """
            )

            if not _column_exists(connection, "budget", "year"):
                connection.execute("ALTER TABLE budget ADD COLUMN year INTEGER")
            if not _column_exists(connection, "budget", "month"):
                connection.execute("ALTER TABLE budget ADD COLUMN month INTEGER")

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_expenses_user_date_category
                ON expenses (username, date, category)
                """
            )
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_budget_user_month_year
                ON budget (username, year, month)
                """
            )
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to initialize database: {error}") from error


def register_user(username: str, email: str, password: str) -> None:
    """Create a new user account."""
    try:
        with _get_connection() as connection:
            connection.execute(
                """
                INSERT INTO users (username, email, password_hash)
                VALUES (?, ?, ?)
                """,
                (username.strip(), email.strip().lower(), _hash_password(password)),
            )
    except sqlite3.IntegrityError as error:
        raise ValueError("Username or email already exists.") from error
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to register user: {error}") from error


def authenticate_user(username: str, password: str) -> bool:
    """Validate username and password."""
    try:
        with _get_connection() as connection:
            row = connection.execute(
                """
                SELECT password_hash
                FROM users
                WHERE username = ?
                """,
                (username.strip(),),
            ).fetchone()
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to authenticate user: {error}") from error

    if not row:
        return False
    return row["password_hash"] == _hash_password(password)


def user_exists(username: str, email: str) -> bool:
    """Check whether a username and email pair exists."""
    try:
        with _get_connection() as connection:
            row = connection.execute(
                """
                SELECT id
                FROM users
                WHERE username = ? AND email = ?
                """,
                (username.strip(), email.strip().lower()),
            ).fetchone()
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to verify user details: {error}") from error

    return row is not None


def reset_password(username: str, email: str, new_password: str) -> bool:
    """Reset a user's password after verifying username and email."""
    try:
        with _get_connection() as connection:
            row = connection.execute(
                """
                SELECT id
                FROM users
                WHERE username = ? AND email = ?
                """,
                (username.strip(), email.strip().lower()),
            ).fetchone()

            if not row:
                return False

            connection.execute(
                """
                UPDATE users
                SET password_hash = ?
                WHERE id = ?
                """,
                (_hash_password(new_password), int(row["id"])),
            )
            return True
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to reset password: {error}") from error


def add_expense(username: str, amount: float, category: str, date: str, note: str = "") -> None:
    """Insert a new expense record into the database."""
    try:
        with _get_connection() as connection:
            connection.execute(
                """
                INSERT INTO expenses (username, amount, category, date, note)
                VALUES (?, ?, ?, ?, ?)
                """,
                (username, float(amount), category, date, note.strip()),
            )
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to add expense: {error}") from error


def get_all_expenses(username: str) -> pd.DataFrame:
    """Return all expense records for a user as a pandas DataFrame."""
    try:
        with _get_connection() as connection:
            dataframe = pd.read_sql_query(
                """
                SELECT id, amount, category, date, note
                FROM expenses
                WHERE username = ?
                ORDER BY date DESC, id DESC
                """,
                connection,
                params=[username],
            )
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to fetch expenses: {error}") from error

    if dataframe.empty:
        return pd.DataFrame(columns=["id", "amount", "category", "date", "note"])

    dataframe["amount"] = dataframe["amount"].astype(float)
    return dataframe


def filter_expenses(
    username: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> pd.DataFrame:
    """Filter expenses by date range, category, and optionally month/year for a user."""
    query = """
        SELECT id, amount, category, date, note
        FROM expenses
        WHERE username = ?
    """
    params: list[object] = [username]

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    if year is not None:
        query += " AND CAST(strftime('%Y', date) AS INTEGER) = ?"
        params.append(int(year))
    if month is not None:
        query += " AND CAST(strftime('%m', date) AS INTEGER) = ?"
        params.append(int(month))
    if category and category != "All":
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY date ASC, id ASC"

    try:
        with _get_connection() as connection:
            dataframe = pd.read_sql_query(query, connection, params=params)
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to filter expenses: {error}") from error

    if dataframe.empty:
        return pd.DataFrame(columns=["id", "amount", "category", "date", "note"])

    dataframe["amount"] = dataframe["amount"].astype(float)
    return dataframe


def set_budget(username: str, amount: float, year: int, month: int) -> None:
    """Insert or update the monthly budget for a specific month and year."""
    try:
        with _get_connection() as connection:
            existing = connection.execute(
                """
                SELECT id
                FROM budget
                WHERE username = ? AND year = ? AND month = ?
                LIMIT 1
                """,
                (username, int(year), int(month)),
            ).fetchone()

            if existing:
                connection.execute(
                    """
                    UPDATE budget
                    SET monthly_budget = ?
                    WHERE username = ? AND year = ? AND month = ?
                    """,
                    (float(amount), username, int(year), int(month)),
                )
            else:
                connection.execute(
                    """
                    INSERT INTO budget (username, monthly_budget, year, month)
                    VALUES (?, ?, ?, ?)
                    """,
                    (username, float(amount), int(year), int(month)),
                )
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to save budget: {error}") from error


def get_budget(username: str, year: int, month: int) -> Optional[float]:
    """Return the monthly budget for a specific month and year."""
    try:
        with _get_connection() as connection:
            row = connection.execute(
                """
                SELECT monthly_budget
                FROM budget
                WHERE username = ? AND year = ? AND month = ?
                LIMIT 1
                """,
                (username, int(year), int(month)),
            ).fetchone()
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to fetch budget: {error}") from error

    return float(row["monthly_budget"]) if row else None
