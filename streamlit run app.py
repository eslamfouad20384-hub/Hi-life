import streamlit as st
import requests
import pandas as pd
import ta

st.set_page_config(page_title="Crypto Screener Pro", layout="wide")

st.title("🔥 Crypto BUY Screener (100 Coins)")

# =========================
# 📊 جلب Top 100 عملة
# =========================
@st.cache_data
def get_top_100_symbols():
    url = "https://min-api.cryptocompare.com/data/top/mktcapfull"

    params = {
        "limit": 100,
        "tsym": "USD"
    }

    r = requests.get(url, params=params).json()

    coins = []

    for item in r["Data"]:
        try:
            symbol = item["CoinInfo"]["Name"]
            coins.append(symbol)
        except:
            continue

    return coins


# =========================
# 📥 جلب البيانات
# =========================
@st.cache_data
def get_data(symbol):
    url = "https://min-api.cryptocompare.com/data/v2/histohour"

    params = {
        "fsym": symbol,
        "tsym": "USD",
        "limit": 200
    }

    r = requests.get(url, params=params).json()

    if "Data" not in r:
        return None

    df = pd.DataFrame(r["Data"]["Data"])
    return df


# =========================
# 📊 المؤشرات
# =========================
def add_indicators(df):
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()

    df["wr"] = ta.momentum.WilliamsRIndicator(
        df["high"], df["low"], df["close"]
    ).williams_r()

    macd = ta.trend.MACD(df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()

    df["volume_ma"] = df["volumeto"].rolling(20).mean()

    df["ema200"] = ta.trend.EMAIndicator(
        df["close"], window=200
    ).ema_indicator()

    df["support"] = df["close"].rolling(20).min()

    return df


# =========================
# 🎯 BUY Signal
# =========================
def get_score(df):
    latest = df.iloc[-1]

    c1 = latest["rsi"] < 30
    c2 = latest["wr"] < -80
    c3 = latest["close"] <= latest["support"] * 1.01
    c4 = latest["volumeto"] > latest["volume_ma"]
    c5 = latest["macd"] > latest["macd_signal"]
    c6 = latest["close"] > latest["ema200"]

    score = sum([c1, c2, c3, c4, c5, c6])

    return score


# =========================
# 🚀 تشغيل السكريينر
# =========================
if st.button("🚀 Run Screener (100 Coins)"):

    symbols = get_top_100_symbols()

    results = []

    progress = st.progress(0)

    for i, sym in enumerate(symbols):

        df = get_data(sym)

        if df is None or len(df) < 50:
            continue

        df = add_indicators(df)

        score = get_score(df)

        price = df.iloc[-1]["close"]

        results.append({
            "Symbol": sym,
            "Price": price,
            "Score /6": score,
            "Signal": "🔥 BUY" if score >= 3 else "—"
        })

        progress.progress((i + 1) / len(symbols))

    result_df = pd.DataFrame(results)

    result_df = result_df.sort_values(by="Score /6", ascending=False)

    st.dataframe(result_df, use_container_width=True)

    st.success("Done ✔️ 100 coins scanned")
