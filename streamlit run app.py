import streamlit as st
import requests
import pandas as pd
import numpy as np

st.set_page_config(layout="wide")
st.title("🚀 Ultra Hybrid Scanner (Stable + Fixed Version)")

# =========================
# 📊 Coinbase Symbols
# =========================
def get_cb_symbols():
    url = "https://api.exchange.coinbase.com/products"
    r = requests.get(url).json()

    coins = []
    for item in r:
        if item.get("quote_currency") == "USD":
            coins.append(item.get("base_currency"))

    return list(set(coins))


# =========================
# 📊 CryptoCompare Symbols
# =========================
def get_cc_symbols():
    url = "https://min-api.cryptocompare.com/data/all/coinlist"
    r = requests.get(url).json()

    coins = []

    data = r.get("Data", {})
    for k in data.keys():
        coins.append(k)

    return coins


# =========================
# 📊 Coinbase Data
# =========================
def get_data_cb(symbol):
    try:
        url = f"https://api.exchange.coinbase.com/products/{symbol}-USD/candles"
        r = requests.get(url).json()

        if not isinstance(r, list) or len(r) < 100:
            return None

        df = pd.DataFrame(r, columns=["time","low","high","open","close","volume"])
        df = df.sort_values("time").reset_index(drop=True)

        return df.astype(float)

    except:
        return None


# =========================
# 📊 CryptoCompare Data (FIXED)
# =========================
def get_data_cc(symbol):
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

        # 🔥 توحيد الأعمدة
        if "volumefrom" in df.columns:
            df["volume"] = df["volumefrom"]
        elif "volumeto" in df.columns:
            df["volume"] = df["volumeto"]
        else:
            df["volume"] = 0

        # 🔥 ضمان الأعمدة الأساسية
        for col in ["open", "high", "low", "close"]:
            if col not in df.columns:
                df[col] = 0

        df = df.sort_values("time").reset_index(drop=True)

        return df.astype(float)

    except:
        return None


# =========================
# 📊 Indicators
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
# 🔥 Safe Smart Filter
# =========================
def smart_filter(df):

    if df is None or "volume" not in df.columns:
        return False

    avg_volume = df["volume"].mean()

    if np.isnan(avg_volume):
        return False

    volatility = (df["high"].max() - df["low"].min()) / (df["close"].mean() + 1e-9)

    if avg_volume < 5000:
        return False

    if volatility < 0.03:
        return False

    return True


# =========================
# 🧠 Analysis Engine
# =========================
def analyze(df):

    latest = df.iloc[-1]
    score = 0

    # Technical
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

    # Price action
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


    # ===== Signal mapping =====
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
# 🚀 Universe Expansion
# =========================
def build_universe():

    cb = set(get_cb_symbols())
    cc = set(get_cc_symbols())

    hidden = list(cc - cb)

    return list(cb), hidden


# =========================
# 🚀 Scanner
# =========================
results = []

if st.button("🚀 Scan Market (Fixed + Hidden Gems)"):

    cb_coins, hidden_coins = build_universe()

    coins = cb_coins + hidden_coins[:50]  # تقليل الضغط

    progress = st.progress(0)

    for i, coin in enumerate(coins):

        df = get_data_cb(coin)

        if df is None:
            df = get_data_cc(coin)

        if df is None:
            continue

        if not smart_filter(df):
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

        progress.progress((i+1)/len(coins))

    if results:
        st.success("🔥 Results Loaded Successfully")
        st.dataframe(pd.DataFrame(results).sort_values("Score", ascending=False))
    else:
        st.warning("❌ No setups found")
