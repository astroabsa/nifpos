import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import requests

# -------------------------------------------------
# Streamlit basic config
# -------------------------------------------------
st.set_page_config(
    page_title="NIFTY FUT Buildup (Upstox V2)",
    layout="wide",
)

st.title("NIFTY Futures - Price + Position Buildup (Upstox V2)")

# -------------------------------------------------
# Upstox config (ACCESS_TOKEN in secrets.toml)
# -------------------------------------------------
ACCESS_TOKEN = st.secrets["upstox"]["access_token"]  # .streamlit/secrets.toml
BASE_URL = "https://api.upstox.com/v2"

# TODO: yahan apne instruments master se correct NIFTY FUT key daalo
# Example format: "NSE_FO|NIFTY24JUNFUT"
NIFTY_FUT_INSTRUMENT_KEY = "NSE_FO|NIFTY24JUNFUT"

# -------------------------------------------------
# Helper: fetch intraday candles (current day)
# -------------------------------------------------
def fetch_intraday_candles_v2(
    instrument_key: str,
    interval: str = "1minute",
) -> pd.DataFrame:
    """
    V2 intraday endpoint:
    GET /v2/historical-candle/intraday/{instrumentKey}/{interval}
    Returns current trading day's candles.
    """
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Accept": "application/json",
    }

    url = f"{BASE_URL}/historical-candle/intraday/{instrument_key}/{interval}"
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    js = r.json()

    candles = js.get("data", {}).get("candles", [])
    if not candles:
        raise RuntimeError("No intraday candles returned from Upstox")

    rows = []
    for c in candles:
        # Expected format: [timestamp, open, high, low, close, volume]
        ts = datetime.fromisoformat(c[0])
        o = float(c[1])
        h = float(c[2])
        l = float(c[3])
        cl = float(c[4])
        vol = float(c[5]) if len(c) > 5 else 0.0
        rows.append((ts, o, h, l, cl, vol))

    df = pd.DataFrame(
        rows,
        columns=["time", "open", "high", "low", "close", "volume"],
    ).set_index("time")

    return df


# -------------------------------------------------
# 1) Fetch data from Upstox
# -------------------------------------------------
with st.spinner("Fetching NIFTY FUT intraday candles from Upstox..."):
    try:
        df = fetch_intraday_candles_v2(
            instrument_key=NIFTY_FUT_INSTRUMENT_KEY,
            interval="1minute",   # later: map 1/3/5 min
        )
    except Exception as e:
        st.error(f"Upstox API error: {e}")
        st.stop()

# -------------------------------------------------
# 2) Temporary synthetic OI (jab tak real OI source fix na ho)
# -------------------------------------------------
# Abhi ke liye price real hai, OI hum generate kar rahe hain so that
# buildup logic & chart work end-to-end.
np.random.seed(42)
oi = 100000 + np.cumsum(np.random.normal(0, 500, size=len(df)))
oi = np.maximum(oi, 50000)
df["oi"] = oi

# -------------------------------------------------
# 3) Compute long / short buildup
# -------------------------------------------------
df["prev_close"] = df["close"].shift(1)
df["prev_oi"] = df["oi"].shift(1)

df["price_change"] = df["close"] - df["prev_close"]
df["oi_change"] = df["oi"] - df["prev_oi"]

conditions_long = (df["price_change"] > 0) & (df["oi_change"] > 0)
conditions_short = (df["price_change"] < 0) & (df["oi_change"] > 0)

df["buildup_type"] = np.where(
    conditions_long,
    "LONG",
    np.where(conditions_short, "SHORT", "NONE"),
)

df["buildup_value"] = np.where(
    df["buildup_type"].isin(["LONG", "SHORT"]),
    df["oi_change"].abs(),
    0,
)

colors = []
for typ in df["buildup_type"]:
    if typ == "LONG":
        colors.append("rgba(0, 200, 0, 0.8)")   # green
    elif typ == "SHORT":
        colors.append("rgba(200, 0, 0, 0.8)")   # red
    else:
        colors.append("rgba(0, 0, 0, 0.0)")     # invisible

# -------------------------------------------------
# 4) Combined candlestick + buildup chart
# -------------------------------------------------
fig = go.Figure()

# Price candles
fig.add_trace(
    go.Candlestick(
        x=df.index,
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        name="NIFTY FUT",
        increasing_line_color="#00cc96",
        decreasing_line_color="#ff4b4b",
    )
)

# Buildup bars on secondary y-axis
fig.add_trace(
    go.Bar(
        x=df.index,
        y=df["buildup_value"],
        marker_color=colors,
        name="Position Buildup",
        yaxis="y2",
    )
)

fig.update_layout(
    xaxis=dict(
        title="Time",
        rangeslider=dict(visible=False),
    ),
    yaxis=dict(
        title="Price",
        side="right",
        showgrid=True,
        gridcolor="rgba(200,200,200,0.3)",
    ),
    yaxis2=dict(
        title="OI Change (Buildup)",
        overlaying="y",
        side="left",
        showgrid=False,
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
    ),
    margin=dict(l=40, r=40, t=40, b=40),
    height=700,
)

st.plotly_chart(fig, use_container_width=True)

st.caption(
    "Green bars = Long buildup (Price↑, OI↑). "
    "Red bars = Short buildup (Price↓, OI↑). "
    "Price from Upstox V2 intraday candles; OI currently synthetic."
)
