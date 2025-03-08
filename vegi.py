import streamlit as st

# Load secrets from .streamlit/secrets.toml
AUTH_SHEET_ID = st.secrets["A_S_ID"]
COLLECTION_SHEET_ID = st.secrets["C_S_ID"]
EXPENSE_SHEET_ID = st.secrets["E_S_ID"]

st.write("Secrets loaded successfully!")
