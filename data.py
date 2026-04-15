"""
data.py - Datenabruf und technische Indikatoren.

Neu in Phase 2:
- Intraday-Intervalle (1min, 5min, 1h)
- Moving Averages (SMA, EMA)
- RSI (Relative Strength Index)
- Bollinger Bands
"""

import time
import yfinance as yf
import pandas as pd
import numpy as np


POPULAR_TICKERS = {
    "Apple":           "AAPL",
    "Microsoft":       "MSFT",
    "Tesla":           "TSLA",
    "NVIDIA":          "NVDA",
    "BMW":             "BMW.DE",
    "Volkswagen":      "VOW3.DE",
    "Siemens":         "SIE.DE",
    "DAX (Index)":     "^GDAXI",
    "S&P 500 (Index)": "^GSPC",
}

# Zeitraum-Optionen mit zugehörigem Intervall und Label
# yfinance erlaubt nur bestimmte Kombinationen:
#   1m  → max. 7 Tage
#   5m  → max. 60 Tage
#   1h  → max. 730 Tage
#   1d  → unbegrenzt
TIMEFRAME_OPTIONS = {
    "1 Minute  (letzte 7 Tage)":    {"period": "7d",  "interval": "1m"},
    "5 Minuten (letzte 60 Tage)":   {"period": "60d", "interval": "5m"},
    "1 Stunde  (letzte 2 Jahre)":   {"period": "2y",  "interval": "1h"},
    "1 Tag – 1 Monat":              {"period": "1mo", "interval": "1d"},
    "1 Tag – 3 Monate":             {"period": "3mo", "interval": "1d"},
    "1 Tag – 6 Monate":             {"period": "6mo", "interval": "1d"},
    "1 Tag – 1 Jahr":               {"period": "1y",  "interval": "1d"},
    "1 Tag – 2 Jahre":              {"period": "2y",  "interval": "1d"},
    "1 Tag – 5 Jahre":              {"period": "5y",  "interval": "1d"},
}


def load_stock_data(ticker: str, period: str, interval: str) -> pd.DataFrame:
    """
    Lädt historische Kursdaten für einen Ticker.
    Bei Rate-Limit-Fehlern wird bis zu 3x automatisch neu versucht.
    """
    last_error = None

    for attempt in range(3):
        try:
            data = yf.download(
                ticker,
                period=period,
                interval=interval,
                auto_adjust=True,
                progress=False,
            )

            if data.empty:
                raise ValueError(f"Keine Daten für '{ticker}' gefunden. Ticker korrekt?")

            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            if data.index.tz is not None:
                data.index = data.index.tz_localize(None)

            return data

        except ValueError:
            raise   # Ticker-Fehler sofort weitergeben, nicht nochmal versuchen
        except Exception as e:
            last_error = e
            if attempt < 2:
                time.sleep(2 + attempt * 2)   # 2s, dann 4s warten

    raise ValueError(
        f"Yahoo Finance antwortet gerade nicht für '{ticker}'. "
        f"Bitte 30 Sekunden warten und neu laden. (Fehler: {last_error})"
    )


def get_ticker_info(ticker: str) -> dict:
    """Holt Basisinfos — bei Fehler werden Standardwerte zurückgegeben."""
    try:
        info = yf.Ticker(ticker).info
        return {
            "name":      info.get("longName", ticker),
            "currency":  info.get("currency", ""),
            "sector":    info.get("sector", "—"),
            "price":     info.get("currentPrice") or info.get("regularMarketPrice"),
            "52w_high":  info.get("fiftyTwoWeekHigh"),
            "52w_low":   info.get("fiftyTwoWeekLow"),
            "pe_ratio":  info.get("trailingPE"),
        }
    except Exception:
        # Wenn die Info nicht geladen werden kann, einfach Standardwerte
        return {
            "name": ticker, "currency": "", "sector": "—",
            "price": None, "52w_high": None, "52w_low": None, "pe_ratio": None,
        }





def compute_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Berechnet tägliche und kumulative Rendite."""
    df = df.copy()
    df["daily_return"]      = df["Close"].pct_change()
    df["cumulative_return"] = (1 + df["daily_return"]).cumprod() - 1
    return df


# ─── Technische Indikatoren ──────────────────────────────────────────────────

def compute_moving_averages(df: pd.DataFrame, windows: list) -> pd.DataFrame:
    """
    Berechnet Simple Moving Averages (SMA) für mehrere Zeitfenster.

    SMA 20 = Durchschnitt der letzten 20 Kerzen.
    Liegt der Kurs über dem SMA → Aufwärtstrend.
    Liegt er darunter → Abwärtstrend.
    """
    df = df.copy()
    for w in windows:
        df[f"SMA_{w}"] = df["Close"].rolling(window=w).mean()
    return df


def compute_ema(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """
    Exponential Moving Average — wie SMA, aber neuere Kurse zählen stärker.
    Reagiert schneller auf Kursänderungen als der SMA.
    """
    df = df.copy()
    df[f"EMA_{window}"] = df["Close"].ewm(span=window, adjust=False).mean()
    return df


def compute_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    RSI (Relative Strength Index) — Skala von 0 bis 100.

    - RSI > 70 → überkauft (Korrektur möglich)
    - RSI < 30 → überverkauft (Erholung möglich)
    - RSI 50   → neutral
    """
    df = df.copy()
    close = df["Close"]

    delta    = close.diff()
    gain     = delta.clip(lower=0)
    loss     = (-delta).clip(lower=0)

    avg_gain  = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss  = loss.ewm(com=period - 1, adjust=False).mean()

    rs        = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))

    return df


def compute_bollinger_bands(df: pd.DataFrame, window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    """
    Bollinger Bands — zeigen Volatilität um den gleitenden Durchschnitt.

    - Enge Bänder  → ruhiger Markt
    - Weite Bänder → unruhiger Markt
    - Kurs am oberen Band → möglicherweise überkauft
    - Kurs am unteren Band → möglicherweise überverkauft
    """
    df = df.copy()
    sma = df["Close"].rolling(window=window).mean()
    std = df["Close"].rolling(window=window).std()

    df["BB_middle"] = sma
    df["BB_upper"]  = sma + (num_std * std)
    df["BB_lower"]  = sma - (num_std * std)

    return df
