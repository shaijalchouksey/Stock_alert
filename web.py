import streamlit as st
import pandas as pd
import pyodbc
import requests
from bs4 import BeautifulSoup
import time
from sqlalchemy import create_engine
import yfinance as yf
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import google.auth
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64  # Added missing import
import os  # Ensure safe path handling

# Correct SQL Server connection settings
server = "DESKTOP-OSJVKIN\SQLEXPRESS"
database = "stock_data"

# Use SQLAlchemy to manage connections
engine = create_engine(f"mssql+pyodbc://{server}/{database}?driver=SQL+Server")
query = "SELECT * FROM dbo.stock_data ORDER BY timestamp DESC"
df = pd.read_sql(query, engine)

# Streamlit UI
st.title("📈 Live Stock Data Dashboard")

st.subheader("Stock Data Table")
st.dataframe(df)

st.subheader("📨 Get Stock Alerts via Email")
email = st.text_area("Enter recipient email(s) (comma-separated):")
recipient_list = [e.strip() for e in email.split(",") if e.strip()]
selected_alert_stock = st.selectbox("Select a stock for email alerts:", df["symbol"].unique(), key="alert_stock")
threshold = st.number_input("Set a price threshold:", min_value=0.0, value=100.0, step=1.0)

# Gmail API-based Email Notification
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# Use raw string to avoid path escape errors
CLIENT_SECRET_FILE = r"C:\\Users\\abhib\\Desktop\\Stock Market\\client_secret_943600035845-5n6uk0rcp7uubokof6ktcl7a4vsd0ihg.apps.googleusercontent.com.json"

def send_email_oauth2(subject, body, recipient_emails):
    creds = None
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
    creds = flow.run_local_server(port=0)
    service = build("gmail", "v1", credentials=creds)
    
    message = MIMEMultipart()
    message["To"] = ", ".join(recipient_emails)  # Allow multiple recipients
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))
    
    # Encode message correctly
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    try:
        service.users().messages().send(userId="me", body={"raw": raw_message}).execute()
        st.success("📧 Email sent successfully to: " + ", ".join(recipient_emails))
    except Exception as e:
        st.error(f"❌ Failed to send email: {e}")

if st.button("🔔 Set Alert") and recipient_list:
    current_price = df[df["symbol"] == selected_alert_stock]["price"].iloc[-1]
    if current_price >= threshold:
        send_email_oauth2(
            subject=f"Stock Alert: {selected_alert_stock}",
            body=f"The stock {selected_alert_stock} has reached {current_price} which is above your threshold {threshold}.",
            recipient_emails=recipient_list
        )
    else:
        st.info(f"No alert sent. {selected_alert_stock} is currently at {current_price}, below your threshold of {threshold}.")
