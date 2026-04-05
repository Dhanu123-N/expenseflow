import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime
import io
import os
import json
import hashlib

# ---------- USER MANAGEMENT ----------
USERS_FILE = "users.json"

# Helper: hash password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Load users from JSON file
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

# Save users to JSON file
def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

# Initialize users file if empty
users = load_users()
if not users:
    # Create a default admin user (optional)
    users["admin"] = hash_password("admin")
    save_users(users)

# ---------- SESSION STATE ----------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None

# ---------- LOGIN / REGISTER / PROFILE ----------
def show_login():
    st.title("🔐 ExpenseFlow Login")
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            if submitted:
                users = load_users()
                if username in users and users[username] == hash_password(password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("Invalid username or password")
    
    with tab2:
        with st.form("register_form"):
            new_user = st.text_input("Choose username")
            new_pass = st.text_input("Choose password", type="password")
            confirm_pass = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button("Register")
            if submitted:
                users = load_users()
                if not new_user or not new_pass:
                    st.error("Username and password required")
                elif new_user in users:
                    st.error("Username already exists")
                elif new_pass != confirm_pass:
                    st.error("Passwords do not match")
                else:
                    users[new_user] = hash_password(new_pass)
                    save_users(users)
                    st.success("Registration successful! Please login.")
    
    st.stop()

def show_profile():
    with st.sidebar:
        st.write(f"👤 Logged in as: **{st.session_state.username}**")
        with st.expander("⚙️ Profile Settings"):
            tab_change = st.radio("What would you like to change?", ["Change Username", "Change Password"])
            
            if tab_change == "Change Username":
                new_username = st.text_input("New username")
                if st.button("Update Username"):
                    if new_username and new_username != st.session_state.username:
                        users = load_users()
                        if new_username in users:
                            st.error("Username already taken")
                        else:
                            # Update username in users dict
                            password_hash = users.pop(st.session_state.username)
                            users[new_username] = password_hash
                            save_users(users)
                            # Rename user's data file
                            old_file = f"expenses_{st.session_state.username}.csv"
                            new_file = f"expenses_{new_username}.csv"
                            if os.path.exists(old_file):
                                os.rename(old_file, new_file)
                            st.session_state.username = new_username
                            st.success("Username changed! Please login again.")
                            st.session_state.logged_in = False
                            st.rerun()
                    else:
                        st.warning("Enter a valid username")
            
            else:  # Change Password
                old_pass = st.text_input("Current password", type="password")
                new_pass = st.text_input("New password", type="password")
                confirm_pass = st.text_input("Confirm new password", type="password")
                if st.button("Update Password"):
                    users = load_users()
                    if users.get(st.session_state.username) != hash_password(old_pass):
                        st.error("Current password is incorrect")
                    elif new_pass != confirm_pass:
                        st.error("New passwords do not match")
                    elif len(new_pass) < 3:
                        st.warning("Password too short (min 3 characters)")
                    else:
                        users[st.session_state.username] = hash_password(new_pass)
                        save_users(users)
                        st.success("Password changed! Please login again.")
                        st.session_state.logged_in = False
                        st.rerun()
        
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.rerun()

# ---------- DATA STORAGE (User-specific) ----------
def get_user_data_file():
    return f"expenses_{st.session_state.username}.csv"

DATA_FILE = get_user_data_file()

def load_data():
    try:
        df = pd.read_csv(DATA_FILE)
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"])
    except FileNotFoundError:
        df = pd.DataFrame(columns=["Date", "Category", "Amount", "Type", "Description"])
        df.to_csv(DATA_FILE, index=False)
    return df

def save_data(df):
    if "YearMonth" in df.columns:
        df = df.drop(columns=["YearMonth"])
    df.to_csv(DATA_FILE, index=False)

# ---------- MAIN APP ----------
if not st.session_state.logged_in:
    show_login()

# If we reach here, user is logged in
show_profile()

st.set_page_config(page_title=f"ExpenseFlow - {st.session_state.username}", page_icon="💰")
st.title(f"💰 ExpenseFlow – Welcome {st.session_state.username}")

df = load_data()

# ---------- SIDEBAR: ADD TRANSACTION & AI CHATBOT ----------
with st.sidebar:
    st.header("➕ Add Transaction")
    trans_date = st.date_input("Date", value=date.today())
    trans_type = st.radio("Type", ["Income", "Expense"])
    
    if trans_type == "Income":
        category = st.selectbox("Category", ["Salary", "Freelance", "Gift", "Other Income"])
    else:
        category = st.selectbox("Category", ["Food", "Transport", "Entertainment", "Bills", "Shopping", "Other Expense"])
    
    amount = st.number_input("Amount (₹)", min_value=0.0, step=10.0)
    description = st.text_input("Description (optional)")
    
    if st.button("Add Transaction"):
        new_row = pd.DataFrame([{
            "Date": pd.to_datetime(trans_date),
            "Category": category,
            "Amount": amount,
            "Type": trans_type,
            "Description": description
        }])
        df = pd.concat([df, new_row], ignore_index=True)
        save_data(df)
        st.success("Transaction added!")
        st.rerun()

    # ---------- AI CHATBOT ----------
    st.divider()
    st.header("🤖 AI Assistant")
    st.write("Ask me anything about ExpenseFlow or personal finance!")
    
    # Initialize chat history in session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # Display chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    
    # Chat input
    user_question = st.chat_input("Type your question...")
    
    if user_question:
        # Add user message to history
        st.session_state.chat_history.append({"role": "user", "content": user_question})
        with st.chat_message("user"):
            st.write(user_question)
        
        # Generate AI response
        with st.chat_message("assistant"):
            try:
                import google.generativeai as genai
                # Try to get API key from Streamlit secrets first
                api_key = st.secrets.get("GEMINI_API_KEY", None)
                if api_key is None:
                    # For local testing: ask user to enter key (only once per session)
                    if "gemini_key_input" not in st.session_state:
                        api_key = st.text_input("Enter your Gemini API key:", type="password", key="temp_key")
                        if api_key:
                            st.session_state.gemini_key_input = api_key
                            st.rerun()
                        else:
                            st.warning("Please enter your Gemini API key to use the chatbot.")
                            response_text = "⚠️ API key missing. Please add your Gemini API key in the sidebar."
                    else:
                        api_key = st.session_state.gemini_key_input
                
                if api_key:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    prompt = f"You are a helpful assistant for a personal finance app called ExpenseFlow. Answer the user's question concisely and helpfully.\n\nUser question: {user_question}"
                    response = model.generate_content(prompt)
                    response_text = response.text
                else:
                    response_text = "⚠️ API key not provided. Please enter your Gemini API key to use the chatbot."
            except Exception as e:
                response_text = f"Sorry, I encountered an error: {str(e)}"
            
            st.write(response_text)
            st.session_state.chat_history.append({"role": "assistant", "content": response_text})

# ---------- PREPARE MONTHLY DATA ----------
if len(df) > 0:
    df["YearMonth"] = df["Date"].dt.strftime("%B %Y")
    df = df.dropna(subset=["YearMonth"])
    unique_months = df["YearMonth"].unique()
    valid_months = [m for m in unique_months if isinstance(m, str)]
    months = sorted(valid_months, key=lambda x: datetime.strptime(x, "%B %Y"))
else:
    months = []
    df = pd.DataFrame(columns=["Date", "Category", "Amount", "Type", "Description"])

# ---------- FILTER BY MONTH ----------
st.subheader("📅 Filter by Month")
selected_month = st.selectbox("Select Month", ["All"] + months) if months else "All"

if selected_month != "All" and len(df) > 0:
    df_filtered = df[df["YearMonth"] == selected_month].copy()
else:
    df_filtered = df.copy()

# ---------- DARK MODE ----------
dark_mode = st.toggle("🌙 Dark Mode", value=False)
if dark_mode:
    st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    </style>
    """, unsafe_allow_html=True)

# ---------- SEARCH ----------
search_term = st.text_input("🔍 Search by description", placeholder="Type keyword...")
if search_term:
    df_filtered = df_filtered[df_filtered["Description"].str.contains(search_term, case=False, na=False)]

# ---------- BUDGET ALERT ----------
st.subheader("💰 Monthly Budget")
if selected_month != "All" and len(df_filtered) > 0:
    monthly_expense = df_filtered[df_filtered["Type"] == "Expense"]["Amount"].sum()
    budget = st.number_input("Set your monthly budget (₹)", min_value=0, value=20000, step=1000)
    if budget > 0:
        percent_spent = (monthly_expense / budget) * 100
        st.write(f"**Spent:** ₹{monthly_expense:,.2f} of ₹{budget:,.2f} ({percent_spent:.1f}%)")
        st.progress(min(percent_spent / 100, 1.0))
        if percent_spent >= 100:
            st.error(f"⚠️ Exceeded budget by ₹{monthly_expense - budget:,.2f}!")
        elif percent_spent >= 80:
            st.warning(f"⚠️ Warning! Used {percent_spent:.1f}% of budget.")
        else:
            st.success(f"✅ On track! {percent_spent:.1f}% used.")
    else:
        st.info("Budget is zero.")
else:
    st.info("Select a specific month to set a budget.")

# ---------- METRICS ----------
if len(df_filtered) > 0:
    total_income = df_filtered[df_filtered["Type"] == "Income"]["Amount"].sum()
    total_expense = df_filtered[df_filtered["Type"] == "Expense"]["Amount"].sum()
    remaining = total_income - total_expense
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Income", f"₹{total_income:,.2f}")
    col2.metric("Total Expense", f"₹{total_expense:,.2f}")
    col3.metric("Remaining Balance", f"₹{remaining:,.2f}")

    # ---------- SPENDING TREND ----------
    st.subheader("📈 Spending Trend Over Months")
    if len(df) > 0:
        trend_df = df[df["Type"] == "Expense"].copy()
        if len(trend_df) > 0:
            monthly_expenses = trend_df.groupby("YearMonth")["Amount"].sum().reset_index()
            monthly_expenses["sort_key"] = monthly_expenses["YearMonth"].apply(lambda x: datetime.strptime(x, "%B %Y"))
            monthly_expenses = monthly_expenses.sort_values("sort_key")
            fig_line = px.line(monthly_expenses, x="YearMonth", y="Amount", title="Monthly Expenses Trend")
            fig_line.update_traces(mode="lines+markers", marker=dict(size=8))
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("No expense data for trend.")
    else:
        st.info("Add expenses to see trends.")

    # ---------- PIE CHART ----------
    st.subheader("🥧 Expenses by Category")
    expense_df = df_filtered[df_filtered["Type"] == "Expense"]
    if len(expense_df) > 0:
        fig_pie = px.pie(expense_df, values="Amount", names="Category", title="Spending Breakdown")
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No expenses recorded this period.")

    # ---------- TABLE & DELETE ----------
    st.subheader("📋 All Transactions")
    display_df = df_filtered.copy()
    display_df["Select"] = False
    edited_df = st.data_editor(
        display_df,
        column_config={
            "Select": st.column_config.CheckboxColumn("Delete?", default=False),
            "Date": st.column_config.DateColumn("Date"),
            "Amount": st.column_config.NumberColumn("Amount (₹)", format="₹%.2f"),
        },
        disabled=["Date", "Category", "Amount", "Type", "Description", "YearMonth"],
        hide_index=True,
        use_container_width=True
    )
    if st.button("🗑️ Delete Selected Rows"):
        selected_indices = edited_df[edited_df["Select"]].index
        if len(selected_indices) > 0:
            df_filtered = df_filtered.drop(selected_indices).reset_index(drop=True)
            other_months = df[~df["YearMonth"].isin([selected_month])] if selected_month != "All" else pd.DataFrame()
            df = pd.concat([other_months, df_filtered], ignore_index=True)
            if "YearMonth" in df.columns:
                df = df.drop(columns=["YearMonth"])
            save_data(df)
            st.success("Deleted!")
            st.rerun()
        else:
            st.warning("No rows selected.")

    # ---------- EXPORT EXCEL ----------
    st.subheader("📎 Export Data")
    export_df = df.copy()
    if "YearMonth" in export_df.columns:
        export_df = export_df.drop(columns=["YearMonth"])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        export_df.to_excel(writer, sheet_name="Expenses", index=False)
    excel_data = output.getvalue()
    st.download_button(
        label="📥 Download All Data as Excel",
        data=excel_data,
        file_name=f"expenseflow_{st.session_state.username}_{date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("No transactions for this period. Add some using the sidebar.")

st.caption("💡 Tip: Use the Profile Settings in the sidebar to change username or password anytime.")