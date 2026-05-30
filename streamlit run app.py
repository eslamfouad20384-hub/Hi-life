import streamlit as st
import requests
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide")
st.title("🚀 Ultra Smart Scanner PRO + Clean Data Filter")

session = requests.Session()

# =========================
# 📦 COINS LIST
# =========================
@st.cache_data(ttl=3600)
def get_all_products():
    try:
        url = "https://api.exchange.coinbase.com/products"
        r = session.get(url, timeout=10).json()

        symbols = [
            item["base_currency"]
            for item in r
            if item.get("quote_currency") == "USD"
        ]

        return list(set(symbols))
    except:
        return []


# =========================
# 📊 MARKET DATA (CLEAN VERSION)
# =========================
@st.cache_data(ttl=60)
def get_data(symbol):
    try:
        url = f"https://api.exchange.coinbase.com/products/{symbol}-USD/candles?granularity=3600"
        r = session.get(url, timeout=10).json()

        # ❌ reject invalid API response
        if not isinstance(r, list) or len(r) < 120:
            return None

        df = pd.DataFrame(r, columns=["time","low","high","open","close","volume"])

        # ❌ drop rows with missing values immediately
        df = df.dropna()

        # ❌ ensure no empty dataframe after cleaning
        if df.empty:
            return None

        df = df.sort_values("time").reset_index(drop=True)

        # ❌ final validation for numeric consistency
        for col in ["low", "high", "open", "close", "volume"]:
            if col not in df.columns:
                return None
            if df[col].isna().any():
                return None

        return df.astype(float)

    except:
        return None


# =========================
# 📈 INDICATORS
# =========================
def add_indicators(df):

    df["ema50"] = df["close"].ewm(span=50).mean()
    df["ema200"] = df["close"].ewm(span=200).mean()

    delta = df["close"].diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)

    avg_gain = pd.Series(gain).ewm(alpha=1/14, adjust=False).mean()
    avg_loss = pd.Series(loss).ewm(alpha=1/14, adjust=False).mean()

    rs = avg_gain / (avg_loss + 1e-9)
    df["rsi"] = 100 - (100 / (1 + rs))

    ema12 = df["close"].ewm(span=12).mean()
    ema26 = df["close"].ewm(span=26).mean()

    df["macd"] = ema12 - ema26
    df["signal"] = df["macd"].ewm(span=9).mean()

    df["vol_ma"] = df["volume"].rolling(20).mean()
    df["support"] = df["low"].rolling(20).min()
    df["resistance"] = df["high"].rolling(20).max()

    high_low = df["high"] - df["low"]
    high_close = abs(df["high"] - df["close"].shift())
    low_close = abs(df["low"] - df["close"].shift())

    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = tr.rolling(14).mean()

    # ❌ remove rows with NaN after indicators
    df = df.dropna()

    return df


# =========================
# 🧠 STRONG FILTER (NO BROKEN DATA ALLOWED)
# =========================
def smart_filter(df):

    # ❌ basic structure check
    required_cols = ["atr", "volume", "close", "ema50", "ema200", "rsi", "macd"]
    for col in required_cols:
        if col not in df.columns:
            return False

    # ❌ remove incomplete data
    if df.isnull().any().any():
        return False

    # ❌ not enough candles
    if len(df) < 120:
        return False

    # ❌ no zero or negative prices
    if (df["close"] <= 0).any():
        return False

    # ❌ weak liquidity filter
    if df["volume"].mean() < 5000:
        return False

    # ❌ volatility check
    if pd.isna(df["atr"].iloc[-1]):
        return False

    volatility = df["atr"].iloc[-1] / (df["close"].mean() + 1e-9)

    if volatility < 0.01:
        return False

    return True


# =========================
# 🎯 ANALYSIS
# =========================
def analyze(df):

    latest = df.iloc[-1]
    score = 0

    if latest["rsi"] < 35:
        score += 15

    if latest["macd"] > latest["signal"]:
        score += 15

    if latest["ema50"] > latest["ema200"]:
        score += 15

    if latest["close"] <= latest["support"] * 1.02:
        score += 10

    if latest["volume"] > latest["vol_ma"]:
        score += 10

    if latest["atr"] > df["atr"].mean():
        score += 10

    if latest["close"] > df["close"].iloc[-5:].mean():
        score += 10

    if df["close"].iloc[-10:].mean() > df["close"].iloc[-30:-10].mean():
        score += 5

    if score >= 80:
        signal = "🔥 قوي جدًا"
    elif score >= 65:
        signal = "🟢 فرصة"
    elif score >= 50:
        signal = "⚠️ مراقبة"
    else:
        signal = "❌ ضعيف"

    return signal, score


# =========================
# 💰 RISK MANAGEMENT
# =========================
def risk_management(df, rr=2):

    latest = df.iloc[-1]

    entry = latest["close"]
    atr = latest["atr"]

    if pd.isna(atr):
        return None

    stop_loss = entry - (1.5 * atr)
    risk = entry - stop_loss
    take_profit = entry + (risk * rr)

    return entry, stop_loss, take_profit, rr


# =========================
# ⚙️ PROCESS COIN
# =========================
def process_coin(coin):

    df = get_data(coin)

    # ❌ reject missing or broken data instantly
    if df is None or df.empty:
        return None

    df = add_indicators(df)

    if not smart_filter(df):
        return None

    signal, score = analyze(df)

    if score >= 50:

        risk = risk_management(df, rr=2)
        if risk is None:
            return None

        entry, sl, tp, rr = risk

        return {
            "Symbol": coin,
            "Signal": signal,
            "Score": score,
            "Entry": round(entry, 4),
            "Stop Loss": round(sl, 4),
            "Take Profit": round(tp, 4),
            "R/R": f"1:{rr}"
        }

    return None


# =========================
# 🚀 SCANNER
# =========================
results = []

if st.button("🚀 Scan Market PRO"):

    coins = get_all_products()
    progress = st.progress(0)

    with ThreadPoolExecutor(max_workers=10) as executor:

        for i, result in enumerate(executor.map(process_coin, coins)):

            if result:
                results.append(result)

            progress.progress((i+1)/len(coins))

    if results:
        df_res = pd.DataFrame(results).sort_values("Score", ascending=False)
        st.success("🔥 Strong Clean Signals Found")
        st.dataframe(df_res, use_container_width=True)
    else:
        st.warning("❌ No clean setups found")
