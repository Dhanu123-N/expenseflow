import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime
import io

# ---------- DATA STORAGE ----------
DATA_FILE = "expenses.csv"

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

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="ExpenseFlow", page_icon="💰")
st.title("💰 ExpenseFlow")

# ---------- LOAD DATA ----------
df = load_data()

# ---------- SIDEBAR: ADD TRANSACTION ----------
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

# ---------- DARK MODE TOGGLE (NEW) ----------
dark_mode = st.toggle("🌙 Dark Mode", value=False)
if dark_mode:
    st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    </style>
    """, unsafe_allow_html=True)

# ---------- SEARCH BY DESCRIPTION (NEW) ----------
search_term = st.text_input("🔍 Search by description", placeholder="Type keyword...")
if search_term:
    df_filtered = df_filtered[df_filtered["Description"].str.contains(search_term, case=False, na=False)]

# ---------- BUDGET ALERT ----------
st.subheader("💰 Monthly Budget")

if selected_month != "All" and len(df_filtered) > 0:
    monthly_expense = df_filtered[df_filtered["Type"] == "Expense"]["Amount"].sum()
    default_budget = 20000
    budget = st.number_input("Set your monthly budget (₹)", min_value=0, value=default_budget, step=1000)
    
    if budget > 0:
        percent_spent = (monthly_expense / budget) * 100
        st.write(f"**Spent:** ₹{monthly_expense:,.2f} of ₹{budget:,.2f} ({percent_spent:.1f}%)")
        st.progress(min(percent_spent / 100, 1.0))
        
        if percent_spent >= 100:
            st.error(f"⚠️ Alert! You've exceeded your budget by ₹{monthly_expense - budget:,.2f}!")
        elif percent_spent >= 80:
            st.warning(f"⚠️ Warning! You've used {percent_spent:.1f}% of your budget.")
        else:
            st.success(f"✅ You're on track! {percent_spent:.1f}% used.")
    else:
        st.info("Budget is zero. Set a positive budget to track.")
else:
    if len(df_filtered) == 0:
        st.info("No data for this month. Add expenses to see budget tracking.")
    else:
        st.info("Select a specific month (not 'All') to set a budget.")

# ---------- METRICS ----------
if len(df_filtered) > 0:
    total_income = df_filtered[df_filtered["Type"] == "Income"]["Amount"].sum()
    total_expense = df_filtered[df_filtered["Type"] == "Expense"]["Amount"].sum()
    remaining = total_income - total_expense
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Income", f"₹{total_income:,.2f}")
    col2.metric("Total Expense", f"₹{total_expense:,.2f}")
    col3.metric("Remaining Balance", f"₹{remaining:,.2f}")
    
    # ---------- SPENDING TREND LINE CHART ----------
    st.subheader("📈 Spending Trend Over Months")
    if len(df) > 0:
        trend_df = df[df["Type"] == "Expense"].copy()
        if len(trend_df) > 0:
            monthly_expenses = trend_df.groupby("YearMonth")["Amount"].sum().reset_index()
            monthly_expenses["sort_key"] = monthly_expenses["YearMonth"].apply(lambda x: datetime.strptime(x, "%B %Y"))
            monthly_expenses = monthly_expenses.sort_values("sort_key")
            
            fig_line = px.line(monthly_expenses, x="YearMonth", y="Amount", 
                               title="Monthly Expenses Trend",
                               labels={"Amount": "Expense (₹)", "YearMonth": "Month"})
            fig_line.update_traces(mode="lines+markers", marker=dict(size=8))
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("No expense data available for trend chart.")
    else:
        st.info("Add some expenses to see spending trends.")
    
    # ---------- PIE CHART ----------
    st.subheader("🥧 Expenses by Category")
    expense_df = df_filtered[df_filtered["Type"] == "Expense"]
    if len(expense_df) > 0:
        fig_pie = px.pie(expense_df, values="Amount", names="Category", title="Spending Breakdown")
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No expenses recorded in this period.")
    
    # ---------- DATA TABLE WITH DELETE CHECKBOXES ----------
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
            st.success("Selected rows deleted!")
            st.rerun()
        else:
            st.warning("No rows selected for deletion.")
    
    # ---------- EXPORT TO EXCEL ----------
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
        file_name=f"expenseflow_export_{date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("No transactions for the selected month. Try adding some or change filter.")

st.caption("💡 Tip: Select a specific month to set a budget. Use dark mode for night viewing. Search by description to find transactions.")