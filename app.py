"""
app.py - StockSense Dashboard Phase 2.

Neu: Technische Indikatoren (MA, RSI, Bollinger Bands)
     und Intraday-Zeitrahmen (1min, 5min, 1h).
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data import (
    load_stock_data, get_ticker_info, compute_returns,
    compute_moving_averages, compute_ema, compute_rsi,
    compute_bollinger_bands,
    POPULAR_TICKERS, TIMEFRAME_OPTIONS,
)


st.set_page_config(page_title="StockSense", page_icon="📈", layout="wide")
st.title("📈 StockSense")
st.caption("Historische Aktienanalyse mit technischen Indikatoren · Phase 2")


# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Einstellungen")

    selected_name = st.selectbox("Aktie / Index", list(POPULAR_TICKERS.keys()))
    ticker = POPULAR_TICKERS[selected_name]

    custom = st.text_input("Oder eigenes Symbol", placeholder="z.B. AMZN, SAP.DE")
    if custom.strip():
        ticker = custom.strip().upper()

    selected_tf = st.selectbox("Zeitrahmen", list(TIMEFRAME_OPTIONS.keys()), index=3)
    period   = TIMEFRAME_OPTIONS[selected_tf]["period"]
    interval = TIMEFRAME_OPTIONS[selected_tf]["interval"]

    st.divider()
    st.subheader("Indikatoren")

    show_sma      = st.checkbox("Moving Averages (SMA 20 / 50)", value=True)
    show_ema      = st.checkbox("EMA 20", value=False)
    show_bb       = st.checkbox("Bollinger Bands", value=True)
    show_rsi      = st.checkbox("RSI", value=True)
    show_volume   = st.checkbox("Volumen", value=True)
    show_returns  = st.checkbox("Kumulative Rendite", value=True)


# ─── Datenabruf ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)   # 1 Minute Cache — kürzer für Intraday-Daten
def cached_load(ticker, period, interval):
    return load_stock_data(ticker, period, interval)

@st.cache_data(ttl=300)
def cached_info(ticker):
    return get_ticker_info(ticker)


with st.spinner(f"Lade {ticker} · {selected_tf}..."):
    try:
        df   = cached_load(ticker, period, interval)
        info = cached_info(ticker)
    except ValueError as e:
        st.error(str(e))
        st.stop()

# Indikatoren berechnen
df = compute_returns(df)
if show_sma:
    df = compute_moving_averages(df, [20, 50])
if show_ema:
    df = compute_ema(df, 20)
if show_bb:
    df = compute_bollinger_bands(df)
if show_rsi:
    df = compute_rsi(df)


# ─── Kennzahlen ──────────────────────────────────────────────────────────────
st.subheader(info["name"])

first_close = float(df["Close"].iloc[0])
last_close  = float(df["Close"].iloc[-1])
change_pct  = (last_close - first_close) / first_close * 100
currency    = info.get("currency", "")

col1, col2, col3, col4 = st.columns(4)
col1.metric(
    f"Kurs ({currency})",
    f"{last_close:,.2f}",
    f"{change_pct:+.2f}%",
)
col2.metric("52W-Hoch", f"{info['52w_high']:,.2f}" if info["52w_high"] else "—")
col3.metric("52W-Tief", f"{info['52w_low']:,.2f}"  if info["52w_low"]  else "—")

# RSI-Ampel in der 4. Karte
if show_rsi and "RSI" in df.columns:
    rsi_val = float(df["RSI"].dropna().iloc[-1])
    if rsi_val > 70:
        rsi_label = "Überkauft"
    elif rsi_val < 30:
        rsi_label = "Überverkauft"
    else:
        rsi_label = "Neutral"
    col4.metric("RSI (14)", f"{rsi_val:.1f}", rsi_label)
else:
    col4.metric("Sektor", info["sector"] or "—")


# ─── Haupt-Chart: Kurs + Indikatoren ─────────────────────────────────────────
# Anzahl der Zeilen im Chart dynamisch bestimmen
chart_rows    = [1]                        # Kurs immer dabei
row_heights   = [0.55]

if show_volume:
    chart_rows.append(len(chart_rows) + 1)
    row_heights.append(0.15)
if show_rsi and "RSI" in df.columns:
    chart_rows.append(len(chart_rows) + 1)
    row_heights.append(0.20)
if show_returns:
    chart_rows.append(len(chart_rows) + 1)
    row_heights.append(0.20)

# Höhen auf 1.0 normalisieren
total = sum(row_heights)
row_heights = [h / total for h in row_heights]

fig = make_subplots(
    rows=len(chart_rows), cols=1,
    shared_xaxes=True,
    row_heights=row_heights,
    vertical_spacing=0.04,
)

# ── Candlestick ──
fig.add_trace(go.Candlestick(
    x=df.index,
    open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
    name="Kurs",
    increasing_line_color="#1D9E75",
    decreasing_line_color="#E24B4A",
), row=1, col=1)

# ── Bollinger Bands (als Fläche) ──
if show_bb and "BB_upper" in df.columns:
    fig.add_trace(go.Scatter(
        x=df.index, y=df["BB_upper"],
        line=dict(color="#7F77DD", width=1, dash="dot"),
        name="BB oben", showlegend=True,
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=df["BB_lower"],
        line=dict(color="#7F77DD", width=1, dash="dot"),
        fill="tonexty",
        fillcolor="rgba(127,119,221,0.08)",
        name="BB unten", showlegend=True,
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=df["BB_middle"],
        line=dict(color="#7F77DD", width=1),
        name="BB Mitte", showlegend=True,
    ), row=1, col=1)

# ── Moving Averages ──
ma_colors = {"SMA_20": "#EF9F27", "SMA_50": "#E24B4A"}
if show_sma:
    for col_name, color in ma_colors.items():
        if col_name in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col_name],
                line=dict(color=color, width=1.5),
                name=col_name.replace("_", " "),
            ), row=1, col=1)

if show_ema and "EMA_20" in df.columns:
    fig.add_trace(go.Scatter(
        x=df.index, y=df["EMA_20"],
        line=dict(color="#1D9E75", width=1.5, dash="dash"),
        name="EMA 20",
    ), row=1, col=1)

# ── Volumen ──
current_row = 2
if show_volume:
    colors = [
        "#1D9E75" if float(df["Close"].iloc[i]) >= float(df["Open"].iloc[i]) else "#E24B4A"
        for i in range(len(df))
    ]
    fig.add_trace(go.Bar(
        x=df.index, y=df["Volume"],
        marker_color=colors, opacity=0.6, name="Volumen",
    ), row=current_row, col=1)
    fig.update_yaxes(title_text="Vol.", row=current_row, col=1)
    current_row += 1

# ── RSI ──
if show_rsi and "RSI" in df.columns:
    fig.add_trace(go.Scatter(
        x=df.index, y=df["RSI"],
        line=dict(color="#378ADD", width=1.5),
        name="RSI",
    ), row=current_row, col=1)
    # Überkauft / Überverkauft Linien
    fig.add_hline(y=70, line_dash="dot", line_color="#E24B4A", opacity=0.6, row=current_row, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#1D9E75", opacity=0.6, row=current_row, col=1)
    fig.add_hline(y=50, line_dash="dot", line_color="gray",    opacity=0.3, row=current_row, col=1)
    fig.update_yaxes(title_text="RSI", range=[0, 100], row=current_row, col=1)
    current_row += 1

# ── Kumulative Rendite ──
if show_returns:
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["cumulative_return"] * 100,
        line=dict(color="#378ADD", width=1.5),
        fill="tozeroy",
        fillcolor="rgba(55,138,221,0.08)",
        name="Rendite (%)",
        hovertemplate="%{y:.2f}%<extra></extra>",
    ), row=current_row, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.4, row=current_row, col=1)
    fig.update_yaxes(title_text="Rendite %", row=current_row, col=1)

# ── Layout ──
fig.update_layout(
    height=650,
    xaxis_rangeslider_visible=False,
    legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
    margin=dict(l=0, r=0, t=40, b=0),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
)
fig.update_yaxes(title_text="Kurs", row=1, col=1)

st.plotly_chart(fig, use_container_width=True)


# ─── Indikatoren Erklärung ────────────────────────────────────────────────────
with st.expander("Was bedeuten die Indikatoren?"):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**SMA (Simple Moving Average)**")
        st.caption("Durchschnittskurs der letzten N Kerzen. SMA 20 = kurzfristiger Trend, SMA 50 = mittelfristiger Trend. Kreuzt SMA 20 den SMA 50 von unten → mögliches Kaufsignal (Golden Cross).")
        st.markdown("**EMA (Exponential Moving Average)**")
        st.caption("Wie SMA, aber neuere Kurse gewichtet stärker. Reagiert schneller auf Veränderungen.")
    with c2:
        st.markdown("**RSI (Relative Strength Index)**")
        st.caption("Wert zwischen 0–100. Über 70 = überkauft (Vorsicht). Unter 30 = überverkauft (mögliche Erholung). Bei 50 = neutral.")
        st.markdown("**Bollinger Bands**")
        st.caption("Zeigen Volatilität. Enge Bänder = ruhiger Markt. Weite Bänder = unruhiger Markt. Kurs am oberen Band = möglicherweise zu teuer.")

# ─── Rohdaten ─────────────────────────────────────────────────────────────────
with st.expander("Rohdaten anzeigen"):
    cols = ["Open", "High", "Low", "Close", "Volume"]
    if show_sma:
        cols += [c for c in ["SMA_20", "SMA_50"] if c in df.columns]
    if show_rsi and "RSI" in df.columns:
        cols.append("RSI")
    display_df = df[cols].copy().round(2).sort_index(ascending=False)
    display_df.index = display_df.index.strftime("%d.%m.%Y %H:%M") if interval != "1d" else display_df.index.strftime("%d.%m.%Y")
    st.dataframe(display_df, use_container_width=True)
