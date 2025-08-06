import streamlit as st
import pandas as pd
import numpy as np
import time
import bcrypt
import matplotlib.pyplot as plt
import gspread
from google.oauth2.service_account import Credentials

# Streamlit App Configuration
st.set_page_config(page_title="Google Sheets Dashboard", layout="wide")


# Load Google Sheet IDs securely
AUTH_SHEET_ID = st.secrets["sheets"]["AUTH_SHEET_ID"]
COLLECTION_SHEET_ID = st.secrets["sheets"]["COLLECTION_SHEET_ID"]
EXPENSE_SHEET_ID = st.secrets["sheets"]["EXPENSE_SHEET_ID"]
INVESTMENT_SHEET_ID = st.secrets["sheets"]["INVESTMENT_SHEET_ID"]
BANK_SHEET_ID = st.secrets["sheets"]["BANK_SHEET_ID"]


# Authentication Google Sheets Details

AUTH_SHEET_NAME = "Sheet1"


# --- DATA LOADING ---
COLLECTION_SHEET_NAME = "collection"
COLLECTION_CSV_URL = f"https://docs.google.com/spreadsheets/d/{COLLECTION_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={COLLECTION_SHEET_NAME}"

# --- EXPENSE DATA ---

EXPENSE_SHEET_NAME = "expense"
EXPENSE_CSV_URL = f"https://docs.google.com/spreadsheets/d/{EXPENSE_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={EXPENSE_SHEET_NAME}"

# --- INVESTMENT DATA ---

INVESTMENT_SHEET_NAME = "Investment_Details"
INVESTMENT_CSV_URL = f"https://docs.google.com/spreadsheets/d/{INVESTMENT_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={INVESTMENT_SHEET_NAME}"


# --- Bank DATA ---

BANK_SHEET_NAME = "Bank_Transaction"
BANK_CSV_URL = f"https://docs.google.com/spreadsheets/d/{BANK_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={BANK_SHEET_NAME}"

# ✅ Load credentials from Streamlit Secrets (Create a Copy)
creds_dict = dict(st.secrets["gcp_service_account"])  # Create a mutable copy

# ✅ Fix private key formatting
creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

# ✅ Function to Connect to Google Sheets (with Caching)
@st.cache_resource  # Cache for 5 minutes
def connect_to_sheets():
    try:
        creds = Credentials.from_service_account_info(
            creds_dict, 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        client = gspread.authorize(creds)
        
        # Open sheets once and reuse them
        AUTH_sheet = client.open_by_key(st.secrets["sheets"]["AUTH_SHEET_ID"]).worksheet(AUTH_SHEET_NAME)
        COLLECTION_sheet = client.open_by_key(st.secrets["sheets"]["COLLECTION_SHEET_ID"]).worksheet(COLLECTION_SHEET_NAME)
        EXPENSE_sheet = client.open_by_key(st.secrets["sheets"]["EXPENSE_SHEET_ID"]).worksheet(EXPENSE_SHEET_NAME)
        INVESTMENT_sheet = client.open_by_key(st.secrets["sheets"]["INVESTMENT_SHEET_ID"]).worksheet(INVESTMENT_SHEET_NAME)
        BANK_sheet = client.open_by_key(st.secrets["sheets"]["BANK_SHEET_ID"]).worksheet(BANK_SHEET_NAME)
        
        return AUTH_sheet, COLLECTION_sheet, EXPENSE_sheet, INVESTMENT_sheet , BANK_sheet

    except Exception as e:
        st.error(f"❌ Failed to connect to Google Sheets: {e}")
        st.stop()




# ✅ Get cached sheets
AUTH_sheet, COLLECTION_sheet, EXPENSE_sheet, INVESTMENT_sheet ,BANK_sheet= connect_to_sheets()

# Function to load authentication data securely
@st.cache_resource # Cache for 5 minutes
def load_auth_data():
    data = AUTH_sheet.get_all_records()
    df = pd.DataFrame(data)
    return df

# Load authentication data
auth_df = load_auth_data()

# Function to Verify Password
def verify_password(stored_hash, entered_password):
    return bcrypt.checkpw(entered_password.encode(), stored_hash.encode())

# Initialize Session State for Authentication
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_role = None
    st.session_state.username = None
    st.session_state.user_name = None

# --- LOGIN PAGE ---
if not st.session_state.authenticated:
    st.title("🔒 Secure Login")
    username = st.text_input("👤 Username")
    password = st.text_input("🔑 Password", type="password")
    login_button = st.button("Login")

    if login_button:
        user_data = auth_df[auth_df["Username"] == username]

        if not user_data.empty:
            stored_hash = user_data.iloc[0]["Password"]
            role = user_data.iloc[0]["Role"]
            name = user_data.iloc[0]["Name"]

            if verify_password(stored_hash, password):
                st.session_state.authenticated = True
                st.session_state.user_role = role
                st.session_state.username = username
                st.session_state.user_name = name
                st.experimental_set_query_params(logged_in="true")

                st.success(f"✅ Welcome, {name}!")
                st.rerun()
            else:
                st.error("❌ Invalid Credentials")
        else:
            st.error("❌ User not found")

# --- LOGGED-IN USER SEES DASHBOARD ---
else:
    if st.sidebar.button("🚪 Logout"):
        st.session_state.authenticated = False
        st.session_state.user_role = None
        st.session_state.username = None
        st.session_state.user_name = None
        st.experimental_set_query_params(logged_in="false")
        st.rerun()

    st.sidebar.write(f"👤 **Welcome, {st.session_state.user_name}!**")

    @st.cache_resource # Cache for 5 minutes
    def load_data(url):
        df = pd.read_csv(url, dayfirst=True, dtype={"Vehicle No": str})  # Ensure Vehicle No remains a string
        
        df['Collection Date'] = pd.to_datetime(df['Collection Date'], dayfirst=True, errors='coerce').dt.date
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
        df['Meter Reading'] = pd.to_numeric(df['Meter Reading'], errors='coerce')

        # Assuming df is your DataFrame and it's already sorted by 'Collection Date'
        df = df.sort_values(by=['Vehicle No', 'Collection Date'])

        # Calculate distance for each vehicle separately
        df['Distance'] = df.groupby('Vehicle No')['Meter Reading'].diff().fillna(0)

        # Replace negative distances with the average of positive distances
        positive_avg_distance = df[df['Distance'] > 0]['Distance'].mean()
        df.loc[df['Distance'] < 0, 'Distance'] = np.round(positive_avg_distance)

        # Month-Year Column
        df['Month-Year'] = pd.to_datetime(df['Collection Date']).dt.strftime('%Y-%m')

        return df[['Collection Date', 'Vehicle No', 'Amount', 'Meter Reading', 'Name', 'Distance', 'Month-Year','Received By']]

    @st.cache_resource  # Cache for 5 minutes
    def load_expense_data(url):
        df = pd.read_csv(url, dayfirst=True, dtype={"Vehicle No": str})  # Ensure Vehicle No remains a string
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce').dt.date
        df['Amount Used'] = pd.to_numeric(df['Amount Used'], errors='coerce')
        df['Month-Year'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m')
        return df[['Date', 'Vehicle No', 'Reason of Expense', 'Amount Used', 'Any Bill', 'Month-Year','Expense By']]
    
    @st.cache_resource  # Cache for 5 minutes    
    def load_investment_data(url):
        df = pd.read_csv(url, dayfirst=True)

        # Strip spaces from column names to avoid formatting issues
        df.columns = df.columns.str.strip()

        # Ensure required columns exist
        required_columns = ["Date", "Investment Type", "Amount", "Comment", "Received From"]
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            st.error(f"❌ Missing columns in Investment Data: {missing_columns}")
            return pd.DataFrame()  # Return empty DataFrame to avoid crashing

        # Rename columns for consistency
        df.rename(columns={"Amount": "Investment Amount", "Received From": "Investor Name"}, inplace=True)

        # Convert data types
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce').dt.date
        df['Investment Amount'] = pd.to_numeric(df['Investment Amount'], errors='coerce')
        df['Month-Year'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m')

        return df[['Date', 'Investment Type', 'Investment Amount', 'Comment', 'Investor Name', 'Month-Year']]

    @st.cache_resource
    def load_bank_data(url):
        df = pd.read_csv(url, dayfirst=True)
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce').dt.date
        df['Month-Year'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m')
        return df

    


    df = load_data(COLLECTION_CSV_URL)
    expense_df = load_expense_data(EXPENSE_CSV_URL)
    investment_df = load_investment_data(INVESTMENT_CSV_URL)
    bank_df = load_bank_data(BANK_CSV_URL)


    # Calculate credits and debits
    # Ensure Amount is numeric
    bank_df['Amount'] = pd.to_numeric(bank_df['Amount'], errors='coerce').fillna(0)

    # Calculate total credits and debits
    Collection_Credit_Bank=bank_df[bank_df['Transaction Type'].isin(['Collection_Credit'])]['Amount'].sum()
    Investment_Credit_Bank=bank_df[bank_df['Transaction Type'].isin(['Investment_Credit'])]['Amount'].sum()
    Payment_Credit_Bank=bank_df[bank_df['Transaction Type'].isin(['Payment_Credit'])]['Amount'].sum()
    total_credits = Collection_Credit_Bank+Investment_Credit_Bank+Payment_Credit_Bank

    Expence_Debit_Bank=bank_df[bank_df['Transaction Type'].isin(['Expence_Debit'])]['Amount'].sum()
    Settlement_Debit_Bank=bank_df[bank_df['Transaction Type'].isin(['Settlement_Debit'])]['Amount'].sum()
    total_debits = Expence_Debit_Bank+Settlement_Debit_Bank

    bank_balance = total_credits - total_debits

    # === Individual Summary ===
    # Initialize all required variables
    # For Govind Kumar
    govind_collection_credit = 0
    govind_settlement_credit = 0
    govind_investment_credit = 0
    govind_total_credit = 0
    govind_expense_debit = 0
    govind_settlement_debit = 0
    govind_total_debit = 0

    # For Kumar Gaurav
    gaurav_collection_credit = 0
    gaurav_settlement_credit = 0
    gaurav_investment_credit = 0
    gaurav_total_credit = 0
    gaurav_expense_debit = 0
    gaurav_settlement_debit = 0
    gaurav_total_debit = 0

    # Filter data by person and assign values
    govind_df = bank_df[bank_df['Transaction By'] == 'Govind Kumar']
    gaurav_df = bank_df[bank_df['Transaction By'] == 'Kumar Gaurav']

    # Govind Kumar
    govind_collection_credit = govind_df[govind_df['Transaction Type'] == 'Collection_Credit']['Amount'].sum()
    govind_settlement_credit = govind_df[govind_df['Transaction Type'] == 'Settlement_Credit']['Amount'].sum()
    govind_investment_credit = govind_df[govind_df['Transaction Type'] == 'Investment_Credit']['Amount'].sum()
    govind_total_credit = govind_collection_credit + govind_settlement_credit + govind_investment_credit

    govind_expense_debit = govind_df[govind_df['Transaction Type'] == 'Expence_Debit']['Amount'].sum()
    govind_settlement_debit = govind_df[govind_df['Transaction Type'] == 'Settlement_Debit']['Amount'].sum()
    govind_total_debit = govind_expense_debit + govind_settlement_debit

    # Kumar Gaurav
    gaurav_collection_credit = gaurav_df[gaurav_df['Transaction Type'] == 'Collection_Credit']['Amount'].sum()
    gaurav_settlement_credit = gaurav_df[gaurav_df['Transaction Type'] == 'Settlement_Credit']['Amount'].sum()
    gaurav_investment_credit = gaurav_df[gaurav_df['Transaction Type'] == 'Investment_Credit']['Amount'].sum()
    gaurav_total_credit = gaurav_collection_credit + gaurav_settlement_credit + gaurav_investment_credit

    gaurav_expense_debit = gaurav_df[gaurav_df['Transaction Type'] == 'Expence_Debit']['Amount'].sum()
    gaurav_settlement_debit = gaurav_df[gaurav_df['Transaction Type'] == 'Settlement_Debit']['Amount'].sum()
    gaurav_total_debit = gaurav_expense_debit + gaurav_settlement_debit

    #------------Bank Calculation End-----------------



    #-------------Remaining Balance at you ----------





    #---------------Remaining Balance calculation end------------

    # --- DASHBOARD UI ---
    st.sidebar.header("📂 Navigation")
    page = st.sidebar.radio("Go to:", ["Dashboard", "Monthly Summary", "Grouped Data", "Expenses", "Investment", "Collection Data", "Bank Transaction" ])

    if page == "Dashboard":
        st.title("📊 Orga Yatra Dashboard")
        
        # Get latest month
        last_month = df['Month-Year'].max()

        # Optional: Clean column names in case of leading/trailing spaces
        df.columns = df.columns.str.strip()
        expense_df.columns = expense_df.columns.str.strip()
        investment_df.columns = investment_df.columns.str.strip()
        
        # === Individual Totals (Govind Kumar) ===
        govind_total_collection = df[df['Received By'].isin(['Govind Kumar'])]['Amount'].sum()
        govind_total_investment = investment_df[investment_df['Investor Name'].isin(['Govind Kumar'])]['Investment Amount'].sum()
        govind_total_expense = expense_df[expense_df['Expense By'].isin(['Govind Kumar'])]['Amount Used'].sum()

        govind_last_month_collection = df[(df['Received By'].isin(['Govind Kumar'])) & (df['Month-Year'] == last_month)]['Amount'].sum()
        govind_last_month_expense = expense_df[(expense_df['Expense By'].isin(['Govind Kumar'])) & (expense_df['Month-Year'] == last_month)]['Amount Used'].sum()

        # === Individual Totals (Kumar Gaurav) ===
        gaurav_total_collection = df[df['Received By'].isin(['Kumar Gaurav'])]['Amount'].sum()
        gaurav_total_investment = investment_df[investment_df['Investor Name'].isin(['Kumar Gaurav'])]['Investment Amount'].sum()
        gaurav_total_expense = expense_df[expense_df['Expense By'].isin(['Kumar Gaurav'])]['Amount Used'].sum()

        gaurav_last_month_collection = df[(df['Received By'].isin(['Kumar Gaurav'])) & (df['Month-Year'] == last_month)]['Amount'].sum()
        gaurav_last_month_expense = expense_df[(expense_df['Expense By'].isin(['Kumar Gaurav'])) & (expense_df['Month-Year'] == last_month)]['Amount Used'].sum()

        # === Combined Totals ===
        total_collection = govind_total_collection + gaurav_total_collection
        total_investment = govind_total_investment + gaurav_total_investment + Investment_Credit_Bank
        total_expense = govind_total_expense + gaurav_total_expense

        
        remaining_fund_gaurav= (gaurav_total_collection - gaurav_total_expense - gaurav_collection_credit + gaurav_settlement_debit - gaurav_settlement_credit + gaurav_total_investment)
        remaining_fund_govind= (govind_total_collection - govind_total_expense - govind_collection_credit + govind_settlement_debit - govind_settlement_credit + govind_total_investment)
        Net_balance=remaining_fund_gaurav + remaining_fund_govind + bank_balance

        last_month_collection = govind_last_month_collection + gaurav_last_month_collection
        last_month_expense = govind_last_month_expense + gaurav_last_month_expense

        
        col1, col2, col3, col4, col5,col6,col7 = st.columns(7)
        col1.metric(label="💰 Total Collection", value=f"₹{total_collection:,.2f}")
        col2.metric(label="📉 Total Expenses", value=f"₹{total_expense:,.2f}")
        col3.metric(label="💸 Total Investment", value=f"₹{total_investment:,.2f}")
        col4.metric(label="💵 Govind Balance", value=f"₹{remaining_fund_govind:,.2f}")
        col5.metric(label="💵 Gaurav Balance", value=f"₹{remaining_fund_gaurav:,.2f}")
        col6.metric(label="🏦 Bank Balance", value=f"₹{bank_balance:,.2f}")
        col7.metric(label="🏦 Net Balance", value=f"₹{Net_balance:,.2f}")


        st.markdown("---")
        formatted_last_month = pd.to_datetime(last_month).strftime("%b %Y")  
        st.subheader("📅 "+formatted_last_month+"   Overview")

        col4, col5 = st.columns(2)
        col4.metric(label="📈"+formatted_last_month+"  Collection", value=f"₹{last_month_collection:,.2f}")
        col5.metric(label="📉"+formatted_last_month+" Expenses", value=f"₹{last_month_expense:,.2f}")

        st.markdown("---")
        st.write("### 📈 Collection & Distance Trend")
        st.line_chart(df.set_index("Collection Date")[["Amount", "Distance"]])

        st.write("### 🔍 Recent Collection Data:")
        st.dataframe(df.sort_values(by="Collection Date", ascending=False).head(10))

    elif page == "Monthly Summary":
        st.title("📊 Monthly Summary Report")
    
        # --- Monthly Aggregation ---
        # Govind and Gaurav Collection
        govind_monthly = df[df['Received By'] == 'Govind Kumar'].groupby('Month-Year', as_index=False)['Amount'].sum().rename(columns={"Amount": "Govind Collection"})
        gaurav_monthly = df[df['Received By'] == 'Kumar Gaurav'].groupby('Month-Year', as_index=False)['Amount'].sum().rename(columns={"Amount": "Gaurav Collection"})
    
        # Govind and Gaurav Expenses
        govind_expense_monthly = expense_df[expense_df['Expense By'] == 'Govind Kumar'].groupby('Month-Year', as_index=False)['Amount Used'].sum().rename(columns={"Amount Used": "Govind Expense"})
        gaurav_expense_monthly = expense_df[expense_df['Expense By'] == 'Kumar Gaurav'].groupby('Month-Year', as_index=False)['Amount Used'].sum().rename(columns={"Amount Used": "Gaurav Expense"})
    
        # Merge all
        monthly_summary = pd.merge(govind_monthly, gaurav_monthly, on="Month-Year", how="outer")
        monthly_summary = pd.merge(monthly_summary, govind_expense_monthly, on="Month-Year", how="outer")
        monthly_summary = pd.merge(monthly_summary, gaurav_expense_monthly, on="Month-Year", how="outer")
    
        monthly_summary.fillna(0, inplace=True)
    
        # Total columns
        monthly_summary["Total Collection"] = monthly_summary["Govind Collection"] + monthly_summary["Gaurav Collection"]
        monthly_summary["Total Expense"] = monthly_summary["Govind Expense"] + monthly_summary["Gaurav Expense"]
    
        # Net Balance
        monthly_summary["Net Balance"] = monthly_summary["Total Collection"] - monthly_summary["Total Expense"]
    
        # Percentage Change
        monthly_summary["Collection Change (%)"] = monthly_summary["Total Collection"].pct_change().fillna(0) * 100
        monthly_summary["Expense Change (%)"] = monthly_summary["Total Expense"].pct_change().fillna(0) * 100
    
        # Reorder columns
        ordered_columns = [
            "Month-Year", 
            "Govind Collection", "Gaurav Collection", 
            "Total Collection", "Collection Change (%)", 
            "Govind Expense", "Gaurav Expense", 
            "Total Expense", "Expense Change (%)", 
            "Net Balance"
        ]
        monthly_summary = monthly_summary[ordered_columns]
    
        # === UI ===
        st.subheader("📅 Monthly Breakdown")
        st.dataframe(monthly_summary.style.format({
            "Govind Collection": "₹{:.2f}",
            "Gaurav Collection": "₹{:.2f}",
            "Total Collection": "₹{:.2f}",
            "Collection Change (%)": "{:+.1f}%",
            "Govind Expense": "₹{:.2f}",
            "Gaurav Expense": "₹{:.2f}",
            "Total Expense": "₹{:.2f}",
            "Expense Change (%)": "{:+.1f}%",
            "Net Balance": "₹{:.2f}"
        }), use_container_width=True)
    
        # === Charts ===
        chart_option = st.radio("📊 Show Chart for:", ["Collection vs Expense", "Net Balance Trend"])
        
        if chart_option == "Collection vs Expense":
            chart_df = monthly_summary[["Month-Year", "Total Collection", "Total Expense"]].set_index("Month-Year")
            st.bar_chart(chart_df)
        else:
            net_df = monthly_summary[["Month-Year", "Net Balance"]].set_index("Month-Year")
            st.line_chart(net_df)
    
        # === Download Option ===
        csv = monthly_summary.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Monthly Summary (CSV)", data=csv, file_name="monthly_summary.csv", mime="text/csv")


    elif page == "Grouped Data":
        st.title("🔍 Grouped Collection Data")
    
        group_by = st.sidebar.radio("🔄 Group Data By:", ["Name", "Vehicle No"])
        selected_month = st.sidebar.selectbox("📅 Select Month-Year:", ["All"] + sorted(df['Month-Year'].unique(), reverse=True))
    
        chart_type = st.sidebar.radio("📈 Show Chart For:", ["Amount", "Distance", "Both"])
        top_n = st.sidebar.slider("🔢 Show Top N Groups", min_value=3, max_value=20, value=10)
    
        # Filter by month
        df_filtered = df.copy()
        if selected_month != "All":
            df_filtered = df[df['Month-Year'] == selected_month]
    
        # Grouping logic
        grouped_df = df_filtered.groupby(group_by, as_index=False).agg({
            "Amount": "sum",
            "Distance": "sum",
            "Collection Date": "count"
        }).rename(columns={"Collection Date": "Total Collections"})
    
        # Add averages
        grouped_df["Avg Amount"] = grouped_df["Amount"] / grouped_df["Total Collections"]
        grouped_df["Avg Distance"] = grouped_df["Distance"] / grouped_df["Total Collections"]
    
        # Sort and get top N
        grouped_df = grouped_df.sort_values(by="Amount", ascending=False).head(top_n)
    
        # Display Data
        st.subheader(f"📊 Top {top_n} - Grouped by {group_by}")
        st.dataframe(grouped_df.style.format({
            "Amount": "₹{:.2f}",
            "Distance": "{:.0f} km",
            "Avg Amount": "₹{:.2f}",
            "Avg Distance": "{:.1f} km"
        }), use_container_width=True)
    
        # Download CSV
        csv_grouped = grouped_df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Grouped Data", data=csv_grouped, file_name="grouped_data.csv", mime="text/csv")
    
        # Chart View
        st.subheader("📈 Grouped Chart")
    
        if chart_type == "Amount":
            st.bar_chart(grouped_df.set_index(group_by)["Amount"])
        elif chart_type == "Distance":
            st.bar_chart(grouped_df.set_index(group_by)["Distance"])
        else:
            st.line_chart(grouped_df.set_index(group_by)[["Amount", "Distance"]])
    

    elif page == "Expenses":
        st.title("💸 Expense Insights")

        # ───────────────────────────────────────────────────────────────
        # 🔹 Section 1: Total Expense Summary
        total_manual_expense = expense_df["Amount Used"].sum()
        total_bank_expense = govind_expense_debit + gaurav_expense_debit
        total_expense = total_manual_expense + total_bank_expense
    
        col1, col2, col3 = st.columns(3)
        col1.metric("🧾 Manual Entry Expense (Sheet)", f"₹{total_manual_expense:,.2f}")
        col2.metric("🏦 Bank Debits (Govind + Gaurav)", f"₹{total_bank_expense:,.2f}")
        col3.metric("💰 Total Expense (Combined)", f"₹{total_expense:,.2f}")
    
        st.markdown("---")
    
        # ───────────────────────────────────────────────────────────────
        # 🔹 Section 2: Manually Entered Expenses
        st.subheader("🧾 Manual Expense Summary")
    
        # Monthly manual expenses
        monthly_manual_expense = expense_df.groupby("Month-Year", as_index=False)['Amount Used'].sum()
        st.bar_chart(monthly_manual_expense.set_index("Month-Year"))
    
        with st.expander("🔍 View Bank Expense Transactions"):
            bank_expense_df = bank_df[bank_df['Transaction Type'] == 'Expence_Debit'][['Date', 'Transaction By', 'Amount', 'Reason']]
            st.dataframe(bank_expense_df.sort_values(by="Date", ascending=False))
    
        st.markdown("---")
    
        # ───────────────────────────────────────────────────────────────
        # 🔹 Section 3: Detailed Manual Expense Entries
        st.subheader("📋 Detailed Manual Expense Entries")
        st.dataframe(expense_df.sort_values(by="Date", ascending=False))
    
    
#-----------------------------------------------------

    
    elif page == "Investment":
        st.title("📈 Investment Details")
    
        # --- 1. From Investment Sheet ---
        sheet_total_investment = investment_df["Investment Amount"].sum()
    
        # --- 2. From Bank Transactions ---
        bank_investment_df = bank_df[bank_df["Transaction Type"] == "Investment_Credit"].copy()
    
        # Rename for consistency
        bank_investment_df.rename(columns={
            "Transaction By": "Investor Name",
            "Amount": "Investment Amount",
            "Reason": "Comment"
        }, inplace=True)
    
        # Add source
        investment_df["Source"] = "Manual Sheet"
        bank_investment_df["Source"] = "Bank Transaction"
    
        # Clean and align columns
        investment_df_clean = investment_df[["Date", "Investor Name", "Investment Amount", "Investment Type", "Comment", "Month-Year", "Source"]]
        bank_investment_df_clean = bank_investment_df[["Date", "Investor Name", "Investment Amount", "Comment", "Source"]]
    
        bank_investment_df_clean["Investment Type"] = "Bank Credit"
        bank_investment_df_clean["Month-Year"] = pd.to_datetime(bank_investment_df_clean["Date"]).dt.strftime('%Y-%m')
    
        # Final order of bank data
        bank_investment_df_clean = bank_investment_df_clean[["Date", "Investor Name", "Investment Amount", "Investment Type", "Comment", "Month-Year", "Source"]]
    
        # Combine both
        full_investment_df = pd.concat([investment_df_clean, bank_investment_df_clean], ignore_index=True)
    
        # --- Total Summary ---
        total_combined_investment = full_investment_df["Investment Amount"].sum()
    
        col1, col2, col3 = st.columns(3)
        col1.metric("📄 From Sheet", f"₹{sheet_total_investment:,.2f}")
        col2.metric("🏦 From Bank", f"₹{bank_investment_df['Investment Amount'].sum():,.2f}")
        col3.metric("💰 Total Investment", f"₹{total_combined_investment:,.2f}")
    
        st.markdown("---")
    
        # --- 📊 Split Charts in Equal Bordered Columns ---
        col1, col2 = st.columns(2)
    
        with col1:
            st.markdown("#### 👥 Investment Share (Govind vs Gaurav)")
            pie_df = full_investment_df[full_investment_df["Investor Name"].isin(["Govind Kumar", "Kumar Gaurav"])]
            investor_totals = pie_df.groupby("Investor Name", as_index=False)["Investment Amount"].sum()
    
            if not investor_totals.empty:
                fig1, ax1 = plt.subplots(figsize=(3.5, 3.5))  # Smaller pie
                ax1.pie(
                    investor_totals["Investment Amount"],
                    labels=investor_totals["Investor Name"],
                    autopct='%1.1f%%',
                    startangle=90,
                    colors=plt.cm.Pastel1.colors
                )
                ax1.axis("equal")
                st.pyplot(fig1)
            else:
                st.info("No investment data available for Govind or Gaurav.")
    
        with col2:
            st.markdown("#### 🧾 Manual vs Bank Investment by Investor")
            manual_df = investment_df_clean[investment_df_clean["Investor Name"].isin(["Govind Kumar", "Kumar Gaurav"])]
            bank_df_investor = bank_investment_df_clean[bank_investment_df_clean["Investor Name"].isin(["Govind Kumar", "Kumar Gaurav"])]
    
            manual_summary = manual_df.groupby("Investor Name")["Investment Amount"].sum().rename("Manual Sheet")
            bank_summary = bank_df_investor.groupby("Investor Name")["Investment Amount"].sum().rename("Bank Transaction")
    
            comparison_df = pd.concat([manual_summary, bank_summary], axis=1).fillna(0)
            st.bar_chart(comparison_df)
    
        st.markdown("---")
    
        # --- Detailed View ---
        st.subheader("📋 All Investment Records")
        st.dataframe(full_investment_df.sort_values(by="Date", ascending=False))

    
    elif page == "Collection Data":
        st.title("📊 Collection Data")
    
        # Ensure date column is in datetime format
        df["Collection Date"] = pd.to_datetime(df["Collection Date"])
    
        # Sort by Collection Date descending
        df = df.sort_values("Collection Date", ascending=False)
    
        # Calculate previous amount per vehicle
        df = df.sort_values(["Vehicle No", "Collection Date"])
        df["Previous Amount"] = df.groupby("Vehicle No")["Amount"].shift(1)
        df["Change"] = df["Amount"] - df["Previous Amount"]
    
        # KPIs based on all data
        total_collection = df["Amount"].sum()
        total_vehicles = df["Vehicle No"].nunique()
        best_vehicle = df.groupby("Vehicle No")["Amount"].mean().idxmax()
        worst_vehicle = df.groupby("Vehicle No")["Amount"].mean().idxmin()
    
        # Show KPI Metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("💰 Total Collection", f"₹{total_collection:,.2f}")
        col2.metric("🚐 Total Vehicles", total_vehicles)
        col3.metric("🏆 Best Vehicle", best_vehicle)
        col4.metric("📉 Worst Vehicle", worst_vehicle)
        col5.metric("📄 Total Records", len(df))
    
        st.markdown("---")
    
        # Vehicle filter
        vehicle_list = ["All"] + sorted(df["Vehicle No"].unique())
        selected_vehicle = st.selectbox("🚗 Filter by Vehicle", vehicle_list)
    
        if selected_vehicle != "All":
            filtered_df = df[df["Vehicle No"] == selected_vehicle]
        else:
            filtered_df = df.copy()
    
        # Total collection for selected vehicle
        selected_total = filtered_df["Amount"].sum()
        st.info(f"💰 **Total Collection for {selected_vehicle if selected_vehicle != 'All' else 'All Vehicles'}**: ₹{selected_total:,.2f}")
    
        st.markdown("### 📈 Collection Trend")
    
        # Line chart for all vehicles
        chart_df = df.groupby(["Collection Date", "Vehicle No"])["Amount"].sum().reset_index()
        chart_pivot = chart_df.pivot(index="Collection Date", columns="Vehicle No", values="Amount").fillna(0)
        st.line_chart(chart_pivot)
    
        st.markdown("### 📄 Collection Records")
    
        # Columns to show
        display_cols = ["Collection Date", "Vehicle No", "Amount", "Meter Reading", "Name", "Distance"]
    
        # Round distance
        df["Distance"] = df["Distance"].round(2)
    
        # Styling
        def highlight_amount(val, prev):
            if pd.isna(prev):
                return ""
            elif val > prev:
                return "color: green; font-weight: bold"
            elif val < prev:
                return "color: red; font-weight: bold"
            else:
                return ""
    
        def style_row(row):
            return [
                highlight_amount(row["Amount"], row["Previous Amount"]) if col == "Amount" else ""
                for col in row.index
            ]
    
        # Prepare merged dataframe with Previous Amount (needed for color logic)
        merged_df = filtered_df.copy()
        #styled_df = merged_df[display_cols + ["Previous Amount"]].style.apply(style_row, axis=1)
        styled_df = merged_df.sort_values("Collection Date", ascending=False)[display_cols + ["Previous Amount"]].style.apply(style_row, axis=1)

    
        # Format currency and distance
        styled_df = styled_df.format({
        "Amount": "₹{:,.0f}",
        "Distance": "{:,.0f}",
        "Previous Amount": "{:,.0f}"
    })

    
        # Show styled dataframe
        st.dataframe(styled_df, use_container_width=True)




    elif page == "Bank Transaction":
        st.title("🏦 Bank Transactions")
    
        # Ensure 'Date' is datetime
        bank_df["Date"] = pd.to_datetime(bank_df["Date"], dayfirst=True)
    
        # Normalize whitespace and case
        bank_df["Transaction Type"] = bank_df["Transaction Type"].str.strip()
    
        credit_mask = bank_df["Transaction Type"].str.lower().str.contains("credit")
        debit_mask = bank_df["Transaction Type"].str.lower().str.contains("debit")
        st.write("credit_mask",credit_mask)
        st.write("debit_mask",debit_mask)
        st.write("Columns:", bank_df.columns.tolist())

    
        total_credit = bank_df.loc[credit_mask, "Amount"].sum()
        total_debit = bank_df.loc[debit_mask, "Amount"].sum()
        balance = total_credit - total_debit
    
        # 💰 Current Balance
        st.subheader("💰 Current Bank Balance")
        st.metric(label="Available Balance", value=f"₹ {balance:,.2f}", delta=f"₹ {total_credit - total_debit:,.2f}")
    
        # 📊 Monthly Summary
        st.subheader("📊 Monthly Transaction Summary")
        bank_df["Month"] = bank_df["Date"].dt.strftime("%B %Y")
    
        monthly_summary = (
            bank_df.groupby(["Month", "Transaction Type"])["Amount"]
            .sum()
            .unstack(fill_value=0)
            .reset_index()
        )
        st.dataframe(monthly_summary)
    
        # 📋 Full Transaction Log
        st.subheader("📋 Full Bank Transaction Log")
    
        # Prepare DataFrame
        display_df = bank_df[["Date", "Transaction By", "Transaction Type", "Reason", "Amount", "Bill"]].copy()
    
        # Format Amount with + / - and apply color
        def format_amount(row):
            amt = row["Amount"]
            if "credit" in row["Transaction Type"].lower():
                return f"+₹{amt:,.2f}"
            elif "debit" in row["Transaction Type"].lower():
                return f"-₹{amt:,.2f}"
            return f"₹{amt:,.2f}"
    
        display_df["Formatted Amount"] = bank_df.apply(format_amount, axis=1)
    
        # Style Amount column with color
        def color_amount(val):
            if isinstance(val, str):
                if val.startswith("+"):
                    return "color: green"
                elif val.startswith("-"):
                    return "color: red"
            return ""
    
        styled = display_df[["Date", "Transaction By", "Transaction Type", "Reason", "Formatted Amount", "Bill"]].sort_values(by="Date", ascending=False)
        styled_df = styled.style.applymap(color_amount, subset=["Formatted Amount"])
    
        st.dataframe(styled_df, use_container_width=True)


    
    # 🔁 Refresh button
    if st.sidebar.button("🔁 Refresh"):
        st.cache_resource.clear()
        st.experimental_rerun()
