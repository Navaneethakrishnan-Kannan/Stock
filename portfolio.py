import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from pyxirr import xirr
from datetime import datetime

st.set_page_config(page_title="Direct Google Finance Tracker", layout="wide")
st.title("📊 Live NSE Portfolio (via Google Finance)")

# 1. Your Purchase Data
def get_my_portfolio():
    data = {
        'Stock': ['Wipro', 'TCS', 'Karnataka Bank', 'Dr.Reddy', 'ITC'],
        'Ticker': ['WIPRO', 'TCS', 'KTKBANK', 'DRREDDY', 'ITC'],
        'Bought price': [238, 2850, 162, 1280, 200],
        'Bought date': ['2024-01-08', '2024-02-20', '2023-06-18', '2023-11-20', '2023-08-10'],
        'Quantity': [1100, 120, 1500, 500, 200]
    }
    df = pd.DataFrame(data)
    df['Bought date'] = pd.to_datetime(df['Bought date'])
    return df

@st.cache_data(ttl=300) # Cache for 5 minutes
def scrape_google_finance(ticker):
    """Scrapes Price and Div Yield directly from Google Finance"""
    url = f"https://www.google.com/finance/quote/{ticker}:NSE"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get Price
        price_class = "YMlKec fxKbKc" # This is Google's CSS class for price
        price_text = soup.find("div", {"class": price_class}).text
        price = float(price_text.replace("₹", "").replace(",", ""))
        
        # Get Dividend Yield (Found in the info table)
        # We look for the div that contains 'Yield' and get its sibling
        div_yield = 0.0
        for item in soup.find_all('div', {'class': 'mfs7Fc'}):
            if 'Yield' in item.text:
                yield_val = item.find_next_sibling('div').text
                if yield_val != '-':
                    div_yield = float(yield_val.replace('%', ''))
                break
                
        return price, div_yield
    except Exception as e:
        return None, None

# --- Main Logic ---
portfolio = get_my_portfolio()
results = []
today = datetime.now()

with st.spinner("Scraping live data from Google Finance..."):
    for _, row in portfolio.iterrows():
        price, dy = scrape_google_finance(row['Ticker'])
        
        # Fallback if scraping fails
        curr_price = price if price else row['Bought price']
        curr_yield = dy if dy else 0.0
        
        invested = row['Bought price'] * row['Quantity']
        current_val = curr_price * row['Quantity']
        abs_return = current_val - invested
        pct_return = (abs_return / invested) * 100
        
        # XIRR
        cash_flows = {row['Bought date']: -invested, today: current_val}
        try:
            stock_xirr = xirr(cash_flows) * 100
        except:
            stock_xirr = 0

        results.append({
            'Stock': row['Stock'],
            'Current Price': curr_price,
            'Div Yield (%)': curr_yield,
            'Absolute Return': round(abs_return, 2),
            '% Return': round(pct_return, 2),
            'XIRR (%)': round(stock_xirr, 2),
            'Current Value': current_val,
            'Invested Value': invested,
            'Bought Date': row['Bought date'].date()
        })

pdf = pd.DataFrame(results)

# --- Display Dashboard ---
t_inv = pdf['Invested Value'].sum()
t_curr = pdf['Current Value'].sum()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Invested", f"₹{t_inv:,.0f}")
m2.metric("Portfolio Value", f"₹{t_curr:,.0f}")
m3.metric("Absolute Profit", f"₹{t_curr - t_inv:,.0f}", f"{((t_curr/t_inv)-1)*100:.2f}%")

# Aggregate XIRR
agg_flows = {}
for _, row in portfolio.iterrows():
    inv_amt = row['Bought price'] * row['Quantity']
    agg_flows[row['Bought date']] = agg_flows.get(row['Bought date'], 0) - inv_amt
agg_flows[today] = t_curr
try:
    total_xirr = xirr(agg_flows) * 100
    m4.metric("Overall XIRR", f"{total_xirr:.2f}%")
except:
    m4.metric("Overall XIRR", "0%")

st.divider()

# Styled Table
def color_val(val):
    color = 'red' if val < 0 else 'green'
    return f'color: {color}'

st.subheader("Performance Breakdown")
st.dataframe(
    pdf[['Stock', 'Bought Date', 'Current Price', 'Div Yield (%)', 'Absolute Return', '% Return', 'XIRR (%)']]
    .style.map(color_val, subset=['Absolute Return', '% Return', 'XIRR (%)']),
    use_container_width=True
)

# Chart
fig = px.pie(pdf, values='Current Value', names='Stock', title="Portfolio Weightage", hole=0.5)
st.plotly_chart(fig, use_container_width=True)
