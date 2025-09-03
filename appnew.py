# ====== CONFIG ====== 
EMAIL_SENDER = "slimevideos0404@gmail.com"
EMAIL_PASSWORD = "bdaf aarm qkvm cfkv"   # create App Password in Gmail security
EMAIL_RECEIVER = "hayyaanraza48@gmail.com"

TICKERS = [
    "AAPL","MSFT","AMZN","NVDA","GOOGL","META","JPM","XOM","JNJ","CAT",
    "PFE","V","SHOP","GS","LMT","NEE","C","RELIANCE.NS","INFY.NS","TCS.NS",
    "HDFCBANK.NS","ICICIBANK.NS","LT.NS","BHARTIARTL.NS","ADANIENT.NS","NTPC.NS",
    "NESN.SW","ASML.AS","MC.PA","SIE.DE","SAP.DE","TTE.PA","ULVR.L","RIO.L",
    "SAN.PA","ADYEN.AS","VOW3.DE","AZN.L","BARC.L","IBE.MC","NG.L","URW.PA",
    "VALE","PBR","ABEV","YPF","EC","AVAL","SQM","EMBR3.SA","FUNO11.MX",
    "D05.SI","SE","BBCA.JK","5183.KL","7203.T","005930.KS","TSM","6758.T","000660.KS"
]

# ====== HELPERS ======
def send_email(subject, body):
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = EMAIL_SENDER
        msg["To"] = EMAIL_RECEIVER
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, [EMAIL_RECEIVER], msg.as_string())
    except Exception as e:
        print(f"[ERROR] Email failed: {e}")

def bollinger(close, window, k):
    sma = close.rolling(window).mean()
    std = close.rolling(window).std()
    upper = sma + k*std
    lower = sma - k*std
    bw = (upper - lower) / sma * 100
    return sma, upper, lower, bw

def crossed_upper(close, upper):
    if len(close) < 2:
        return False
    return close.iloc[-1] > upper.iloc[-1] and close.iloc[-2] <= upper.iloc[-2]

def run_scan(interval, period, window, std_mult, lookback, max_bw):
    results = []
    try:
        data = yf.download(TICKERS, period=period, interval=interval, group_by="ticker", progress=False, threads=True)
    except Exception as e:
        print(f"[WARN] yfinance error: {e}")
        return pd.DataFrame()
    for t in TICKERS:
        try:
            df = data[t] if isinstance(data.columns, pd.MultiIndex) else data
            close = df["Close"].dropna()
            if len(close) < window+lookback+2:
                continue
            sma, upper, lower, bw = bollinger(close, window, std_mult)
            if crossed_upper(close, upper) and bw.iloc[-lookback] <= max_bw:
                results.append({
                    "Ticker": t,
                    "Close": round(close.iloc[-1], 2),
                    "UpperBB": round(upper.iloc[-1], 2),
                    "LowerBB": round(lower.iloc[-1], 2),
                    "Bandwidth%": round(bw.iloc[-lookback], 2),
                    "df": df
                })
        except Exception:
            continue
    return pd.DataFrame(results)

# ====== BACKGROUND JOBS ======
def job_10m():
    df = run_scan("10m", "60d", 20, 2, 4, 6.0)
    if not df.empty:
        send_email("🔔 10m Bollinger Alerts", df.to_string(index=False))

def job_1h():
    df = run_scan("1h", "730d", 20, 2, 4, 6.0)
    if not df.empty:
        send_email("🔔 1h Bollinger Alerts", df.to_string(index=False))

def start_scheduler():
    schedule.every(30).minutes.do(job_10m)
    schedule.every(1).hours.do(job_1h)
    while True:
        schedule.run_pending()
        time.sleep(60)

# Run scheduler in background thread
def run_in_background():
    t = threading.Thread(target=start_scheduler, daemon=True)
    t.start()

# ====== STREAMLIT UI ======
import streamlit as st
import pandas as pd
import yfinance as yf
import schedule
import time
import threading
import smtplib
from email.mime.text import MIMEText
import plotly.graph_objects as go

st.set_page_config(page_title="Bollinger Band Scanner", layout="wide")

# Custom CSS to give it a clean, website-like look
st.markdown("""
<style>
.main {
    background-color: #F8F9FA;
    color: #343A40;
}
.st-emotion-cache-1cpx6a9 {
    background-color: #ffffff;
    padding: 20px;
    border-radius: 10px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}
.stButton>button {
    border: none;
    background-color: #28A745;
    color: white;
    font-weight: bold;
    border-radius: 5px;
}
.stButton>button:hover {
    background-color: #218838;
    color: white;
}
</style>
""", unsafe_allow_html=True)

st.title("📊 Bollinger Band Multi-Timeframe Scanner")
st.markdown(
    "Analyze stocks to find opportunities based on Bollinger Band signals. "
    "Use the sidebar to run a manual scan or start a background process for automated alerts."
)

st.sidebar.header("Manual Scan Parameters")
window = st.sidebar.number_input("Bollinger Window", 5, 100, 20)
std_mult = st.sidebar.number_input("Std Dev Multiplier", 1.0, 4.0, 2.0, step=0.5)
lookback = st.sidebar.number_input("Lookback Candles", 1, 20, 4)
max_bandwidth = st.sidebar.number_input("Max Bandwidth %", 0.0, 50.0, 6.0)
tf = st.sidebar.selectbox("Timeframe", ["10m","1h","1d"])
period_map = {"10m":"60d","1h":"730d","1d":"1y"}

if st.sidebar.button("Run Manual Scan"):
    with st.spinner("Fetching data..."):
        # Pass the max_bandwidth instead of min_bandwidth
        df_results = run_scan(tf, period_map[tf], window, std_mult, lookback, max_bandwidth)
        
    if df_results.empty:
        st.warning("No signals found.")
    else:
        st.success(f"Found {len(df_results)} signals.")
        
        st.markdown("---")
        st.header("🔍 Scan Results")
        st.dataframe(df_results.drop(columns=['df'])) # drop the dataframe to avoid showing it in the table
        st.download_button(
            f"Download {tf} Results CSV",
            df_results.to_csv(index=False).encode("utf-8"),
            file_name=f"bb_results_{tf}.csv",
            mime="text/csv"
        )

        st.markdown("---")
        st.header("📈 Interactive Charts")
        
        for index, row in df_results.iterrows():
            ticker = row['Ticker']
            ticker_df = row['df']
            
            close = ticker_df["Close"].dropna()
            sma, upper, lower, bw = bollinger(close, window, std_mult)

            # Create candlestick chart
            fig = go.Figure(data=[go.Candlestick(
                x=ticker_df.index,
                open=ticker_df['Open'],
                high=ticker_df['High'],
                low=ticker_df['Low'],
                close=ticker_df['Close'],
                name='Price'
            )])

            # Add Bollinger Bands
            fig.add_trace(go.Scatter(x=close.index, y=upper, name='Upper BB', line=dict(color='orange', width=1.5)))
            fig.add_trace(go.Scatter(x=close.index, y=lower, name='Lower BB', line=dict(color='blue', width=1.5)))
            fig.add_trace(go.Scatter(x=close.index, y=sma, name='SMA', line=dict(color='purple', width=1.5)))

            fig.update_layout(
                title=f"Bollinger Band Chart for {ticker}",
                yaxis_title="Price",
                xaxis_rangeslider_visible=False,
                paper_bgcolor='#F8F9FA'
            )

            st.plotly_chart(fig, use_container_width=True)
            
if st.sidebar.button("Start Auto Alerts"):
    st.success("✅ Background auto-alerts started (10m every 30min, 1h every 1h).")
    run_in_background()

st.markdown("---")
st.caption("Data: Yahoo Finance | Alerts via Gmail | For educational use only.")