import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from pyxirr import xirr
from datetime import datetime

st.set_page_config(page_title="Investment Portfolio", layout="wide")
st.title("📈 Portfolio Dashboard")

# 1. Base Portfolio Data
@st.cache_data
def get_base_data():
    data = {
        'Stock name': ['Wipro', 'TCS', 'Karnataka Bank', 'Dr.Reddy', 'ITC'],
        'Ticker': ['WIPRO.NS', 'TCS.NS', 'KTKBANK.NS', 'DRREDDY.NS', 'ITC.NS'],
        'Bought price': [238, 2850, 162, 1280, 200],
        'Bought date': ['2024-01-08', '2024-02-20', '2023-06-18', '2023-11-20', '2023-08-10'],
        'Quantity': [1100, 120, 1500, 500, 200]
    }
    df = pd.DataFrame(data)
    df['Bought date'] = pd.to_datetime(df['Bought date'])
    return df

@st.cache_data(ttl=3600)
def get_live_prices(tickers):
    # Batch download is faster and helps avoid rate limits
    data = yf.download(tickers, period="1d", interval="1m", progress=False)
    # Get the last valid price for each ticker
    return data['Close'].iloc[-1].to_dict()

# Main App Logic
df = get_base_data()
tickers_list = df['Ticker'].tolist()

try:
    with st.spinner('Fetching live prices...'):
        current_prices = get_live_prices(tickers_list)
    
    results = []
    today = datetime.now()

    for _, row in df.iterrows():
        # Fallback to bought price if the ticker isn't in the returned data
        ticker_symbol = row['Ticker']
        
        # yf.download might return a Series if only 1 ticker, or a Dict-like for multiple
        curr_price = current_prices.get(ticker_symbol, row['Bought price'])
        
        invested_val = row['Bought price'] * row['Quantity']
        current_val = curr_price * row['Quantity']
        abs_ret = current_val - invested_val
        pct_ret = (abs_ret / invested_val) * 100 if invested_val > 0 else 0
        
        # Cash flows for XIRR
        cash_flows = {row['Bought date']: -invested_val, today: current_val}
        try:
            stock_xirr = xirr(cash_flows) * 100
        except:
            stock_xirr = 0

        results.append({
            'Stock': row['Stock name'],
            'Current Price': round(curr_price, 2),
            '% Return': round(pct_ret, 2),
            'Absolute Return': round(abs_ret, 2),
            'XIRR (%)': round(stock_xirr, 2),
            'Current Value': current_val,
            'Invested Value': invested_val,
            'Bought Date': row['Bought date']
        })

    portfolio_df = pd.DataFrame(results)

    # UI Metrics
    total_inv = portfolio_df['Invested Value'].sum()
    total_curr = portfolio_df['Current Value'].sum()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Invested", f"₹{total_inv:,.0f}")
    m2.metric("Current Value", f"₹{total_curr:,.0f}", f"{((total_curr/total_inv)-1)*100:.2f}%")
    
    # Portfolio XIRR
    agg_flows = {}
    for _, row in portfolio_df.iterrows():
        agg_flows[row['Bought Date']] = agg_flows.get(row['Bought Date'], 0) - row['Invested Value']
    agg_flows[today] = total_curr
    total_xirr = xirr(agg_flows) * 100
    m3.metric("Overall XIRR", f"{total_xirr:.2f}%")

    st.divider()
    st.dataframe(portfolio_df[['Stock', 'Current Price', '% Return', 'XIRR (%)', 'Current Value']], use_container_width=True)

    # Simple Allocation Chart
    fig = px.pie(portfolio_df, values='Current Value', names='Stock', title="Stock Allocation")
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Error fetching data: {e}")
    st.info("Yahoo Finance is blocking requests. Try refreshing in 1-2 minutes.")
