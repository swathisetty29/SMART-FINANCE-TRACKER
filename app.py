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
    add_borrowing,
    add_expense,
    authenticate_user,
    create_user_session,
    delete_user_session,
    filter_expenses,
    get_budget,
    get_borrowings,
    get_user_by_session_token,
    get_username_for_login,
    init_db,
    register_user,
    reset_password,
    set_budget,
    user_exists,
)
from insights import analyze_finances


st.set_page_config(page_title="Smart Finance Tracker", page_icon="💰", layout="wide")

CATEGORIES = ["Food", "Travel", "Shopping", "Bills", "Others"]
PAGE_QUOTES = {
    "login": "Come back, track clearly, and take one more step toward reducing unnecessary expenses.",
    "register": "Start here, build better money habits, and turn small tracking into big savings.",
    "dashboard": "A budget is not a restriction. It is a plan for peace of mind.",
    "add_expense": "Every expense you record gives your future self more clarity.",
    "view_expenses": "Clear records turn confusion into confidence.",
    "borrowed_money": "Borrow carefully, track honestly, and repay with confidence.",
    "insights": "Awareness is the first step toward financial growth.",
}


def format_currency(amount: float) -> str:
    return f"₹{amount:,.2f}"


def parse_amount_input(raw_value: str) -> float:
    """Convert a typed amount string into a valid float."""
    cleaned_value = raw_value.replace(",", "").strip()
    if not cleaned_value:
        raise ValueError("Please enter an amount.")

    try:
        amount = float(cleaned_value)
    except ValueError as error:
        raise ValueError("Enter a valid number like 5000, 12,500, or 2500.75.") from error

    if amount <= 0:
        raise ValueError("Amount must be greater than 0.")

    return round(amount, 2)


def apply_custom_styles() -> None:
    """Add premium dark-mode styling with falling coins, gold accents, and ultra-thin dividers."""
    st.markdown(
        """
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
        <style>
            /* ── Global Font ── */
            html, body, [class*="css"] {
                font-family: 'Inter', sans-serif !important;
                font-size: 1.02rem !important;
            }

            /* ── Dark Animated Background ── */
            .stApp {
                background: linear-gradient(-45deg, #0b101e, #111827, #0f1a2e, #1a1035) !important;
                background-size: 400% 400% !important;
                animation: darkBG 18s ease infinite !important;
            }
            @keyframes darkBG {
                0%   { background-position: 0% 50%; }
                50%  { background-position: 100% 50%; }
                100% { background-position: 0% 50%; }
            }

            /* ── Main Content Area ── */
            .block-container {
                padding-top: 5rem;
                padding-bottom: 2.5rem;
                max-width: 1200px;
                z-index: 10;
                position: relative;
            }

            /* ── Dark Glassmorphism Cards ── */
            .card {
                background: rgba(255, 255, 255, 0.04) !important;
                backdrop-filter: blur(20px) !important;
                -webkit-backdrop-filter: blur(20px) !important;
                border: 1px solid rgba(245, 166, 35, 0.18) !important;
                border-radius: 18px !important;
                padding: 1.5rem 1.6rem !important;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255,255,255,0.06) !important;
                margin-bottom: 1rem;
                transition: transform 0.3s ease, box-shadow 0.3s ease, border-color 0.3s ease;
            }
            .card:hover {
                transform: translateY(-4px);
                border-color: rgba(245, 166, 35, 0.45) !important;
                box-shadow: 0 16px 48px rgba(0, 0, 0, 0.55), 0 0 20px rgba(245, 166, 35, 0.08) !important;
            }

            /* ── Metric Labels & Values ── */
            .metric-label {
                color: #94a3b8;
                font-size: 0.78rem;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 1.2px;
                margin-bottom: 0.4rem;
            }
            .metric-value {
                font-size: 2.1rem;
                font-weight: 800;
                color: #f8fafc;
                letter-spacing: -0.5px;
            }

            /* ── Page Titles ── */
            .page-title {
                font-size: 2.3rem;
                font-weight: 900;
                margin-bottom: 0.3rem;
                background: linear-gradient(90deg, #F5A623 0%, #f9d06b 50%, #F5A623 100%);
                background-size: 200% auto;
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                animation: shimmer 3s linear infinite;
            }
            @keyframes shimmer {
                0%   { background-position: 0% center; }
                100% { background-position: 200% center; }
            }
            .page-subtitle {
                color: #94a3b8;
                font-size: 1.1rem;
                font-weight: 500;
                margin-bottom: 1.6rem;
            }
            .section-gap {
                margin-top: 0.6rem;
                margin-bottom: 0.8rem;
            }

            /* ── Sidebar ── */
            [data-testid="stSidebar"] {
                background: rgba(11, 16, 30, 0.92) !important;
                border-right: 1px solid rgba(245, 166, 35, 0.15) !important;
                backdrop-filter: blur(12px);
            }
            [data-testid="stSidebar"] .stSelectbox label,
            [data-testid="stSidebar"] .stRadio label {
                color: #94a3b8 !important;
                font-size: 0.82rem;
                text-transform: uppercase;
                letter-spacing: 0.8px;
            }

            /* ── Buttons ── */
            .stButton > button {
                background: linear-gradient(135deg, #F5A623 0%, #e8940f 100%) !important;
                color: #0b101e !important;
                border: none !important;
                border-radius: 12px !important;
                font-weight: 700 !important;
                font-size: 0.95rem !important;
                padding: 0.6rem 1.6rem !important;
                box-shadow: 0 4px 15px rgba(245, 166, 35, 0.3) !important;
            }
            .stButton > button:hover {
                transform: translateY(-2px) !important;
                box-shadow: 0 8px 25px rgba(245, 166, 35, 0.5) !important;
            }

            /* ── Text Inputs ── */
            .stTextInput > div > div > input,
            .stSelectbox > div > div {
                background: rgba(255,255,255,0.05) !important;
                border: 1px solid rgba(245, 166, 35, 0.2) !important;
                border-radius: 10px !important;
                color: #f1f5f9 !important;
                transition: all 0.2s ease !important;
            }
            .stTextInput > div > div > input:focus {
                border-color: #F5A623 !important;
                background: rgba(255,255,255,0.08) !important;
                box-shadow: 0 0 0 3px rgba(245, 166, 35, 0.15) !important;
            }

            /* Hide "Press Enter to submit form" tooltip (Aggressive) */
            div[data-testid="stFormSubmitTooltip"],
            [data-testid="stFormSubmitTooltip"],
            [data-testid="InputInstructions"],
            .stFormSubmitTooltip,
            .stInputInstructions {
                display: none !important;
                visibility: hidden !important;
                height: 0 !important;
                width: 0 !important;
                position: absolute !important;
                pointer-events: none !important;
            }

            /* ── ULTRA-THIN DIVIDER FIX ── */
            hr, [data-testid="stMarkdownContainer"] hr {
                all: unset !important;
                display: block !important;
                width: 100% !important;
                height: 1px !important;
                background-color: rgba(245, 166, 35, 0.2) !important;
                border: none !important;
                margin: 0.8rem 0 !important;
                padding: 0 !important;
                box-shadow: none !important;
                border-radius: 0 !important;
            }

            /* ── Falling Icons (Behind everything) ── */
            .coin-container {
                position: fixed;
                top: 0;
                left: 0;
                width: 100vw;
                height: 100vh;
                overflow: hidden;
                pointer-events: none;
                z-index: -1 !important;
            }
            .coin {
                position: absolute;
                top: -10vh;
                font-size: 2rem;
                opacity: 0.35;
                animation: fall linear infinite;
            }
            @keyframes fall {
                0%   { transform: translateY(-10vh) rotate(0deg); opacity: 0; }
                10%  { opacity: 0.5; }
                90%  { opacity: 0.5; }
                100% { transform: translateY(110vh) rotate(360deg); opacity: 0; }
            }
            .coin:nth-child(1)  { left: 5%;  animation-duration: 8s;   animation-delay: 0s; }
            .coin:nth-child(2)  { left: 15%; animation-duration: 12s;  animation-delay: 2s; }
            .coin:nth-child(3)  { left: 25%; animation-duration: 9s;   animation-delay: 4s; }
            .coin:nth-child(4)  { left: 35%; animation-duration: 15s;  animation-delay: 1s; }
            .coin:nth-child(5)  { left: 45%; animation-duration: 10s;  animation-delay: 5s; }
            .coin:nth-child(6)  { left: 55%; animation-duration: 7s;   animation-delay: 3s; }
            .coin:nth-child(7)  { left: 65%; animation-duration: 11s;  animation-delay: 7s; }
            .coin:nth-child(8)  { left: 75%; animation-duration: 14s;  animation-delay: 2s; }
            .coin:nth-child(9)  { left: 85%; animation-duration: 9.5s; animation-delay: 6s; }
            .coin:nth-child(10) { left: 95%; animation-duration: 13s;  animation-delay: 4s; }
        </style>

        <div class="coin-container">
            <div class="coin">🪙</div>
            <div class="coin">💵</div>
            <div class="coin">🪙</div>
            <div class="coin">💶</div>
            <div class="coin">💰</div>
            <div class="coin">💸</div>
            <div class="coin">🪙</div>
            <div class="coin">💳</div>
            <div class="coin">🪙</div>
            <div class="coin">💎</div>
        </div>
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
    if "reset_feedback" not in st.session_state:
        st.session_state.reset_feedback = {"type": "", "message": "", "code": ""}
    if "session_token" not in st.session_state:
        st.session_state.session_token = ""


def refresh_auth_forms() -> None:
    """Force auth widgets to rebuild with empty values."""
    st.session_state.auth_form_version += 1


def reset_password_recovery_state() -> None:
    """Clear the full forgot-password flow state."""
    st.session_state.reset_step = 1
    st.session_state.reset_identity = {"username": "", "email": ""}
    st.session_state.reset_code = ""
    st.session_state.reset_code_expiry = None
    st.session_state.reset_feedback = {"type": "", "message": "", "code": ""}


def set_auth_mode(mode: str) -> None:
    """Switch auth mode and reset visible auth form values safely."""
    st.session_state.auth_mode = mode
    reset_password_recovery_state()
    refresh_auth_forms()


def get_auth_key(name: str) -> str:
    """Create a versioned widget key for auth inputs."""
    return f"{name}_{st.session_state.auth_form_version}"


def send_reset_code_email(email: str, code: str) -> tuple[bool, str, str]:
    """Send a password reset verification code by email using SMTP settings."""
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_sender = os.getenv("SMTP_SENDER", smtp_username or "")

    if not smtp_host or not smtp_port or not smtp_username or not smtp_password or not smtp_sender:
        return (
            True,
            "Email delivery is not configured on this machine, so a demo verification code is shown below.",
            "demo",
        )

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
        return (
            True,
            "We could not deliver the email right now, so a temporary verification code is shown below.",
            "demo",
        )

    return True, "A verification code has been sent to your email.", "email"


def render_feedback_message(message_type: str, message: str) -> None:
    """Render a user-friendly status message."""
    if not message:
        return
    if message_type == "success":
        st.success(message)
    elif message_type == "warning":
        st.warning(message)
    elif message_type == "error":
        st.error(message)
    else:
        st.info(message)


def render_metric_card(label: str, value: str, value_color: str = "#f8fafc") -> None:
    """Render a premium dark metric card using HTML styling."""
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


def render_page_quote(quote: str) -> None:
    """Render a premium short motivational quote card."""
    st.markdown(
        f"""
        <div class="card" style="padding: 0.9rem 1.2rem; border-left: 4px solid #F5A623;">
            <div style="color: #94a3b8; font-style: italic; font-size: 0.95rem; line-height: 1.6;">"{quote}"</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_month_bounds(selected_year: int, selected_month: int) -> tuple[date, date]:
    """Return the first and last date for a selected month."""
    first_day = date(selected_year, selected_month, 1)
    last_day = date(selected_year, selected_month, monthrange(selected_year, selected_month)[1])
    return first_day, last_day


def get_month_label(selected_year: int, selected_month: int) -> str:
    """Return a user-friendly month label."""
    return f"{month_name[selected_month]} {selected_year}"


def get_month_access_state(selected_year: int, selected_month: int) -> str:
    """Return whether the selected month is past, current, or future."""
    today = date.today()
    if (selected_year, selected_month) < (today.year, today.month):
        return "past"
    if (selected_year, selected_month) > (today.year, today.month):
        return "future"
    return "current"


def render_month_access_notice(month_access_state: str) -> None:
    """Show clear read/write restrictions for the selected month."""
    if month_access_state == "future":
        st.warning("You cannot add expenses for future months")
    elif month_access_state == "past":
        st.info("This month is read-only. You can only view expenses")


def get_selected_year_expenses(
    username: str,
    selected_year: int,
    category: str = "All",
) -> pd.DataFrame:
    """Fetch year-to-date expense data for the selected year."""
    today = date.today()
    start_date = date(selected_year, 1, 1)
    if selected_year < today.year:
        end_date = date(selected_year, 12, 31)
    elif selected_year == today.year:
        end_date = today
    else:
        return pd.DataFrame(columns=["date", "category", "amount", "note"])

    return filter_expenses(
        username=username,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        category=category,
    )


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
        render_page_quote(PAGE_QUOTES["login"] if st.session_state.auth_mode == "Login" else PAGE_QUOTES["register"])

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
                username = st.text_input(
                    "Username or Email",
                    key=get_auth_key("login_username"),
                    autocomplete="off",
                    placeholder="Enter your username or email",
                )
                password = st.text_input(
                    "Password",
                    type="password",
                    key=get_auth_key("login_password"),
                    autocomplete="off",
                    placeholder="Enter your password",
                )
                submitted = st.form_submit_button("Login", use_container_width=True)

            if submitted:
                try:
                    if authenticate_user(username, password):
                        resolved_username = get_username_for_login(username)
                        session_token = create_user_session(resolved_username or username.strip())
                        st.session_state.logged_in = True
                        st.session_state.username = resolved_username or username.strip()
                        st.session_state.session_token = session_token
                        st.query_params["session"] = session_token
                        refresh_auth_forms()
                        st.success("Login successful.")
                        st.rerun()
                    else:
                        st.error("Login failed. Please check your username and password.")
                except Exception:
                    st.error("Login failed. Please try again.")

            with st.expander("Forgot Password?"):
                feedback = st.session_state.reset_feedback
                render_feedback_message(feedback["type"], feedback["message"])

                if feedback["code"]:
                    st.info("Use this verification code in the next step.")
                    st.code(feedback["code"])

                if st.session_state.reset_step == 1:
                    st.caption("Step 1 of 2: verify your account and request a code.")
                    with st.form("forgot_password_step_one"):
                        reset_username_value = st.text_input(
                            "Username",
                            key=get_auth_key("reset_username"),
                            autocomplete="off",
                            placeholder="Enter your username",
                        )
                        reset_email_value = st.text_input(
                            "Email",
                            key=get_auth_key("reset_email"),
                            autocomplete="off",
                            placeholder="Enter your email",
                        )
                        send_code = st.form_submit_button("Send Verification Code", use_container_width=True)

                    if send_code:
                        if not reset_username_value.strip() or not reset_email_value.strip():
                            st.error("Please enter both username and email.")
                        elif "@" not in reset_email_value or "." not in reset_email_value:
                            st.error("Please enter a valid email address.")
                        else:
                            try:
                                reset_password_recovery_state()
                                if not user_exists(reset_username_value, reset_email_value):
                                    st.error("We could not find an account with those details.")
                                else:
                                    code = f"{secrets.randbelow(1000000):06d}"
                                    sent, message, delivery_mode = send_reset_code_email(reset_email_value, code)
                                    if sent:
                                        st.session_state.reset_identity = {
                                            "username": reset_username_value.strip(),
                                            "email": reset_email_value.strip().lower(),
                                        }
                                        st.session_state.reset_code = code
                                        st.session_state.reset_code_expiry = datetime.now() + timedelta(minutes=10)
                                        st.session_state.reset_step = 2
                                        st.session_state.reset_feedback = {
                                            "type": "success" if delivery_mode == "email" else "warning",
                                            "message": message,
                                            "code": code if delivery_mode == "demo" else "",
                                        }
                                        refresh_auth_forms()
                                        st.rerun()
                                    else:
                                        st.session_state.reset_feedback = {
                                            "type": "error",
                                            "message": message,
                                            "code": "",
                                        }
                                        st.rerun()
                            except Exception:
                                st.error("We could not start password recovery. Please try again.")
                else:
                    st.caption("Step 2 of 2: enter the verification code and choose a new password.")
                    st.info(
                        f"Enter the verification code for {st.session_state.reset_identity['email']} to continue."
                    )
                    if st.button(
                        "Use a Different Account or Email",
                        key=get_auth_key("reset_change_identity"),
                        use_container_width=True,
                    ):
                        reset_password_recovery_state()
                        refresh_auth_forms()
                        st.rerun()

                    with st.form("forgot_password_step_two"):
                        entered_code = st.text_input(
                            "Verification Code",
                            key=get_auth_key("verification_code"),
                            autocomplete="one-time-code",
                            placeholder="Enter the 6-digit code",
                        )
                        new_password = st.text_input(
                            "New Password",
                            type="password",
                            key=get_auth_key("reset_password"),
                            autocomplete="new-password",
                            placeholder="Create a new password",
                        )
                        confirm_password = st.text_input(
                            "Confirm New Password",
                            type="password",
                            key=get_auth_key("reset_confirm_password"),
                            autocomplete="new-password",
                            placeholder="Re-enter your new password",
                        )
                        reset_submitted = st.form_submit_button("Verify and Reset Password", use_container_width=True)

                    if reset_submitted:
                        expiry = st.session_state.reset_code_expiry
                        if not entered_code.strip() or not new_password:
                            st.error("Please fill in all fields.")
                        elif expiry is None or datetime.now() > expiry:
                            st.error("The verification code has expired. Please request a new one.")
                            reset_password_recovery_state()
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
                                    reset_password_recovery_state()
                                    refresh_auth_forms()
                                    st.success("Password reset successful. Please log in with your new password.")
                                    st.rerun()
                                else:
                                    st.error("Password reset failed. Please start again.")
                            except Exception:
                                st.error("Password reset failed. Please try again.")

                    if st.button("Start Over", key=get_auth_key("reset_restart"), use_container_width=True):
                        reset_password_recovery_state()
                        refresh_auth_forms()
                        st.rerun()
        else:
            with st.form("register_form"):
                username = st.text_input(
                    "Username",
                    key=get_auth_key("register_username"),
                    autocomplete="off",
                    placeholder="Choose a username",
                )
                email = st.text_input(
                    "Email",
                    key=get_auth_key("register_email"),
                    autocomplete="off",
                    placeholder="Enter your email",
                )
                password = st.text_input(
                    "Password",
                    type="password",
                    key=get_auth_key("register_password"),
                    autocomplete="off",
                    placeholder="Create a password",
                )
                confirm_password = st.text_input(
                    "Confirm Password",
                    type="password",
                    key=get_auth_key("register_confirm_password"),
                    autocomplete="off",
                    placeholder="Re-enter your password",
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


def render_sidebar(username: str) -> tuple[str, int, int, str]:
    """Render sidebar navigation and month/year selectors."""
    current_year = date.today().year
    year_options = list(range(current_year - 4, current_year + 6))

    st.sidebar.title("💰 Smart Finance Tracker")
    st.sidebar.markdown(
        f"""<div style="font-size: 1.05rem; font-weight: 600; color: #94a3b8; margin-top: -0.3rem;">
        Logged in as: <span style="color: #F5A623; font-weight: 800; font-size: 1.1rem;">{username}</span>
        </div>""",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("<hr/>", unsafe_allow_html=True)
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

    st.sidebar.markdown("<hr/>", unsafe_allow_html=True)
    view_mode = st.sidebar.radio("Data Scope", ["Monthly View", "Yearly View"], horizontal=False)

    st.sidebar.markdown("<hr/>", unsafe_allow_html=True)
    menu_options = (
        ["Dashboard", "Add Expense", "View Expenses", "Borrowed Money", "Insights"]
        if view_mode == "Monthly View"
        else ["Dashboard", "View Expenses", "Insights"]
    )
    page = st.sidebar.radio(
        "Menu",
        menu_options,
    )
    st.sidebar.markdown("<hr/>", unsafe_allow_html=True)
    if st.sidebar.button("Logout", use_container_width=True):
        if st.session_state.session_token:
            try:
                delete_user_session(st.session_state.session_token)
            except Exception:
                pass
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.session_token = ""
        if "session" in st.query_params:
            del st.query_params["session"]
        st.rerun()
    return page, selected_month, selected_year, view_mode


def restore_login_from_query_params() -> None:
    """Restore login state from a persisted session token on full refresh."""
    if st.session_state.logged_in:
        return

    token = st.query_params.get("session")
    if not token:
        return

    try:
        username = get_user_by_session_token(token)
    except Exception:
        username = None

    if username:
        st.session_state.logged_in = True
        st.session_state.username = username
        st.session_state.session_token = token
    else:
        if "session" in st.query_params:
            del st.query_params["session"]


def render_budget_editor(username: str, selected_year: int, selected_month: int) -> float | None:
    """Render the month-specific budget editor."""
    render_page_quote(PAGE_QUOTES["dashboard"])
    month_label = get_month_label(selected_year, selected_month)
    budget_amount = get_budget(username, selected_year, selected_month)
    month_access_state = get_month_access_state(selected_year, selected_month)

    st.subheader("💼 Monthly Budget")
    st.caption(f"Set a budget for {month_label}.")
    render_month_access_notice(month_access_state)
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        with st.form("budget_form", clear_on_submit=False):
            budget_input = st.text_input(
                f"Budget for {month_label}",
                value=f"{float(budget_amount or 0.0):,.2f}" if budget_amount is not None else "",
                placeholder="Enter budget like 5000 or 12,500.75",
                disabled=month_access_state != "current",
            )
            submitted = st.form_submit_button(
                "Save Budget",
                use_container_width=True,
                disabled=month_access_state != "current",
            )

        if submitted and month_access_state == "current":
            try:
                parsed_budget = parse_amount_input(budget_input)
                set_budget(username, parsed_budget, selected_year, selected_month)
                st.success("Monthly budget saved successfully.")
                budget_amount = parsed_budget
            except ValueError as error:
                st.error(str(error))
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
    render_page_quote(PAGE_QUOTES["view_expenses"])
    selected_category = render_month_filter_card()
    expenses_df = get_selected_month_expenses(username, selected_year, selected_month, selected_category)
    summary = calculate_summary(expenses_df, budget_amount)

    # Fetch borrowing data
    first_day, last_day = get_month_bounds(selected_year, selected_month)
    borrowings_df = get_borrowings(
        username=username,
        start_date=first_day.isoformat(),
        end_date=last_day.isoformat(),
    )
    total_borrowed = float(borrowings_df["amount"].sum()) if not borrowings_df.empty else 0.0
    borrowing_count = len(borrowings_df)

    remaining_color = "#16a34a" if summary["remaining_budget"] >= 0 else "#dc2626"
    col1, col2, col3 = st.columns(3, gap="large")
    with col1:
        render_metric_card("Total Budget", format_currency(summary["budget"]))
    with col2:
        render_metric_card("Total Spent", format_currency(summary["total_spent"]))
    with col3:
        render_metric_card("Remaining Balance", format_currency(summary["remaining_budget"]), remaining_color)

    # New row for Borrowing metrics
    b_col1, b_col2, b_col3 = st.columns(3, gap="large")
    with b_col1:
        render_metric_card("Total Borrowed", format_currency(total_borrowed), "#b45309")
    with b_col2:
        render_metric_card("Borrowing Count", str(borrowing_count))
    with b_col3:
        # Placeholder for visual balance
        st.write("")

    # Borrow impact messages
    if total_borrowed > 0:
        st.warning(f"⚠️ You borrowed {format_currency(total_borrowed)} this month. Monitor your spending.")
    
    if (summary["total_spent"] + total_borrowed) > summary["budget"] and summary["budget"] > 0:
        st.error("🚨 Your expenses + borrowings exceed your budget")
    
    if summary["total_spent"] > summary["budget"] and total_borrowed > 0 and summary["budget"] > 0:
        st.info("💡 You started borrowing after exceeding your budget")

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
    analysis = analyze_finances(expenses_df, budget_amount)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    summary = analysis["summary"]
    st.write(
        f"Top category: {summary['top_category']} | Total spent: {format_currency(summary['total_spent'])}"
    )
    st.markdown("</div>", unsafe_allow_html=True)

    for warning in analysis["warnings"]:
        st.warning(warning)
    
    # Quick borrowing warning
    first_day, last_day = get_month_bounds(selected_year, selected_month)
    borrowings_df = get_borrowings(st.session_state.username, first_day.isoformat(), last_day.isoformat())
    if not borrowings_df.empty:
        st.warning("💳 Borrowing detected this month. Try reducing expenses.")

    for insight in analysis["insights"]:
        st.info(insight)
    st.success(analysis["prediction"])


def render_add_expense_page(username: str, selected_year: int, selected_month: int) -> None:
    """Render the add expense form page."""
    render_page_header("🧾 Add Expense", "Capture expenses for the selected month in a clean, simple form.")
    render_page_quote(PAGE_QUOTES["add_expense"])
    first_day, last_day = get_month_bounds(selected_year, selected_month)
    month_access_state = get_month_access_state(selected_year, selected_month)

    st.caption(f"Expenses added here will belong to {get_month_label(selected_year, selected_month)}.")
    render_month_access_notice(month_access_state)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    with st.form("expense_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            amount = st.text_input(
                "Amount",
                placeholder="Enter amount like 500, 2,500, or 2500.75",
                disabled=month_access_state != "current",
            )
            category = st.selectbox("Category", CATEGORIES, disabled=month_access_state != "current")
        with col2:
            expense_date = st.date_input(
                "Date",
                value=min(date.today(), last_day) if date.today() >= first_day else first_day,
                min_value=first_day,
                max_value=min(date.today(), last_day),
                disabled=month_access_state != "current",
            )
            note = st.text_input("Optional Note", disabled=month_access_state != "current")
        submitted = st.form_submit_button(
            "Add Expense",
            use_container_width=True,
            disabled=month_access_state != "current",
        )

    if submitted and month_access_state == "current":
        try:
            parsed_amount = parse_amount_input(amount)
            add_expense(username, parsed_amount, category, expense_date.isoformat(), note)
            st.success("Expense added successfully.")
        except ValueError as error:
            st.error(str(error))
        except Exception as error:
            st.error(str(error))
    st.markdown("</div>", unsafe_allow_html=True)


def render_view_expenses_page(username: str, selected_year: int, selected_month: int) -> None:
    """Render the monthly expense table with filters."""
    render_page_header("📋 View Expenses", "Review all expenses recorded for the selected month.")
    render_page_quote(PAGE_QUOTES["add_expense"])
    selected_category = render_month_filter_card()
    expenses_df = get_selected_month_expenses(username, selected_year, selected_month, selected_category)

    if expenses_df.empty:
        st.info("No expenses found for the selected month and category.")
        return

    display_df = expenses_df.copy()
    display_df["date"] = pd.to_datetime(display_df["date"]).dt.strftime("%Y-%m-%d")
    display_df["amount"] = display_df["amount"].map(format_currency)
    st.dataframe(display_df[["date", "category", "amount", "note"]], use_container_width=True)


def render_borrowings_page(username: str, selected_year: int, selected_month: int) -> None:
    """Render borrowing entry and history for the selected month."""
    render_page_header(
        "Borrowed Money",
        "Track money borrowed from others, who helped you, and why you needed it.",
    )
    render_page_quote(PAGE_QUOTES["borrowed_money"])
    first_day, last_day = get_month_bounds(selected_year, selected_month)
    month_label = get_month_label(selected_year, selected_month)

    st.caption(f"Borrowing records shown here belong to {month_label}.")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    with st.form("borrowing_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            amount = st.text_input(
                "Borrowed Amount",
                placeholder="Enter amount like 1000 or 15,000",
            )
            lender_name = st.text_input("From Whom", placeholder="Enter lender name")
            purpose = st.text_input("For What Purpose", placeholder="Example: Rent, fees, emergency")
        with col2:
            borrowing_date = st.date_input(
                "Borrowing Date",
                value=min(date.today(), last_day) if date.today() >= first_day else first_day,
                min_value=first_day,
                max_value=min(date.today(), last_day),
            )
            note = st.text_input("Optional Note", placeholder="Any extra detail")
        submitted = st.form_submit_button("Save Borrowing", use_container_width=True)

    if submitted:
        try:
            parsed_amount = parse_amount_input(amount)
            if not lender_name.strip():
                raise ValueError("Please enter the lender name.")
            if not purpose.strip():
                raise ValueError("Please enter the purpose of borrowing.")
            add_borrowing(
                username,
                parsed_amount,
                lender_name,
                purpose,
                borrowing_date.isoformat(),
                note,
            )
            st.success("Borrowing record saved successfully.")
        except ValueError as error:
            st.error(str(error))
        except Exception as error:
            st.error(str(error))
    st.markdown("</div>", unsafe_allow_html=True)

    borrowings_df = get_borrowings(
        username=username,
        start_date=first_day.isoformat(),
        end_date=last_day.isoformat(),
    )

    st.subheader("Borrowing Summary")
    total_borrowed = float(borrowings_df["amount"].sum()) if not borrowings_df.empty else 0.0
    summary_col1, summary_col2 = st.columns(2, gap="large")
    with summary_col1:
        render_metric_card("Total Borrowed", format_currency(total_borrowed), "#b45309")
    with summary_col2:
        render_metric_card("Entries This Month", str(len(borrowings_df)))

    st.subheader("Borrowing Records")
    if borrowings_df.empty:
        st.info("No borrowing records found for this month.")
        return

    display_df = borrowings_df.copy()
    display_df["date"] = pd.to_datetime(display_df["date"]).dt.strftime("%Y-%m-%d")
    display_df["amount"] = display_df["amount"].map(format_currency)
    st.dataframe(
        display_df[["date", "lender_name", "purpose", "amount", "note"]],
        use_container_width=True,
    )


def render_insights_page(username: str, selected_year: int, selected_month: int) -> None:
    """Render human-friendly monthly suggestions."""
    render_page_header("🧠 Monthly Insights", "Friendly guidance based on your spending behavior this month.")
    render_page_quote(PAGE_QUOTES["insights"])
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
    
    # Quick borrowing warning
    first_day, last_day = get_month_bounds(selected_year, selected_month)
    borrowings_df = get_borrowings(username, first_day.isoformat(), last_day.isoformat())
    if not borrowings_df.empty:
        st.warning("💳 Borrowing detected this month. Try reducing expenses.")

    for insight in analysis["insights"]:
        st.info(insight)
    st.success(analysis["prediction"])

    # --- Borrowing Analysis Section ---
    st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)
    st.subheader("💳 Borrowing Analysis")
    
    first_day, last_day = get_month_bounds(selected_year, selected_month)
    borrowings_df = get_borrowings(username, first_day.isoformat(), last_day.isoformat())
    
    total_borrowed = float(borrowings_df["amount"].sum()) if not borrowings_df.empty else 0.0
    borrowing_count = len(borrowings_df)

    # Fetch previous month data for comparison
    prev_month = selected_month - 1 if selected_month > 1 else 12
    prev_year = selected_year if selected_month > 1 else selected_year - 1
    p_first, p_last = get_month_bounds(prev_year, prev_month)
    prev_borrowings_df = get_borrowings(username, p_first.isoformat(), p_last.isoformat())
    prev_total_borrowed = float(prev_borrowings_df["amount"].sum()) if not prev_borrowings_df.empty else 0.0

    sum_col1, sum_col2 = st.columns(2)
    with sum_col1:
        render_metric_card("Total Borrowed", format_currency(total_borrowed), "#b45309")
    with sum_col2:
        render_metric_card("Number of Borrowings", str(borrowing_count))

    if total_borrowed > 0:
        st.warning(f"⚠️ You borrowed {format_currency(total_borrowed)} this month")
        st.info("💡 Try reducing high-spending categories to avoid borrowing")
        
        # Only show increase if previous month had borrowing
        if prev_total_borrowed > 0 and total_borrowed > prev_total_borrowed:
            st.error("📈 Your borrowing has increased compared to last month")
        
        if budget_amount and summary["total_spent"] > budget_amount:
            st.warning("⚠️ You started borrowing after exceeding your budget")


def render_yearly_dashboard_page(username: str, selected_year: int) -> None:
    """Render read-only yearly dashboard with insights-focused summaries."""
    render_page_header("📅 Yearly Dashboard", "Year-to-date spending overview with read-only insights.")
    st.caption(f"Showing aggregated data for {selected_year} (up to today where applicable).")
    st.info("Yearly View is read-only. Adding or editing is not available here.")

    selected_category = render_month_filter_card()
    yearly_df = get_selected_year_expenses(username, selected_year, selected_category)
    summary = calculate_summary(yearly_df, None)

    col1, col2 = st.columns(2, gap="large")
    with col1:
        render_metric_card("Total Spending (Year)", format_currency(summary["total_spent"]))
    with col2:
        render_metric_card("Transactions", str(len(yearly_df)))

    if yearly_df.empty:
        st.info("No expenses available for this year-to-date range.")
        return

    trend_df = yearly_df.copy()
    trend_df["date"] = pd.to_datetime(trend_df["date"])
    trend_df["month"] = trend_df["date"].dt.strftime("%Y-%m")
    monthly_trend = trend_df.groupby("month", as_index=False)["amount"].sum()

    chart_col1, chart_col2 = st.columns(2, gap="large")
    with chart_col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("🥧 Category Breakdown (Year)")
        st.pyplot(create_pie_chart(category_breakdown(yearly_df)), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with chart_col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📈 Monthly Trend")
        st.pyplot(create_line_chart(monthly_trend), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)


def render_yearly_view_expenses_page(username: str, selected_year: int) -> None:
    """Render read-only expense table for year-to-date data."""
    render_page_header("📋 Yearly Expenses", "Review year-to-date expenses in read-only mode.")
    st.info("Yearly View is read-only. You can only analyze past and current data.")
    selected_category = render_month_filter_card()
    expenses_df = get_selected_year_expenses(username, selected_year, selected_category)

    if expenses_df.empty:
        st.info("No expenses found for the selected year range.")
        return

    display_df = expenses_df.copy()
    display_df["date"] = pd.to_datetime(display_df["date"]).dt.strftime("%Y-%m-%d")
    display_df["amount"] = display_df["amount"].map(format_currency)
    st.dataframe(display_df[["date", "category", "amount", "note"]], use_container_width=True)


def render_yearly_insights_page(username: str, selected_year: int) -> None:
    """Render yearly insights with total, category mix, and monthly trend."""
    render_page_header("🧠 Yearly Insights", "Read-only yearly analysis from January up to the allowed date.")
    render_page_quote(PAGE_QUOTES["insights"])
    st.info("Yearly View is read-only. This section is focused on insights only.")

    yearly_df = get_selected_year_expenses(username, selected_year)
    summary = calculate_summary(yearly_df, None)

    metric_col1, metric_col2 = st.columns(2, gap="large")
    with metric_col1:
        render_metric_card("Total Spending in Year", format_currency(summary["total_spent"]))
    with metric_col2:
        top_category = "N/A"
        if not yearly_df.empty:
            top_category = category_breakdown(yearly_df).sort_values("amount", ascending=False).iloc[0]["category"]
        render_metric_card("Top Category", str(top_category))

    if yearly_df.empty:
        st.info("No expenses available for yearly insights in this time range.")
        return

    category_totals = category_breakdown(yearly_df)
    trend_df = yearly_df.copy()
    trend_df["date"] = pd.to_datetime(trend_df["date"])
    trend_df["month"] = trend_df["date"].dt.strftime("%Y-%m")
    monthly_trend = trend_df.groupby("month", as_index=False)["amount"].sum()

    chart_col1, chart_col2 = st.columns(2, gap="large")
    with chart_col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📊 Category-wise Breakdown")
        st.pyplot(create_pie_chart(category_totals), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with chart_col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📈 Monthly Spending Trend")
        st.pyplot(create_line_chart(monthly_trend), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)


def main() -> None:
    """Application entry point."""
    init_db()
    apply_custom_styles()
    ensure_session_state()
    restore_login_from_query_params()

    if not st.session_state.logged_in:
        render_auth_screen()
        return

    username = st.session_state.username
    page, selected_month, selected_year, view_mode = render_sidebar(username)

    if view_mode == "Yearly View":
        if page == "Dashboard":
            render_yearly_dashboard_page(username, selected_year)
        elif page == "View Expenses":
            render_yearly_view_expenses_page(username, selected_year)
        else:
            render_yearly_insights_page(username, selected_year)
    else:
        if page == "Dashboard":
            render_dashboard_page(username, selected_year, selected_month)
        elif page == "Add Expense":
            render_add_expense_page(username, selected_year, selected_month)
        elif page == "View Expenses":
            render_view_expenses_page(username, selected_year, selected_month)
        elif page == "Borrowed Money":
            render_borrowings_page(username, selected_year, selected_month)
        else:
            render_insights_page(username, selected_year, selected_month)


if __name__ == "__main__":
    main()
