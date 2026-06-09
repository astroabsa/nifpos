import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

import plotly.graph_objects as go
from plotly.subplots import make_subplots

# -----------------------
# Streamlit page config
# -----------------------
st.set_page_config(
    page_title="NIFTY FUT Buildup Demo",
    layout="wide",
)

st.title("NIFTY Futures - Price + Position Buildup (Dummy Data)")

# -----------------------
# Sidebar – timeframe
# -----------------------
tf = st.sidebar.selectbox(
    "Timeframe",
    options=["1 min", "3 min", "5 min"],
    index=0,
)

if tf == "1 min":
    step_minutes = 1
elif tf == "3 min":
    step_minutes = 3
else:
    step_minutes = 5

st.sidebar.write(f"Dummy candles every {step_minutes} minute(s).")

# -----------------------
# 1. Generate dummy data
# -----------------------
np.random.seed(42)

num_candles = 50
start_time = datetime.now() - timedelta(minutes=num_candles * step_minutes)

times = [start_time + timedelta(minutes=i * step_minutes)
         for i in range(num_candles)]

# Price path
price = 22500 + np.cumsum(np.random.normal(0, 5, size=num_candles))
high = price + np.random.uniform(5, 15, size=num_candles)
low = price - np.random.uniform(5, 15, size=num_candles)
open_ = price + np.random.normal(0, 3, size=num_candles)
close = price

# OI path
oi = 100000 + np.cumsum(np.random.normal(0, 500, size=num_candles))
oi = np.maximum(oi, 50000)

df = pd.DataFrame(
    {
        "time": times,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "oi": oi,
    }
).set_index("time")

# -----------------------
# 2. Compute buildup
# -----------------------
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
        colors.append("rgba(0, 200, 0, 0.9)")   # green
    elif typ == "SHORT":
        colors.append("rgba(220, 0, 0, 0.9)")   # red
    else:
        colors.append("rgba(0, 0, 0, 0.0)")     # invisible

# ------- buildup values ko + / - banao  -------
df["buildup_signed"] = 0.0

df.loc[df["buildup_type"] == "LONG", "buildup_signed"] = df["oi_change"].abs()
df.loc[df["buildup_type"] == "SHORT", "buildup_signed"] = -df["oi_change"].abs()

colors = []
for val in df["buildup_signed"]:
    if val > 0:
        colors.append("rgba(0, 200, 0, 0.9)")   # LONG -> green
    elif val < 0:
        colors.append("rgba(220, 0, 0, 0.9)")   # SHORT -> red
    else:
        colors.append("rgba(0, 0, 0, 0.0)")     # NONE -> invisible

# ------- subplots -------
from plotly.subplots import make_subplots
import plotly.graph_objects as go

fig = make_subplots(
    rows=2,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.03,
    row_heights=[0.7, 0.3],
)

# Row 1: price candles
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
    ),
    row=1,
    col=1,
)

# Row 2: signed buildup histogram
fig.add_trace(
    go.Bar(
        x=df.index,
        y=df["buildup_signed"],
        marker_color=colors,
        name="Position Buildup",
        width=0.6,
    ),
    row=2,
    col=1,
)

fig.update_yaxes(title_text="Price", row=1, col=1,
                 showgrid=True, gridcolor="rgba(220,220,220,0.5)")

fig.update_yaxes(title_text="OI Change (Buildup)",
                 row=2, col=1,
                 zeroline=True, zerolinecolor="black",
                 showgrid=False)

fig.update_xaxes(title_text="Time", row=2, col=1)

fig.update_layout(
    legend=dict(orientation="h", yanchor="bottom", y=1.02,
                xanchor="right", x=1),
    margin=dict(l=40, r=40, t=40, b=40),
    height=800,
)

fig.update_traces(marker_line_width=0, row=2, col=1)

st.plotly_chart(fig, use_container_width=True)
st.caption(
    "Green bars = Long buildup (Price↑, OI↑). "
    "Red bars = Short buildup (Price↓, OI↑). Dummy data only – next step: Upstox live data."
)
