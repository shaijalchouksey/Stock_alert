import streamlit as st
import pandas as pd
import pyodbc
import requests
import time
import os
from sqlalchemy import create_engine
import plotly.graph_objects as go
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ✅ Load Alpha Vantage API Key from system environment variable
ALPHA_VANTAGE_API_KEY = os.environ.get("ALPHA_VANTAGE_API_KEY")

if not ALPHA_VANTAGE_API_KEY:
    st.error("❌ Alpha Vantage API Key is missing. Set it in your system environment variables.")
    st.stop()

# ✅ Database connection settings
server = "DESKTOP-OSJVKIN\\SQLEXPRESS"
database = "stock_data"
try:
    engine = create_engine(f"mssql+pyodbc://{server}/{database}?driver=SQL+Server")
    query = "SELECT * FROM dbo.stock_data ORDER BY timestamp DESC"
    df = pd.read_sql(query, engine)
except Exception as e:
    st.warning("⚠️ Could not connect to the database. Showing empty data.")
    df = pd.DataFrame(columns=["symbol", "price", "timestamp"])

# ✅ Function to fetch stock data from Alpha Vantage
def fetch_stock_data(symbol):
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=5min&apikey={ALPHA_VANTAGE_API_KEY}"
    response = requests.get(url)
    data = response.json()

    if "Time Series (5min)" not in data:
        st.error(f"❌ Failed to fetch data for {symbol}. API limit exceeded or invalid symbol.")
        return None

    latest_time = max(data["Time Series (5min)"])
    latest_data = data["Time Series (5min)"][latest_time]
    return {
        "symbol": symbol,
        "price": float(latest_data["1. open"]),
        "timestamp": latest_time
    }

# ✅ Streamlit UI
st.title("📈 Live Stock Data Dashboard")

st.subheader("Stock Data Table")
st.dataframe(df)

# ✅ Fetch new data
st.subheader("🔄 Fetch Live Stock Data")
stock_symbol = st.text_input("Enter Stock Symbol (e.g., AAPL, TSLA)", value="AAPL")
if st.button("Fetch Data"):
    stock_info = fetch_stock_data(stock_symbol)
    if stock_info:
        st.success(f"✅ Latest price for {stock_symbol}: {stock_info['price']} USD")
        st.write(stock_info)

# ✅ Email Alert Section
st.subheader("📨 Get Stock Alerts via Email")
email = st.text_area("Enter recipient email(s) (comma-separated):")
recipient_list = [e.strip() for e in email.split(",") if e.strip()]
selected_alert_stock = st.selectbox("Select a stock for email alerts:", df["symbol"].unique() if not df.empty else [])
threshold = st.number_input("Set a price threshold:", min_value=0.0, value=100.0, step=1.0)

# ✅ Gmail API-based Email Notification
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
CLIENT_SECRET_FILE = r"C:\\Users\\abhib\\Desktop\\Stock Market\\client_secret.json"

ALPHA_VANTAGE_API_KEY = "L6TXKYFD2SU6ZMXX"  # Replace with your actual API key


def send_email_oauth2(subject, body, recipient_emails):
    try:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        service = build("gmail", "v1", credentials=creds)

        message = MIMEMultipart()
        message["To"] = ", ".join(recipient_emails)
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw_message}).execute()

        st.success(f"📧 Email sent successfully to: {', '.join(recipient_emails)}")
    except Exception as e:
        st.error(f"❌ Failed to send email: {e}")

if st.button("🔔 Set Alert") and recipient_list:
    try:
        current_price = df[df["symbol"] == selected_alert_stock]["price"].iloc[-1]
        if current_price >= threshold:
            send_email_oauth2(
                subject=f"Stock Alert: {selected_alert_stock}",
                body=f"The stock {selected_alert_stock} has reached {current_price} which is above your threshold {threshold}.",
                recipient_emails=recipient_list
            )
        else:
            st.info(f"No alert sent. {selected_alert_stock} is currently at {current_price}, below your threshold of {threshold}.")
    except IndexError:
        st.warning("⚠️ No stock data available for the selected stock.")

