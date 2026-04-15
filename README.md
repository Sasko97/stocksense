# StockSense 📈

An interactive stock market analysis dashboard built with Python and Streamlit.

## Features (Phase 1)
- Real-time historical price data via Yahoo Finance (no API key required)
- Interactive candlestick chart with zoom and hover
- Volume overlay
- Cumulative return chart
- Key metrics: current price, 52-week high/low, sector

## Planned Features
- Phase 2: Technical indicators (RSI, Bollinger Bands, Moving Averages)
- Phase 3: ML-based price forecasting with confidence intervals
- Phase 4: Portfolio comparison and Sharpe ratio

## Getting Started

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/stocksense.git
cd stocksense

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the dashboard
streamlit run app.py
```

## Tech Stack
- [Streamlit](https://streamlit.io/) — web dashboard framework
- [yfinance](https://github.com/ranaroussi/yfinance) — Yahoo Finance data
- [Plotly](https://plotly.com/python/) — interactive charts
- [Pandas](https://pandas.pydata.org/) — data processing

## Project Structure
```
stocksense/
├── app.py          # Streamlit dashboard (main entry point)
├── data.py         # Data fetching and processing logic
├── requirements.txt
└── README.md
```

## Background
Built as a learning project during my Master's in Advanced Manufacturing Technologies (Vienna). Combining financial data analysis with Python fundamentals learned alongside engineering and business coursework.
