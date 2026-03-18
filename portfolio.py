import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from pyxirr import xirr
from datetime import datetime

# Page config
st.set_page_config(page_title="Investment Portfolio Tracker", layout="wide")

st.title("📈 My Investment Scoreboard")

# 1. Define Portfolio Data (In a real app, you might use st.file_uploader for a CSV)
@st.cache_data
def get_base_data():
    data = {
        'Stock name': ['Wipro', 'TCS', 'Karnataka Bank', 'Dr.Reddy', 'ITC'],
        'Ticker': ['WIPRO.NS', 'TCS.NS', 'KTKBANK.NS', 'DRREDDY.NS', 'ITC.NS'],
        'Bought price': [238, 2850, 162, 1280, 200],
        'Bought date': ['2026-01-08', '2026-02-20', '2025-06-18', '2025-11-20', '2023-08-10'],
        'Quantity': [1100, 120, 1500, 500, 200]
    }
    df = pd.DataFrame(data)
    df['Bought date'] = pd.to_datetime(df['Bought date'])
    return df

@st.cache_data(ttl=3600) # Cache data for 1 hour to save API limits
def get_portfolio_stats(df):
    results = []
    today = datetime.now()

    for _, row in df.iterrows():
        ticker = yf.Ticker(row['Ticker'])
        info = ticker.info

        current_price = info.get('currentPrice', 0)
        curr_div_yield = info.get('trailingAnnualDividendYield', 0)
        annual_div = info.get('dividendRate', 0)

        invested_value = row['Bought price'] * row['Quantity']
        current_value = current_price * row['Quantity']
        abs_return = current_value - invested_value
        pct_return = (abs_return / invested_value) * 100 if invested_value > 0 else 0
        my_div_yield = (annual_div / row['Bought price']) * 100 if row['Bought price'] > 0 else 0

        # Individual XIRR
        cash_flows = {row['Bought date']: -invested_value, today: current_value}
        try:
            stock_xirr = xirr(cash_flows) * 100
        except:
            stock_xirr = 0

        results.append({
            'Stock': row['Stock name'],
            'Sector': info.get('sector', 'Unknown'),
            'Cap': info.get('marketCap', 0),
            'Current Price': current_price,
            'Curr Div Yield (%)': round(curr_div_yield * 100, 2),
            'My Div Yield (%)': round(my_div_yield, 2),
            '% Return': round(pct_return, 2),
            'Absolute Return': round(abs_return, 2),
            'XIRR (%)': round(stock_xirr, 2),
            'Current Value': current_value,
            'Invested Value': invested_value,
            'Bought Date': row['Bought date']
        })

    return pd.DataFrame(results)

# Execute Data Retrieval
base_df = get_base_data()

with st.spinner('Fetching live market data...'):
    portfolio_df = get_portfolio_stats(base_df)

# --- CALCULATIONS ---
total_invested = portfolio_df['Invested Value'].sum()
total_current = portfolio_df['Current Value'].sum()
total_profit = total_current - total_invested

# Aggregate XIRR
agg_flows = {}
for _, row in portfolio_df.iterrows():
    agg_flows[row['Bought Date']] = agg_flows.get(row['Bought Date'], 0) - row['Invested Value']
agg_flows[datetime.now()] = total_current
portfolio_xirr = xirr(agg_flows) * 100

# --- DASHBOARD LAYOUT ---
# Top Metrics
m1, m2, m3, m4 = st.columns(4)
m1.metric("Invested Value", f"₹{total_invested:,.0f}")
m2.metric("Current Value", f"₹{total_current:,.0f}", f"{((total_current/total_invested)-1)*100:.2f}%")
m3.metric("Total Profit", f"₹{total_profit:,.0f}")
m4.metric("Portfolio XIRR", f"{portfolio_xirr:.2f}%")

st.divider()

# Detailed Table
st.subheader("Stock Performance Breakdown")
# Highlighting positive/negative returns
st.dataframe(portfolio_df[['Stock', 'Current Price', 'Curr Div Yield (%)', 'My Div Yield (%)', '% Return', 'Absolute Return', 'XIRR (%)']], 
             use_container_width=True)

st.divider()

# Visualizations
col1, col2 = st.columns(2)

with col1:
    fig_sector = px.pie(portfolio_df, values='Current Value', names='Sector', title='Sector-wise Allocation', hole=0.4)
    st.plotly_chart(fig_sector, use_container_width=True)

with col2:
    # Cap size logic
    portfolio_df['Cap Size'] = pd.qcut(portfolio_df['Cap'], q=min(3, len(portfolio_df)), labels=['Small Cap', 'Mid Cap', 'Large Cap'][:min(3, len(portfolio_df))])
    fig_cap = px.pie(portfolio_df, values='Current Value', names='Cap Size', title='Market Cap Allocation', hole=0.4)
    st.plotly_chart(fig_cap, use_container_width=True)
