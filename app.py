import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(
    page_title="NIFTY FUT Buildup Demo",
    layout="wide",
)

st.title("NIFTY Futures - Price + Position Buildup (Dummy Data Demo)")

# -----------------------
# 1. Generate dummy data
# -----------------------
np.random.seed(42)

num_candles = 50
start_time = datetime.now() - timedelta(minutes=num_candles)

times = [start_time + timedelta(minutes=i) for i in range(num_candles)]

# Price path
price = 22500 + np.cumsum(np.random.normal(0, 5, size=num_candles))
high = price + np.random.uniform(5, 15, size=num_candles)
low = price - np.random.uniform(5, 15, size=num_candles)
open_ = price + np.random.normal(0, 3, size=num_candles)
close = price

# OI path (monotonic-ish but noisy)
oi = 100000 + np.cumsum(np.random.normal(0, 500, size=num_candles))
oi = np.maximum(oi, 50000)  # avoid negative

df = pd.DataFrame(
    {
        "time": times,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "oi": oi,
    }
)

df.set_index("time", inplace=True)

# -----------------------
# 2. Compute buildup
# -----------------------
df["prev_close"] = df["close"].shift(1)
df["prev_oi"] = df["oi"].shift(1)

df["price_change"] = df["close"] - df["prev_close"]
df["oi_change"] = df["oi"] - df["prev_oi"]

# Long / Short buildup flags
conditions_long = (df["price_change"] > 0) & (df["oi_change"] > 0)
conditions_short = (df["price_change"] < 0) & (df["oi_change"] > 0)

df["buildup_type"] = np.where(
    conditions_long,
    "LONG",
    np.where(conditions_short, "SHORT", "NONE"),
)

# Bar height: only where buildup exists, else 0
df["buildup_value"] = np.where(
    df["buildup_type"].isin(["LONG", "SHORT"]),
    df["oi_change"].abs(),
    0,
)

# Colors: green for LONG, red for SHORT, transparent for NONE
colors = []
for typ in df["buildup_type"]:
    if typ == "LONG":
        colors.append("rgba(0, 200, 0, 0.8)")   # green
    elif typ == "SHORT":
        colors.append("rgba(200, 0, 0, 0.8)")   # red
    else:
        colors.append("rgba(0, 0, 0, 0.0)")     # invisible

# -----------------------
# 3. Build Plotly figure
# -----------------------
fig = go.Figure()

# Candlestick (row 1 conceptually)
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

# Add a second y-axis for buildup bars
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
        x=1
    ),
    margin=dict(l=40, r=40, t=40, b=40),
    height=700,
)

st.plotly_chart(fig, use_container_width=True)

st.caption(
    "Green bars = Long buildup (Price↑, OI↑). Red bars = Short buildup (Price↓, OI↑). "
    "Dummy data only – next step: wire Upstox futures + OI."
)
