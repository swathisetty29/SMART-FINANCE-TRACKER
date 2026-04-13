from __future__ import annotations

from calendar import month_name, monthrange
from datetime import date
from datetime import datetime, timedelta
from email.message import EmailMessage
import os
import secrets
import smtplib

import pandas as pd
import streamlit as st

from analytics import (
    calculate_summary,
    category_breakdown,
    create_line_chart,
    create_pie_chart,
    daily_spending,
)
from database import (
    add_expense,
    authenticate_user,
    filter_expenses,
    get_budget,
    init_db,
    register_user,
    reset_password,
    set_budget,
    user_exists,
)
from insights import analyze_finances


st.set_page_config(page_title="Smart Finance Tracker", page_icon="💰", layout="wide")

CATEGORIES = ["Food", "Travel", "Shopping", "Bills", "Others"]


def format_currency(amount: float) -> str:
    return f"₹{amount:,.2f}"


def apply_custom_styles() -> None:
    """Add lightweight custom styling for a cleaner interface."""
    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 2.25rem;
                padding-bottom: 2rem;
                max-width: 1180px;
            }
            .card {
                background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
                border: 1px solid #e2e8f0;
                border-radius: 18px;
                padding: 1.1rem 1.15rem;
                box-shadow: 0 16px 32px rgba(15, 23, 42, 0.06);
                margin-bottom: 1rem;
            }
            .metric-label {
                color: #64748b;
                font-size: 0.92rem;
                margin-bottom: 0.25rem;
            }
            .metric-value {
                font-size: 1.9rem;
                font-weight: 700;
                color: #0f172a;
            }
            .page-title {
                font-size: 2.1rem;
                font-weight: 700;
                margin-bottom: 0.25rem;
            }
            .page-subtitle {
                color: #64748b;
                margin-bottom: 1.2rem;
            }
            .section-gap {
                margin-top: 0.6rem;
                margin-bottom: 0.8rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def ensure_session_state() -> None:
    """Initialize session state keys used by the app."""
    today = date.today()
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = ""
    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "Login"
    if "selected_month" not in st.session_state:
        st.session_state.selected_month = today.month
    if "selected_year" not in st.session_state:
        st.session_state.selected_year = today.year
    if "auth_form_version" not in st.session_state:
        st.session_state.auth_form_version = 0
    if "reset_step" not in st.session_state:
        st.session_state.reset_step = 1
    if "reset_identity" not in st.session_state:
        st.session_state.reset_identity = {"username": "", "email": ""}
    if "reset_code" not in st.session_state:
        st.session_state.reset_code = ""
    if "reset_code_expiry" not in st.session_state:
        st.session_state.reset_code_expiry = None


def refresh_auth_forms() -> None:
    """Force auth widgets to rebuild with empty values."""
    st.session_state.auth_form_version += 1


def set_auth_mode(mode: str) -> None:
    """Switch auth mode and reset visible auth form values safely."""
    st.session_state.auth_mode = mode
    st.session_state.reset_step = 1
    st.session_state.reset_identity = {"username": "", "email": ""}
    st.session_state.reset_code = ""
    st.session_state.reset_code_expiry = None
    refresh_auth_forms()


def get_auth_key(name: str) -> str:
    """Create a versioned widget key for auth inputs."""
    return f"{name}_{st.session_state.auth_form_version}"


def send_reset_code_email(email: str, code: str) -> tuple[bool, str]:
    """Send a password reset verification code by email using SMTP settings."""
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_sender = os.getenv("SMTP_SENDER", smtp_username or "")

    if not smtp_host or not smtp_port or not smtp_username or not smtp_password or not smtp_sender:
        return False, "Password reset email is not configured yet. Please ask the app owner to set SMTP details."

    message = EmailMessage()
    message["Subject"] = "Smart Finance Tracker Password Reset Code"
    message["From"] = smtp_sender
    message["To"] = email.strip().lower()
    message.set_content(
        "Your Smart Finance Tracker verification code is "
        f"{code}. This code will expire in 10 minutes."
    )

    try:
        with smtplib.SMTP(smtp_host, int(smtp_port), timeout=20) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(message)
    except Exception:
        return False, "We could not send the verification code right now. Please try again in a moment."

    return True, "A verification code has been sent to your email."


def render_metric_card(label: str, value: str, value_color: str = "#0f172a") -> None:
    """Render a simple metric card using HTML styling."""
    st.markdown(
        f"""
        <div class="card">
            <div class="metric-label">{label}</div>
            <div class="metric-value" style="color: {value_color};">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(title: str, subtitle: str) -> None:
    """Render a clean heading area for each page."""
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def get_month_bounds(selected_year: int, selected_month: int) -> tuple[date, date]:
    """Return the first and last date for a selected month."""
    first_day = date(selected_year, selected_month, 1)
    last_day = date(selected_year, selected_month, monthrange(selected_year, selected_month)[1])
    return first_day, last_day


def get_month_label(selected_year: int, selected_month: int) -> str:
    """Return a user-friendly month label."""
    return f"{month_name[selected_month]} {selected_year}"


def render_auth_screen() -> None:
    """Render the login and registration interface."""
    _, center, _ = st.columns([1, 1.35, 1])
    with center:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(
            "<h1 style='text-align: center; margin-bottom: 0.25rem;'>💰 Smart Finance Tracker</h1>",
            unsafe_allow_html=True,
        )
        st.caption("Login or create an account to manage your monthly budget and expenses.")

        selected_mode = st.radio(
            "Choose an option",
            ["Login", "Register"],
            index=0 if st.session_state.auth_mode == "Login" else 1,
            horizontal=True,
            label_visibility="collapsed",
        )
        if selected_mode != st.session_state.auth_mode:
            set_auth_mode(selected_mode)
            st.rerun()

        if st.session_state.auth_mode == "Login":
            with st.form("login_form"):
                username = st.text_input("Username", key=get_auth_key("login_username"))
                password = st.text_input("Password", type="password", key=get_auth_key("login_password"))
                submitted = st.form_submit_button("Login", use_container_width=True)

            if submitted:
                try:
                    if authenticate_user(username, password):
                        st.session_state.logged_in = True
                        st.session_state.username = username.strip()
                        refresh_auth_forms()
                        st.success("Login successful.")
                        st.rerun()
                    else:
                        st.error("Login failed. Please check your username and password.")
                except Exception:
                    st.error("Login failed. Please try again.")

            with st.expander("Forgot Password?"):
                if st.session_state.reset_step == 1:
                    with st.form("forgot_password_step_one"):
                        reset_username_value = st.text_input("Username", key=get_auth_key("reset_username"))
                        reset_email_value = st.text_input("Email", key=get_auth_key("reset_email"))
                        send_code = st.form_submit_button("Send Verification Code", use_container_width=True)

                    if send_code:
                        if not reset_username_value.strip() or not reset_email_value.strip():
                            st.error("Please enter both username and email.")
                        elif "@" not in reset_email_value or "." not in reset_email_value:
                            st.error("Please enter a valid email address.")
                        else:
                            try:
                                if not user_exists(reset_username_value, reset_email_value):
                                    st.error("We could not find an account with those details.")
                                else:
                                    code = f"{secrets.randbelow(1000000):06d}"
                                    sent, message = send_reset_code_email(reset_email_value, code)
                                    if sent:
                                        st.session_state.reset_identity = {
                                            "username": reset_username_value.strip(),
                                            "email": reset_email_value.strip().lower(),
                                        }
                                        st.session_state.reset_code = code
                                        st.session_state.reset_code_expiry = datetime.now() + timedelta(minutes=10)
                                        st.session_state.reset_step = 2
                                        refresh_auth_forms()
                                        st.success(message)
                                        st.rerun()
                                    else:
                                        st.error(message)
                            except Exception:
                                st.error("We could not start password recovery. Please try again.")
                else:
                    st.info(
                        f"A verification code was sent to {st.session_state.reset_identity['email']}. "
                        "Enter it below to continue."
                    )
                    with st.form("forgot_password_step_two"):
                        entered_code = st.text_input("Verification Code", key=get_auth_key("verification_code"))
                        new_password = st.text_input("New Password", type="password", key=get_auth_key("reset_password"))
                        confirm_password = st.text_input(
                            "Confirm New Password",
                            type="password",
                            key=get_auth_key("reset_confirm_password"),
                        )
                        reset_submitted = st.form_submit_button("Verify and Reset Password", use_container_width=True)

                    if reset_submitted:
                        expiry = st.session_state.reset_code_expiry
                        if not entered_code.strip() or not new_password:
                            st.error("Please fill in all fields.")
                        elif expiry is None or datetime.now() > expiry:
                            st.error("The verification code has expired. Please request a new one.")
                            st.session_state.reset_step = 1
                            st.session_state.reset_code = ""
                            st.session_state.reset_code_expiry = None
                            refresh_auth_forms()
                        elif entered_code.strip() != st.session_state.reset_code:
                            st.error("Verification failed. Please check the code and try again.")
                        elif len(new_password) < 6:
                            st.error("New password must be at least 6 characters long.")
                        elif new_password != confirm_password:
                            st.error("Passwords do not match.")
                        else:
                            try:
                                updated = reset_password(
                                    st.session_state.reset_identity["username"],
                                    st.session_state.reset_identity["email"],
                                    new_password,
                                )
                                if updated:
                                    st.session_state.reset_step = 1
                                    st.session_state.reset_identity = {"username": "", "email": ""}
                                    st.session_state.reset_code = ""
                                    st.session_state.reset_code_expiry = None
                                    refresh_auth_forms()
                                    st.success("Password reset successful. Please log in with your new password.")
                                    st.rerun()
                                else:
                                    st.error("Password reset failed. Please start again.")
                            except Exception:
                                st.error("Password reset failed. Please try again.")

                    if st.button("Start Over", key=get_auth_key("reset_restart"), use_container_width=True):
                        st.session_state.reset_step = 1
                        st.session_state.reset_identity = {"username": "", "email": ""}
                        st.session_state.reset_code = ""
                        st.session_state.reset_code_expiry = None
                        refresh_auth_forms()
                        st.rerun()
        else:
            with st.form("register_form"):
                username = st.text_input("Username", key=get_auth_key("register_username"))
                email = st.text_input("Email", key=get_auth_key("register_email"))
                password = st.text_input("Password", type="password", key=get_auth_key("register_password"))
                confirm_password = st.text_input(
                    "Confirm Password",
                    type="password",
                    key=get_auth_key("register_confirm_password"),
                )
                submitted = st.form_submit_button("Register", use_container_width=True)

            if submitted:
                if not username.strip() or not email.strip() or not password:
                    st.error("All fields are required.")
                elif "@" not in email or "." not in email:
                    st.error("Enter a valid email address.")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters long.")
                elif password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    try:
                        register_user(username, email, password)
                        set_auth_mode("Login")
                        st.success("Registration successful. You can log in now.")
                    except ValueError:
                        st.error("Registration failed. That username or email is already in use.")
                    except Exception:
                        st.error("Registration failed. Please try again.")
        st.markdown("</div>", unsafe_allow_html=True)


def render_sidebar(username: str) -> tuple[str, int, int]:
    """Render sidebar navigation and month/year selectors."""
    current_year = date.today().year
    year_options = list(range(current_year - 4, current_year + 6))

    st.sidebar.title("💰 Smart Finance Tracker")
    st.sidebar.caption(f"Logged in as: `{username}`")
    st.sidebar.markdown("---")
    selected_month = st.sidebar.selectbox(
        "Select Month",
        options=list(range(1, 13)),
        index=st.session_state.selected_month - 1,
        format_func=lambda value: month_name[value],
    )
    selected_year = st.sidebar.selectbox(
        "Select Year",
        options=year_options,
        index=year_options.index(st.session_state.selected_year)
        if st.session_state.selected_year in year_options
        else year_options.index(current_year),
    )
    st.session_state.selected_month = selected_month
    st.session_state.selected_year = selected_year

    st.sidebar.markdown("---")
    page = st.sidebar.radio("Menu", ["Dashboard", "Add Expense", "View Expenses", "Insights"])
    st.sidebar.markdown("---")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()
    return page, selected_month, selected_year


def render_budget_editor(username: str, selected_year: int, selected_month: int) -> float | None:
    """Render the month-specific budget editor."""
    month_label = get_month_label(selected_year, selected_month)
    budget_amount = get_budget(username, selected_year, selected_month)

    st.subheader("💼 Monthly Budget")
    st.caption(f"Set a budget for {month_label}.")
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        with st.form("budget_form"):
            budget_input = st.number_input(
                f"Budget for {month_label}",
                min_value=0.0,
                value=float(budget_amount or 0.0),
                step=100.0,
                format="%.2f",
            )
            submitted = st.form_submit_button("Save Budget", use_container_width=True)

        if submitted:
            try:
                set_budget(username, float(budget_input), selected_year, selected_month)
                st.success("Monthly budget saved successfully.")
                budget_amount = float(budget_input)
            except Exception as error:
                st.error(str(error))
        st.markdown("</div>", unsafe_allow_html=True)
    return budget_amount


def get_selected_month_expenses(
    username: str,
    selected_year: int,
    selected_month: int,
    category: str = "All",
) -> pd.DataFrame:
    """Fetch expense data for the selected month and optional category."""
    first_day, last_day = get_month_bounds(selected_year, selected_month)
    return filter_expenses(
        username=username,
        start_date=first_day.isoformat(),
        end_date=last_day.isoformat(),
        category=category,
        year=selected_year,
        month=selected_month,
    )


def render_month_filter_card() -> str:
    """Render the category filter card used by monthly pages."""
    st.markdown('<div class="card">', unsafe_allow_html=True)
    selected_category = st.selectbox("Filter by Category", ["All"] + CATEGORIES)
    st.markdown("</div>", unsafe_allow_html=True)
    return selected_category


def render_dashboard_page(username: str, selected_year: int, selected_month: int) -> None:
    """Render the main monthly dashboard."""
    render_page_header("💰 Smart Finance Dashboard", "A clear monthly view of your budget, spending, and trends.")

    month_label = get_month_label(selected_year, selected_month)
    st.caption(f"Showing data for {month_label}")
    budget_amount = render_budget_editor(username, selected_year, selected_month)

    st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)
    st.subheader("📊 Overview")
    selected_category = render_month_filter_card()
    expenses_df = get_selected_month_expenses(username, selected_year, selected_month, selected_category)
    summary = calculate_summary(expenses_df, budget_amount)

    remaining_color = "#16a34a" if summary["remaining_budget"] >= 0 else "#dc2626"
    col1, col2, col3 = st.columns(3, gap="large")
    with col1:
        render_metric_card("Total Budget", format_currency(summary["budget"]))
    with col2:
        render_metric_card("Total Spent", format_currency(summary["total_spent"]))
    with col3:
        render_metric_card("Remaining Balance", format_currency(summary["remaining_budget"]), remaining_color)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    progress_value = min(summary["spent_percentage"] / 100, 1.0) if summary["budget"] > 0 else 0.0
    st.write("Budget usage")
    st.progress(progress_value, text=f"{summary['spent_percentage']:.2f}% of budget used")
    st.markdown("</div>", unsafe_allow_html=True)

    if expenses_df.empty:
        st.info("No expenses recorded for this month yet.")
        return

    chart_col1, chart_col2 = st.columns(2, gap="large")
    category_totals = category_breakdown(expenses_df)
    daily_totals = daily_spending(expenses_df)

    with chart_col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("🥧 Category Breakdown")
        st.pyplot(create_pie_chart(category_totals), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with chart_col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📈 Daily Spending Trend")
        st.pyplot(create_line_chart(daily_totals), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    render_dashboard_insights(username, expenses_df, budget_amount, selected_year, selected_month)


def render_dashboard_insights(
    username: str,
    expenses_df: pd.DataFrame,
    budget_amount: float | None,
    selected_year: int,
    selected_month: int,
) -> None:
    """Render dashboard insights using friendly alert components."""
    del username
    del selected_year
    del selected_month
    st.subheader("💡 Insights")
    analysis = analyze_finances(expenses_df, budget_amount)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    summary = analysis["summary"]
    st.write(
        f"Top category: {summary['top_category']} | Total spent: {format_currency(summary['total_spent'])}"
    )
    st.markdown("</div>", unsafe_allow_html=True)

    for warning in analysis["warnings"]:
        st.warning(warning)
    for insight in analysis["insights"]:
        st.info(insight)
    st.success(analysis["prediction"])


def render_add_expense_page(username: str, selected_year: int, selected_month: int) -> None:
    """Render the add expense form page."""
    render_page_header("🧾 Add Expense", "Capture expenses for the selected month in a clean, simple form.")
    first_day, last_day = get_month_bounds(selected_year, selected_month)

    st.caption(f"Expenses added here will belong to {get_month_label(selected_year, selected_month)}.")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    with st.form("expense_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            amount = st.number_input("Amount", min_value=0.01, step=10.0, format="%.2f")
            category = st.selectbox("Category", CATEGORIES)
        with col2:
            expense_date = st.date_input(
                "Date",
                value=first_day,
                min_value=first_day,
                max_value=last_day,
            )
            note = st.text_input("Optional Note")
        submitted = st.form_submit_button("Add Expense", use_container_width=True)

    if submitted:
        try:
            add_expense(username, float(amount), category, expense_date.isoformat(), note)
            st.success("Expense added successfully.")
        except Exception as error:
            st.error(str(error))
    st.markdown("</div>", unsafe_allow_html=True)


def render_view_expenses_page(username: str, selected_year: int, selected_month: int) -> None:
    """Render the monthly expense table with filters."""
    render_page_header("📋 View Expenses", "Review all expenses recorded for the selected month.")
    selected_category = render_month_filter_card()
    expenses_df = get_selected_month_expenses(username, selected_year, selected_month, selected_category)

    if expenses_df.empty:
        st.info("No expenses found for the selected month and category.")
        return

    display_df = expenses_df.copy()
    display_df["date"] = pd.to_datetime(display_df["date"]).dt.strftime("%Y-%m-%d")
    display_df["amount"] = display_df["amount"].map(format_currency)
    st.dataframe(display_df[["date", "category", "amount", "note"]], use_container_width=True)


def render_insights_page(username: str, selected_year: int, selected_month: int) -> None:
    """Render human-friendly monthly suggestions."""
    render_page_header("🧠 Monthly Insights", "Friendly guidance based on your spending behavior this month.")
    budget_amount = get_budget(username, selected_year, selected_month)
    expenses_df = get_selected_month_expenses(username, selected_year, selected_month)
    analysis = analyze_finances(expenses_df, budget_amount)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    summary = analysis["summary"]
    st.write(
        f"Highest category this month: {summary['top_category']} ({summary['percentage']:.2f}%)"
    )
    st.write(f"Total spent this month: {format_currency(summary['total_spent'])}")
    st.markdown("</div>", unsafe_allow_html=True)

    for warning in analysis["warnings"]:
        st.warning(warning)
    for insight in analysis["insights"]:
        st.info(insight)
    st.success(analysis["prediction"])


def main() -> None:
    """Application entry point."""
    init_db()
    apply_custom_styles()
    ensure_session_state()

    if not st.session_state.logged_in:
        render_auth_screen()
        return

    username = st.session_state.username
    page, selected_month, selected_year = render_sidebar(username)

    if page == "Dashboard":
        render_dashboard_page(username, selected_year, selected_month)
    elif page == "Add Expense":
        render_add_expense_page(username, selected_year, selected_month)
    elif page == "View Expenses":
        render_view_expenses_page(username, selected_year, selected_month)
    else:
        render_insights_page(username, selected_year, selected_month)


if __name__ == "__main__":
    main()
