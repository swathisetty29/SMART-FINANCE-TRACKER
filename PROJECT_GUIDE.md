# Smart Finance Tracker - Project Guide

This document provides a comprehensive overview of the **Smart Finance Tracker** project, explaining its architecture, file structure, and the technologies used.

---

## 🚀 Overview
The **Smart Finance Tracker** is a premium personal finance management application designed to help users track expenses, budgets, and borrowings with a high-end visual experience. It features an automated dark-mode UI, glassmorphism cards, and dynamic animations.

---

## 🛠️ Technology Stack
- **Python 3.10+**: The core programming language.
- **Streamlit**: The web framework for building the interactive UI.
- **SQLite**: A lightweight, serverless database for storing user accounts and financial data.
- **Pandas**: Used for data manipulation, filtering, and preparing data for charts.
- **Plotly**: Powers the dynamic and interactive line/pie charts.
- **CSS (Vanilla)**: Extensively used to override default Streamlit styles for the "Premium Dark" aesthetic.
- **Localtunnel**: Used to expose the local server to the external web.

---

## 📁 File Structure & Responsibilities

### 1. `app.py` (The Heart of the Application)
- **Role**: Main entry point and UI controller.
- **Key Functions**:
    - `apply_custom_styles()`: Injects custom CSS for dark mode, glassmorphism, and falling coins.
    - `render_sidebar()`: Manages navigation and month/year selection.
    - `render_auth_screen()`: Handles Login/Registration UI.
    - `render_dashboard_page()`: Compiles the main overview with metrics and charts.
- **Rules**: Prevents future-dated entries relative to current today.

### 2. `database.py` (The Data Backbone)
- **Role**: Handles all interactions with the SQLite database (`finance.db`).
- **Key Responsibilities**:
    - Initializing tables (`init_db`).
    - User authentication and session management.
    - CRUD operations for expenses, budgets, and borrowings.
    - Secure password hashing.

### 3. `analytics.py` (The Logic Engine)
- **Role**: Performs calculations and generates visualizations.
- **Key Responsibilities**:
    - Categorizing and summing expenses.
    - Creating Plotly charts (Pie charts for breakdown, Line charts for daily spending).
    - Summarizing monthly vs. daily averages.

### 4. `insights.py` (Financial Intelligence)
- **Role**: Provides automated analysis of the user's spending habits.
- **Key Responsibilities**:
    - Comparing current spending against the budget.
    - Identifying the highest spending category.
    - Generating motivational or cautionary tips based on spending patterns.

### 5. `.streamlit/config.toml`
- **Role**: Configuration file for Streamlit's server behavior and default theme settings.

### 6. `finance.db`
- **Role**: The actual SQLite database file containing all persistent data.

---

## 🌐 Device Access (WiFi)
Since external tunnel services can be unstable due to local firewalls (like McAfee), the most reliable way to access the app on another device (phone/tablet) is via your **Local Network link**.

**Requirement:** Both devices must be connected to the **SAME WiFi**.

- **Local Machine Link**: `http://localhost:8501`
- **Network Link (for phone/other devices)**: [http://10.2.26.202:8501](http://10.2.26.202:8501)
- **Status**: Stable & Permanent (Recommended)

---

## ☁️ External Access (Internet) 
If you need true external access over the internet, we recommend using a professional tool like **Ngrok** with an account token to bypass firewall restrictions.

---

## 🔒 Security Features
- **Password Protection**: User passwords are encrypted and never stored in plain text.
- **Session Persistence**: Users stay logged in even after a page refresh using session tokens stored in URL parameters.
- **Date Validation**: The app prevents entering "future" expenses, ensuring data integrity.
