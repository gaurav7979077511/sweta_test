import streamlit as st
import pandas as pd
import bcrypt
import gspread
from google.oauth2.service_account import Credentials

# Streamlit App Configuration
st.set_page_config(page_title="Google Sheets Dashboard", layout="wide")

# Google Sheets Authentication
SHEET_IDS = {
    "auth": "1RCIZrxv21hY-xtzDRuC0L50KLCLpZuYWKKatuJoVCT8",
    "collection": "1l0RVkf3U0XvWJre74qHy3Nv5n-4TKTCSV5yNVW4Sdbw",
    "expense": "1bEquqG2T-obXkw5lWwukx1v_lFnLrFdAf6GlWHZ9J18"
}
SHEET_NAMES = {
    "auth": "Sheet1",
    "collection": "Form responses 1",
    "expense": "Form responses 1"
}

# Load credentials from Streamlit Secrets
creds_dict = dict(st.secrets["gcp_service_account"])
creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
creds = Credentials.from_service_account_info(
    creds_dict,
    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
)
client = gspread.authorize(creds)

def load_sheet_data(sheet_id, sheet_name):
    sheet = client.open_by_key(sheet_id).worksheet(sheet_name)
    return pd.DataFrame(sheet.get_all_records())

# Authentication Data
auth_df = load_sheet_data(SHEET_IDS["auth"], SHEET_NAMES["auth"])

def verify_password(stored_hash, entered_password):
    return bcrypt.checkpw(entered_password.encode(), stored_hash.encode())

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_role = None
    st.session_state.username = None
    st.session_state.user_name = None

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
                st.success(f"✅ Welcome, {name}!")
                st.rerun()
            else:
                st.error("❌ Invalid Credentials")
        else:
            st.error("❌ User not found")
else:
    if st.sidebar.button("🚪 Logout"):
        st.session_state.authenticated = False
        st.session_state.user_role = None
        st.session_state.username = None
        st.session_state.user_name = None
        st.rerun()
    
    st.sidebar.write(f"👤 **Welcome, {st.session_state.user_name}!**")
    df = load_sheet_data(SHEET_IDS["collection"], SHEET_NAMES["collection"])
    expense_df = load_sheet_data(SHEET_IDS["expense"], SHEET_NAMES["expense"])
    
    st.sidebar.header("📂 Navigation")
    page = st.sidebar.radio("Go to:", ["Dashboard", "Monthly Summary", "Grouped Data", "Expenses", "Raw Data"])

    if page == "Dashboard":
        st.title("📊 Orga Yatra Dashboard")
        total_collection = df['Amount'].sum()
        total_expense = expense_df['Amount Used'].sum()
        remaining_amount = total_collection - total_expense

        last_month = df['Month-Year'].max()
        last_month_collection = df[df['Month-Year'] == last_month]['Amount'].sum()
        last_month_expense = expense_df[expense_df['Month-Year'] == last_month]['Amount Used'].sum()

        col1, col2, col3 = st.columns(3)
        col1.metric(label="💰 Total Collection", value=f"₹{total_collection:,.2f}")
        col2.metric(label="📉 Total Expenses", value=f"₹{total_expense:,.2f}")
        col3.metric(label="💵 Remaining Balance", value=f"₹{remaining_amount:,.2f}")
        
        formatted_last_month = pd.to_datetime(last_month).strftime("%b %Y")  
        st.subheader("📅 " + formatted_last_month + " Overview")
        
        col4, col5 = st.columns(2)
        col4.metric(label="📈 " + formatted_last_month + " Collection", value=f"₹{last_month_collection:,.2f}")
        col5.metric(label="📉 " + formatted_last_month + " Expenses", value=f"₹{last_month_expense:,.2f}")
        
        st.write("### 📈 Collection & Distance Trend")
        st.line_chart(df.set_index("Collection Date")[["Amount", "Distance"]])
        
        st.write("### 🔍 Recent Collection Data:")
        st.dataframe(df.sort_values(by="Collection Date", ascending=False).head(10))

    elif page == "Expenses":
        st.title("💸 Expense Details")
        st.dataframe(expense_df.sort_values(by="Date", ascending=False))
    
    elif page == "Raw Data":
        st.title("📋 Full Collection Data")
        st.dataframe(df.sort_values(by="Collection Date", ascending=False))
