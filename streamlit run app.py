import streamlit as st
import requests
import pandas as pd
import numpy as np
import time

st.set_page_config(layout="wide")
st.title("🚀 Full Market Engine (5000 Coins AI Pipeline)")

# =========================
# 🌍 1. UNIVERSE (5000+ coins)
# =========================
def get_cc_universe():
    url = "https://min-api.cryptocompare.com/data/all/coinlist"
    r = requests.get(url).json()

    data = r.get("Data", {})
    coins = list(data.keys())

    return coins


# =========================
# ⚡ 2. LIGHT DATA (fast check)
# =========================
def get_fast_data(symbol):

    try:
        url = "https://min-api.cryptocompare.com/data/pricemultifull"
        params = {
            "fsyms": symbol,
            "tsyms": "USD"
        }

        r = requests.get(url, params=params).json()

        raw = r.get("RAW", {}).get(symbol, {}).get("USD", {})

        if not raw:
            return None

        price = raw.get("PRICE", 0)
        volume = raw.get("VOLUME24HOUR", 0)
        change = raw.get("CHANGEPCT24HOUR", 0)

        return {
            "price": price,
            "volume": volume,
            "change": change
        }

    except:
        return None


# =========================
# 🧠 LIGHT FILTER (5000 → 200)
# =========================
def light_filter(data):

    if data is None:
        return False

    if data["price"] <= 0:
        return False

    if data["volume"] < 50000:
        return False

    if abs(data["change"]) < 1:
        return False

    return True


# =========================
# 📊 OHLC (deep analysis)
# =========================
def get_ohlc(symbol):

    try:
        url = "https://min-api.cryptocompare.com/data/v2/histohour"
        params = {
            "fsym": symbol,
            "tsym": "USD",
            "limit": 200
        }

        r = requests.get(url, params=params).json()

        data = r.get("Data", {}).get("Data", [])
        if len(data) < 100:
            return None

        df = pd.DataFrame(data)

        df = df.sort_values("time").reset_index(drop=True)

        df["volume"] = df.get("volumefrom", 0)

        return df

    except:
        return None


# =========================
# ⚡ DEEP FILTER (200 → 30)
# =========================
def deep_filter(df):

    try:
        avg_vol = df["volume"].mean()
        volatility = (df["high"].max() - df["low"].min()) / (df["close"].mean() + 1e-9)

        if avg_vol < 10000:
            return False

        if volatility < 0.04:
            return False

        return True

    except:
        return False


# =========================
# 📊 INDICATORS
# =========================
def add_indicators(df):

    df["ema50"] = df["close"].ewm(span=50).mean()
    df["ema200"] = df["close"].ewm(span=200).mean()

    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    rs = gain.rolling(14).mean() / (loss.rolling(14).mean() + 1e-9)
    df["rsi"] = 100 - (100 / (1 + rs))

    ema12 = df["close"].ewm(span=12).mean()
    ema26 = df["close"].ewm(span=26).mean()

    df["macd"] = ema12 - ema26
    df["signal"] = df["macd"].ewm(span=9).mean()

    df["vol_ma"] = df["volume"].rolling(20).mean()
    df["support"] = df["low"].rolling(20).min()

    return df


# =========================
# 🧠 FINAL SCORING
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

    if latest["close"] <= latest["support"] * 1.01:
        score += 10

    if latest["volume"] > df["vol_ma"].iloc[-1]:
        score += 10

    low = df["low"].min()
    high = df["high"].max()

    pressure = (latest["close"] - low) / (high - low + 1e-9)

    sweep = latest["low"] <= low

    momentum = latest["close"] > df["close"].iloc[-5:].mean()

    trend = df["close"].iloc[-10:].mean() > df["close"].iloc[-30:-10].mean()

    if pressure < 0.2:
        score += 15

    if sweep:
        score += 10

    if momentum:
        score += 5

    if trend:
        score += 5

    # ===== SIGNALS =====
    if score >= 80:
        signal = "🔥 قوي جدًا"
    elif score >= 65:
        signal = "🟢 صالح"
    elif score >= 50:
        signal = "⚠️ مراقبة"
    else:
        signal = "❌ لا يوجد دخول"

    return signal, score


# =========================
# 🚀 ENGINE PIPELINE
# =========================
results = []

if st.button("🚀 Run Full Market Engine"):

    coins = get_cc_universe()

    st.write(f"🌍 Universe Size: {len(coins)} coins")

    light_pass = []

    progress = st.progress(0)

    # =========================
    # 🧠 STAGE 1 (5000 → 200)
    # =========================
    for i, coin in enumerate(coins[:2000]):  # حماية من الضغط

        data = get_fast_data(coin)

        if light_filter(data):
            light_pass.append(coin)

        progress.progress((i+1)/2000)

    st.write(f"⚡ After Light Filter: {len(light_pass)} coins")

    # =========================
    # ⚡ STAGE 2 (200 → 30)
    # =========================
    deep_pass = []

    for coin in light_pass[:300]:

        df = get_ohlc(coin)

        if df is None:
            continue

        if deep_filter(df):
            deep_pass.append(coin)

    st.write(f"📊 After Deep Filter: {len(deep_pass)} coins")

    # =========================
    # 📊 STAGE 3 (Analysis)
    # =========================
    for coin in deep_pass[:30]:

        df = get_ohlc(coin)

        if df is None:
            continue

        df = add_indicators(df)

        signal, score = analyze(df)

        if score >= 50:

            results.append({
                "Symbol": coin,
                "Signal": signal,
                "Score": score,
                "Price": df.iloc[-1]["close"]
            })

    # =========================
    # 🔥 OUTPUT
    # =========================
    if results:
        st.success("🔥 Final Signals Ready")
        st.dataframe(pd.DataFrame(results).sort_values("Score", ascending=False))
    else:
        st.warning("❌ No strong signals")
