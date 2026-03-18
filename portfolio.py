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
def get_portfolio_data(tickers_list):
    # Fetching multiple tickers at once to minimize API calls
    tickers_obj = yf.Tickers(' '.join(tickers_list))
    prices = {}
    div_yields = {}
    
    for ticker in tickers_list:
        try:
            info = tickers_obj.tickers[ticker].info
            prices[ticker] = info.get('currentPrice', 0)
            # Fetching trailingAnnualDividendYield (stored as decimal, e.g., 0.02)
            div_yields[ticker] = info.get('trailingAnnualDividendYield', 0)
        except:
            prices[ticker] = 0
            div_yields[ticker] = 0
            
    return prices, div_yields

# --- Execution ---
df = get_base_data()
tickers_list = df['Ticker'].tolist()

try:
    with st.spinner('Fetching Live Market & Dividend Data...'):
        current_prices, dividend_yields = get_portfolio_data(tickers_list)
    
    results = []
    today = datetime.now()

    for _, row in df.iterrows():
        ticker_symbol = row['Ticker']
        curr_price = current_prices.get(ticker_symbol, row['Bought price'])
        div_yield = dividend_yields.get(ticker_symbol, 0)
        
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
            'Bought Price': row['Bought price'],
            'Current Price': round(curr_price, 2),
            'Curr Div Yield (%)': round(div_yield * 100, 2), # Convert to percentage
            'Absolute Return': round(abs_ret, 2),
            '% Return': round(pct_ret, 2),
            'XIRR (%)': round(stock_xirr, 2),
            'Current Value': round(current_val, 2),
            'Invested Value': invested_val,
            'Bought Date': row['Bought date'].date()
        })

    portfolio_df = pd.DataFrame(results)

    # --- TOP METRICS ---
    total_inv = portfolio_df['Invested Value'].sum()
    total_curr = portfolio_df['Current Value'].sum()
    total_abs_return = total_curr - total_inv
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Invested", f"₹{total_inv:,.0f}")
    m2.metric("Current Value", f"₹{total_curr:,.0f}")
    m3.metric("Total Profit/Loss", f"₹{total_abs_return:,.0f}", f"{((total_curr/total_inv)-1)*100:.2f}%")
    
    # Portfolio XIRR
    agg_flows = {}
    for _, row in df.iterrows():
        inv_amt = row['Bought price'] * row['Quantity']
        agg_flows[row['Bought date']] = agg_flows.get(row['Bought date'], 0) - inv_amt
    agg_flows[today] = total_curr
    total_portfolio_xirr = xirr(agg_flows) * 100
    m4.metric("Portfolio XIRR", f"{total_portfolio_xirr:.2f}%")

    st.divider()

    # --- DATAFRAME DISPLAY ---
    st.subheader("Performance Breakdown")
    
    def color_returns(val):
        if isinstance(val, (int, float)):
            color = 'red' if val < 0 else 'green'
            return f'color: {color}'
        return ''

    # Define columns to display
    display_cols = ['Stock', 'Bought Date', 'Current Price', 'Curr Div Yield (%)', 'Absolute Return', '% Return', 'XIRR (%)']
    
    st.dataframe(
        portfolio_df[display_cols].style.map(color_returns, subset=['Absolute Return', '% Return', 'XIRR (%)'])
        .format(precision=2),
        use_container_width=True
    )

    # --- VISUALS ---
    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        fig1 = px.pie(portfolio_df, values='Current Value', names='Stock', 
                     title="Portfolio Weightage", hole=0.4)
        st.plotly_chart(fig1, use_container_width=True)
        
    with col2:
        fig2 = px.bar(portfolio_df, x='Stock', y='Curr Div Yield (%)', 
                      title="Dividend Yield Comparison", color='Stock')
        st.plotly_chart(fig2, use_container_width=True)

except Exception as e:
    st.error(f"Data Fetch Error: {e}")
    st.info("Yahoo Finance rate limit hit. This usually resets every few minutes.")
