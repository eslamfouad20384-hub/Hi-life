import streamlit as st
import requests
import pandas as pd
import numpy as np

st.set_page_config(layout="wide")
st.title("🔥 Ultra Hybrid Smart Scanner (Technical + Price Action)")

# =========================
# 📊 Coinbase symbols
# =========================
def get_all_products():
    url = "https://api.exchange.coinbase.com/products"
    r = requests.get(url).json()

    symbols = []
    for item in r:
        if item["quote_currency"] == "USD":
            symbols.append(item["base_currency"])

    return list(set(symbols))


# =========================
# 📥 OHLC Data (Coinbase)
# =========================
def get_data(symbol):
    url = f"https://api.exchange.coinbase.com/products/{symbol}-USD/candles"

    r = requests.get(url).json()

    if not isinstance(r, list) or len(r) < 100:
        return None

    df = pd.DataFrame(r, columns=["time","low","high","open","close","volume"])

    # ترتيب الزمن (مهم جدًا 🔥)
    df = df.sort_values("time").reset_index(drop=True)

    return df.astype(float)


# =========================
# 📊 Indicators (Hybrid)
# =========================
def add_indicators(df):

    # EMA
    df["ema50"] = df["close"].ewm(span=50).mean()
    df["ema200"] = df["close"].ewm(span=200).mean()

    # RSI
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / (avg_loss + 1e-9)

    df["rsi"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = df["close"].ewm(span=12).mean()
    ema26 = df["close"].ewm(span=26).mean()
    df["macd"] = ema12 - ema26
    df["signal"] = df["macd"].ewm(span=9).mean()

    # Volume avg
    df["vol_ma"] = df["volume"].rolling(20).mean()

    # Support / Resistance
    df["support"] = df["low"].rolling(20).min()
    df["resistance"] = df["high"].rolling(20).max()

    return df


# =========================
# 🧠 Smart Filter (Market quality)
# =========================
def smart_filter(df):

    avg_volume = df["volume"].mean()

    high_low_range = df["high"].max() - df["low"].min()
    volatility = high_low_range / (df["close"].mean() + 1e-9)

    # سوق ميت
    if avg_volume < 5000:
        return False

    # حركة ضعيفة
    if volatility < 0.03:
        return False

    return True


# =========================
# 🎯 Hybrid Scoring System
# =========================
def analyze(df):

    latest = df.iloc[-1]

    score = 0

    # ===== Technical (from system 1)
    if latest["rsi"] < 35:
        score += 15

    if latest["macd"] > latest["signal"]:
        score += 15

    if latest["ema50"] > latest["ema200"]:
        score += 15

    if latest["close"] <= latest["support"] * 1.01:
        score += 10

    if latest["volume"] > latest["vol_ma"]:
        score += 10

    # ===== Price Action (from system 2)

    pressure = (latest["close"] - df["low"].min()) / (df["high"].max() - df["low"].min() + 1e-9)

    sweep = latest["low"] <= df["low"].min()

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

    # ===== Signal mapping
    if score >= 80:
        signal = "🔥 BUY قوي جدًا"
    elif score >= 65:
        signal = "🟢 BUY قوي"
    elif score >= 50:
        signal = "⏳ مراقبة"
    else:
        signal = "❌ لا يوجد دخول"

    return signal, score


# =========================
# 🚀 Scanner
# =========================
results = []

if st.button("🚀 Scan Hybrid Market"):

    coins = get_all_products()

    progress = st.progress(0)

    for i, coin in enumerate(coins):

        df = get_data(coin)

        if df is None:
            continue

        if not smart_filter(df):
            continue

        df = add_indicators(df)

        signal, score = analyze(df)

        if score >= 70:

            results.append({
                "Symbol": coin,
                "Signal": signal,
                "Score": score,
                "Price": df.iloc[-1]["close"]
            })

        progress.progress((i+1)/len(coins))

    if results:
        st.success("🔥 Best Hybrid Opportunities")
        st.dataframe(pd.DataFrame(results).sort_values("Score", ascending=False))
    else:
        st.warning("❌ No strong setups right now")
