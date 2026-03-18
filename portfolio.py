import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from pyxirr import xirr
from datetime import datetime
import plotly.express as px

st.set_page_config(page_title="NSE Portfolio Tracker", layout="wide")
st.title("📊 Live NSE Portfolio (Google Finance)")

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

@st.cache_data(ttl=300)
def scrape_google_finance(ticker):
    url = f"https://www.google.com/finance/quote/{ticker}:NSE"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Finding Price
        price_element = soup.find("div", {"class": "YMlKec fxKbKc"})
        price = float(price_element.text.replace("₹", "").replace(",", "")) if price_element else None
        
        # Finding Yield
        div_yield = 0.0
        info_items = soup.find_all('div', {'class': 'mfs7Fc'})
        for item in info_items:
            if 'Yield' in item.text:
                val = item.find_next_sibling('div').text
                if val != '-':
                    div_yield = float(val.replace('%', ''))
                break
        return price, div_yield
    except:
        return None, 0.0

# --- MAIN LOGIC ---
portfolio_input = get_my_portfolio()
results = []
today = datetime.now()

with st.spinner("Scraping live data..."):
    for _, row in portfolio_input.iterrows():
        price, dy = scrape_google_finance(row['Ticker'])
        
        # Use live price if available, otherwise fallback to bought price
        curr_price = price if price is not None else row['Bought price']
        
        invested = row['Bought price'] * row['Quantity']
        current_val = curr_price * row['Quantity']
        abs_return = current_val - invested
        pct_return = (abs_return / invested) * 100 if invested > 0 else 0
        
        # XIRR Calculation
        cash_flows = {row['Bought date']: -invested, today: current_val}
        try:
            stock_xirr = xirr(cash_flows) * 100
        except:
            stock_xirr = 0

        results.append({
            'Stock': row['Stock'],
            'Bought Date': row['Bought date'].date(),
            'Current Price': curr_price,
            'Div Yield (%)': dy,
            'Absolute Return': round(abs_return, 2),
            '% Return': round(pct_return, 2),
            'XIRR (%)': round(stock_xirr, 2),
            'Current Value': current_val,
            'Invested Value': invested
        })

# Create the DataFrame
pdf = pd.DataFrame(results)

# --- DISPLAY LOGIC (Only runs if pdf is not empty) ---
if not pdf.empty:
    t_inv = pdf['Invested Value'].sum()
    t_curr = pdf['Current Value'].sum()
    t_profit = t_curr - t_inv

    # Top Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Invested", f"₹{t_inv:,.0f}")
    m2.metric("Current Value", f"₹{t_curr:,.0f}", f"{(t_profit/t_inv*100):.2f}%")
    m3.metric("Absolute Profit", f"₹{t_profit:,.0f}")

    st.divider()

    # Performance Table
    st.subheader("Stock Performance")
    def color_negative_red(val):
        color = 'red' if val < 0 else 'green'
        return f'color: {color}'

    st.dataframe(
        pdf[['Stock', 'Bought Date', 'Current Price', 'Div Yield (%)', 'Absolute Return', '% Return', 'XIRR (%)']]
        .style.map(color_negative_red, subset=['Absolute Return', '% Return', 'XIRR (%)']),
        use_container_width=True
    )

    # Pie Chart
    st.divider()
    fig = px.pie(pdf, values='Current Value', names='Stock', title="Portfolio Allocation", hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("Failed to generate portfolio data. Please check your internet connection.")
