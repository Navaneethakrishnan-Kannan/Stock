import streamlit as st
import pandas as pd
import plotly.express as px
from pyxirr import xirr
from datetime import datetime

try:
    import yfinance as yf
except ModuleNotFoundError:
    st.error(
        "Missing dependency `yfinance`.\n\n"
        "Install it in this project's venv:\n"
        "`venv\\Scripts\\python -m pip install -r requirements.txt`"
    )
    st.stop()

# Page config
st.set_page_config(page_title="Investment Portfolio", layout="wide")

st.title("📈 Portfolio Dashboard")

# 1. Data Setup
@st.cache_data
def get_base_data():
    data = {
        'Stock name': ['Wipro', 'TCS', 'Karnataka Bank', 'Dr.Reddy', 'ITC'],
        'Ticker': ['WIPRO.NS', 'TCS.NS', 'KTKBANK.NS', 'DRREDDY.NS', 'ITC.NS'],
        'Bought price': [238, 2850, 162, 1280, 200],
        # Note: Ensure these dates are NOT in the future relative to today's date
        'Bought date': ['2024-01-08', '2024-02-20', '2023-06-18', '2023-11-20', '2023-08-10'],
        'Quantity': [1100, 120, 1500, 500, 200]
    }
    df = pd.DataFrame(data)
    df['Bought date'] = pd.to_datetime(df['Bought date'])
    return df

@st.cache_data(ttl=3600)
def get_portfolio_stats(df):
    results = []
    today = datetime.now()

    for _, row in df.iterrows():
        try:
            ticker = yf.Ticker(row['Ticker'])
            info = ticker.info
            
            current_price = info.get('currentPrice', row['Bought price']) # Fallback to bought price if API fails
            curr_div_yield = info.get('trailingAnnualDividendYield', 0)
            annual_div = info.get('dividendRate', 0)

            invested_value = row['Bought price'] * row['Quantity']
            current_value = current_price * row['Quantity']
            abs_return = current_value - invested_value
            pct_return = (abs_return / invested_value) * 100 if invested_value > 0 else 0
            my_div_yield = (annual_div / row['Bought price']) * 100 if row['Bought price'] > 0 else 0

            # Cash flows for XIRR
            cash_flows = {row['Bought date']: -invested_value, today: current_value}
            stock_xirr = xirr(cash_flows) * 100 if current_value > 0 else 0

            results.append({
                'Stock': row['Stock name'],
                'Sector': info.get('sector', 'Unknown'),
                'Cap': info.get('marketCap', 0),
                'Current Price': current_price,
                'Curr Div Yield (%)': round((curr_div_yield or 0) * 100, 2),
                'My Div Yield (%)': round(my_div_yield, 2),
                '% Return': round(pct_return, 2),
                'Absolute Return': round(abs_return, 2),
                'XIRR (%)': round(stock_xirr, 2),
                'Current Value': current_value,
                'Invested Value': invested_value,
                'Bought Date': row['Bought date']
            })
        except Exception as e:
            st.warning(f"Could not update {row['Stock name']}: {e}")
            continue

    return pd.DataFrame(results)

# Run Logic
base_df = get_base_data()
portfolio_df = get_portfolio_stats(base_df)

if not portfolio_df.empty:
    # Calculations
    total_invested = portfolio_df['Invested Value'].sum()
    total_current = portfolio_df['Current Value'].sum()
    
    agg_flows = {}
    for _, row in portfolio_df.iterrows():
        agg_flows[row['Bought Date']] = agg_flows.get(row['Bought Date'], 0) - row['Invested Value']
    agg_flows[datetime.now()] = total_current
    
    try:
        portfolio_xirr = xirr(agg_flows) * 100
    except:
        portfolio_xirr = 0

    # Layout
    m1, m2, m3 = st.columns(3)
    m1.metric("Invested", f"₹{total_invested:,.0f}")
    m2.metric("Current", f"₹{total_current:,.0f}", f"{(total_current-total_invested)/total_invested*100:.2f}%")
    m3.metric("Overall XIRR", f"{portfolio_xirr:.2f}%")

    st.dataframe(portfolio_df[['Stock', 'Current Price', '% Return', 'XIRR (%)', 'Current Value']], use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        fig1 = px.pie(portfolio_df, values='Current Value', names='Sector', title="Sector Allocation")
        st.plotly_chart(fig1, use_container_width=True)
    with col2:
        # Avoid qcut error by checking unique values
        if portfolio_df['Cap'].nunique() > 1:
            portfolio_df['Cap Size'] = pd.qcut(portfolio_df['Cap'], q=min(3, len(portfolio_df)), labels=['Small', 'Mid', 'Large'][:min(3, len(portfolio_df))])
            fig2 = px.pie(portfolio_df, values='Current Value', names='Cap Size', title="Market Cap Allocation")
            st.plotly_chart(fig2, use_container_width=True)
else:
    st.error("No data found. Check your Internet connection or Ticker symbols.")
