import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import ta
import requests
from bs4 import BeautifulSoup
from textblob import TextBlob
import streamlit as st
import time
import streamlit as st

st.set_page_config(layout="wide")


# ================= UI STYLE =================
st.markdown("""
    <style>
    body {
        background-color: #f4f6f9;
        color: #111;
    }

    .stApp {
        background-color: #f4f6f9;
    }

    .stMetric {
        background-color: #ffffff;
        padding: 14px;
        border-radius: 12px;
        border: 1px solid #e6e6e6;
        box-shadow: 0px 2px 8px rgba(0,0,0,0.06);
    }

    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 10px;
        box-shadow: 0px 2px 6px rgba(0,0,0,0.05);
    }

    h1, h2, h3 {
        color: #111;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Dashboard")

# ================= SESSION =================
session = requests.Session()
headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9"
}

# ================= PCR (FIXED - STABLE) =================
def get_pcr(symbol="NIFTY"):
    try:
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"

        session.get("https://www.nseindia.com", headers=headers, timeout=5)
        res = session.get(url, headers=headers, timeout=10)

        data = res.json()

        put = 0
        call = 0

        records = data.get("records", {}).get("data", [])

        for item in records:
            if item.get("PE"):
                put += item["PE"].get("openInterest", 0)
            if item.get("CE"):
                call += item["CE"].get("openInterest", 0)

        if call > 0:
            return round(put / call, 2)

    except:
        pass

    return None


# ================= VIX (FIXED - GUARANTEED FALLBACK) =================
def get_vix():
    try:
        vix = yf.Ticker("^INDIAVIX").history(period="5d")["Close"].dropna()
        if len(vix) > 0:
            return round(vix.iloc[-1], 2)
    except:
        pass

    try:
        r = session.get("https://www.nseindia.com/api/allIndices", headers=headers, timeout=10)
        data = r.json()

        for i in data.get("data", []):
            if "India VIX" in i.get("index", ""):
                return round(float(i.get("last")), 2)
    except:
        pass

    return None


# ================= INPUT =================
company = st.text_input("Enter Company", "RELIANCE.NS")

if ".NS" in company:
    stock_name = company
    screener_name = company.replace(".NS", "")
else:
    stock_name = company.upper() + ".NS"
    screener_name = company.upper()

# ================= SCREENER =================
def get_screener(name):
    try:
        url = f"https://www.screener.in/company/{name}/"
        soup = BeautifulSoup(requests.get(url).text, "lxml")

        data = {}

        for r in soup.find_all("li", class_="flex flex-space-between"):
            try:
                k = r.find("span", class_="name").text.strip()
                v = r.find("span", class_="number").text.strip()
                data[k] = v
            except:
                pass

        return data
    except:
        return {}

# ================= FETCH =================
stock = yf.Ticker(stock_name)
df = stock.history(period="1y")
info = stock.info
scr = get_screener(screener_name)

def pct(x): return f"{round(x*100,2)} %" if x else "N/A"
def val(x): return round(x,2) if x else "N/A"
def cr(x): return f"₹ {round(x/1e7,2)} Cr" if x else "N/A"

if not df.empty:

    # ================= TECH =================
    df['RSI'] = ta.momentum.RSIIndicator(df['Close']).rsi()
    df['50DMA'] = df['Close'].rolling(50).mean()
    df['200DMA'] = df['Close'].rolling(200).mean()

    # ================= MARKET SENTIMENT =================
    st.markdown("---")
    st.header("Market Sentiment")

    pcr = get_pcr("NIFTY")
    vix = get_vix()

    c1, c2 = st.columns(2)

    if pcr is not None:
        if pcr > 1:
            c1.success(f"NIFTY PCR: {pcr} (Bearish)")
        else:
            c1.success(f"NIFTY PCR: {pcr} (Bullish)")
    else:
        c1.warning("NIFTY PCR: Not Available")

    if vix is not None:
        c2.metric("India VIX", vix)
    else:
        c2.warning("India VIX: Not Available")

    # ================= VALUATION =================
    st.markdown("---")
    st.header("Valuation")

    c1,c2,c3,c4 = st.columns(4)

    c1.metric("Price", f"₹ {val(df['Close'].iloc[-1])}")
    c1.metric("52W High", f"₹ {val(df['High'].max())}")
    c1.metric("52W Low", f"₹ {val(df['Low'].min())}")

    c2.metric("P/E", info.get("trailingPE") or scr.get("P/E"))
    c2.metric("P/B", info.get("priceToBook") or scr.get("P/B"))

    c3.metric("EV/EBITDA", val(info.get("enterpriseToEbitda")))
    c3.metric("Market Cap", cr(info.get("marketCap")))

    c4.metric("Dividend Yield", pct(info.get("dividendYield")))
    c4.metric("Beta", val(info.get("beta")))

    # ================= PROFITABILITY =================
    st.markdown("---")
    st.header("Profitability")

    c5,c6,c7 = st.columns(3)

    roe = info.get("returnOnEquity")
    roe = pct(roe) if roe else scr.get("ROE")

    c5.metric("ROE", roe)
    c5.metric("ROCE", scr.get("ROCE"))

    c6.metric("ROA", pct(info.get("returnOnAssets")))
    c6.metric("Net Margin", pct(info.get("profitMargins")))

    c7.metric("Operating Margin", pct(info.get("operatingMargins")))
    c7.metric("Gross Margin", pct(info.get("grossMargins")))

    # ================= FINANCIAL HEALTH =================
    st.markdown("---")
    st.header("Financial Health")

    f1,f2,f3 = st.columns(3)
    f1.metric("Debt/Equity", val(info.get("debtToEquity")))
    f2.metric("Current Ratio", val(info.get("currentRatio")))
    f3.metric("Quick Ratio", val(info.get("quickRatio")))

    # ================= CASH FLOW =================
    st.markdown("---")
    st.header("Cash Flow")

    cf1,cf2 = st.columns(2)
    cf1.metric("Operating Cash Flow", cr(info.get("operatingCashflow")))
    cf2.metric("Free Cash Flow", cr(info.get("freeCashflow")))

    # ================= RISK =================
    st.markdown("---")
    st.header("Risk Analysis")

    returns = df['Close'].pct_change().dropna()
    vol = returns.std() * np.sqrt(252)
    sharpe = (returns.mean() * 252) / (vol + 1e-5)

    r1,r2 = st.columns(2)
    r1.metric("Volatility", round(vol,2))
    r2.metric("Sharpe Ratio", round(sharpe,2))

    # ================= SIGNAL =================
    st.markdown("---")
    st.header("AI Recommendation")

    signal = "HOLD"
    if df['RSI'].iloc[-1] < 30 and sharpe > 1:
        signal = "BUY"
    elif df['RSI'].iloc[-1] > 70:
        signal = "SELL"

    st.success(f"Signal: {signal}")

    # ================= SCREENER =================
    st.markdown("---")
    st.header("Undervalued Screener")

    universe = ["RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS","ICICIBANK.NS"]
    res = []

    for s in universe:
        i = yf.Ticker(s).info
        if i.get("trailingPE") and i.get("returnOnEquity"):
            if i["trailingPE"] < 25 and i["returnOnEquity"] > 0.15:
                res.append(s)

    st.write(res)

    # ================= NEWS =================
    st.markdown("---")
    st.header("News Sentiment")

    try:
        news = stock.news
        sentiments = []

        for n in news[:5]:
            text = n.get('title') or n.get('summary') or ""
            sentiments.append(TextBlob(text).sentiment.polarity)

        if sentiments:
            avg = np.mean(sentiments)
            st.write("Positive" if avg > 0 else "Negative")
        else:
            st.info("No news")
    except:
        st.info("No news")

    # ================= CHARTS =================
    st.markdown("---")
    st.header("Charts")

    st.line_chart(df['Close'])
    st.line_chart(df[['Close','50DMA','200DMA']])
    st.line_chart(df['RSI'])

else:
    st.error("Invalid stock")