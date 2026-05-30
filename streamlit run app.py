import streamlit as st
import requests
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(layout="wide")
st.title("🚀 Ultra Smart Scanner PRO + Risk Management")

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
            if item["quote_currency"] == "USD"
        ]

        return list(set(symbols))
    except:
        return []


# =========================
# 📊 MARKET DATA
# =========================
@st.cache_data(ttl=60)
def get_data(symbol):
    try:
        url = f"https://api.exchange.coinbase.com/products/{symbol}-USD/candles?granularity=3600"
        r = session.get(url, timeout=10).json()

        if not isinstance(r, list) or len(r) < 100:
            return None

        df = pd.DataFrame(r, columns=["time","low","high","open","close","volume"])
        df = df.sort_values("time").reset_index(drop=True)

        return df.astype(float)

    except:
        return None


# =========================
# 📈 INDICATORS
# =========================
def add_indicators(df):

    df["ema50"] = df["close"].ewm(span=50).mean()
    df["ema200"] = df["close"].ewm(span=200).mean()

    # RSI Wilder
    delta = df["close"].diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)

    avg_gain = pd.Series(gain).ewm(alpha=1/14, adjust=False).mean()
    avg_loss = pd.Series(loss).ewm(alpha=1/14, adjust=False).mean()

    rs = avg_gain / (avg_loss + 1e-9)
    df["rsi"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = df["close"].ewm(span=12).mean()
    ema26 = df["close"].ewm(span=26).mean()

    df["macd"] = ema12 - ema26
    df["signal"] = df["macd"].ewm(span=9).mean()

    # Volume
    df["vol_ma"] = df["volume"].rolling(20).mean()

    # Support / Resistance
    df["support"] = df["low"].rolling(20).min()
    df["resistance"] = df["high"].rolling(20).max()

    # ATR (Risk Engine)
    high_low = df["high"] - df["low"]
    high_close = abs(df["high"] - df["close"].shift())
    low_close = abs(df["low"] - df["close"].shift())

    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = tr.rolling(14).mean()

    return df


# =========================
# 🧠 FILTER
# =========================
def smart_filter(df):

    if df is None or len(df) < 100:
        return False

    if df["volume"].mean() < 5000:
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
# 💰 RISK MANAGEMENT (SL / TP / RR)
# =========================
def risk_management(df, rr=2):

    latest = df.iloc[-1]

    entry = latest["close"]
    atr = latest["atr"]

    # 🛑 Stop Loss (1.5 ATR)
    stop_loss = entry - (1.5 * atr)

    # 🎯 Risk
    risk = entry - stop_loss

    # 🎯 Take Profit
    take_profit = entry + (risk * rr)

    return entry, stop_loss, take_profit, rr


# =========================
# ⚙️ PROCESS COIN
# =========================
def process_coin(coin):

    df = get_data(coin)
    if df is None:
        return None

    if not smart_filter(df):
        return None

    df = add_indicators(df)

    signal, score = analyze(df)

    if score >= 50:

        entry, sl, tp, rr = risk_management(df, rr=2)

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
        st.success("🔥 Strong Signals Found")
        st.dataframe(df_res, use_container_width=True)
    else:
        st.warning("❌ No setups found")
