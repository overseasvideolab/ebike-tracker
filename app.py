import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import datetime

st.set_page_config(layout="wide", page_title="My E-Bike Pro Dashboard")
st.title("🚴‍♂️ E-Bike Analytics Engine")

# 1. Fetch Credentials
try:
    API_KEY = st.secrets["RWGPS_API_KEY"]
    AUTH_TOKEN = st.secrets["RWGPS_AUTH_TOKEN"]
except KeyError:
    st.error("🔒 API keys missing.")
    st.stop() 

# 2. Fetch Data (UPGRADED: Pagination loop to get ALL 2+ years of data)
@st.cache_data(ttl=3600) 
def fetch_all_rides(api_key, auth_token):
    all_rides = []
    offset = 0
    limit = 50 # Pull 50 rides at a time
    url = "https://ridewithgps.com/api/v1/trips.json"
    
    with st.spinner('Downloading complete ride history...'):
        while True:
            # We use 'offset' to skip the rides we already downloaded and get the next batch
            response = requests.get(url, auth=(api_key, auth_token), params={"limit": limit, "offset": offset})
            
            if response.status_code != 200:
                break
                
            data = response.json()
            results = data if isinstance(data, list) else data.get('results', data.get('trips', []))
            
            if not results: # If the page is empty, we have reached the end of your history!
                break
                
            all_rides.extend(results)
            offset += limit # Move to the next page
            
    return all_rides

raw_data = fetch_all_rides(API_KEY, AUTH_TOKEN)

# 3. Process Data
if raw_data and len(raw_data) > 0:
    df = pd.DataFrame(raw_data)
    
    # Clean data
    df['Distance_km'] = df.get('distance', 0) / 1000.0
    date_col = 'departed_at' if 'departed_at' in df.columns else 'created_at'
    df['Date'] = pd.to_datetime(df[date_col])
    
    # Create distinct time markers for analysis
    df['Just_Date'] = df['Date'].dt.date # Strips out the time, leaving just the day
    df['Year'] = df['Date'].dt.year.astype(str)
    df['Month_Num'] = df['Date'].dt.month
    df['Month_Name'] = df['Date'].dt.strftime('%B')
    df['Month_Year'] = df['Date'].dt.to_period('M').astype(str)
    
    df = df.sort_values(by='Date')

    # --- CURRENT TIME CONTEXT ---
    # Get today's date dynamically (Current date is March 2026)
    today = datetime.date.today()
    current_year = str(today.year)
    current_month_num = today.month
    current_month_name = today.strftime('%B')

    # --- FILTER FOR CURRENT MONTH / YEAR ---
    this_month_data = df[(df['Year'] == current_year) & (df['Month_Num'] == current_month_num)]
    this_year_data = df[df['Year'] == current_year]

    # --- KPI METRICS (Days vs Rides) ---
    st.subheader(f"🎯 Current Focus: {current_month_name} {current_year}")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Calculate unique days ridden
    days_ridden_month = this_month_data['Just_Date'].nunique()
    days_ridden_year = this_year_data['Just_Date'].nunique()
    
    col1.metric(f"Distance in {current_month_name}", f"{this_month_data['Distance_km'].sum():.1f} km")
    col2.metric(f"Days Ridden in {current_month_name}", days_ridden_month, help="Count of unique calendar days")
    col3.metric("Total Distance This Year", f"{this_year_data['Distance_km'].sum():.1f} km")
    col4.metric("Total Days Ridden This Year", days_ridden_year)

    st.divider()

    # --- YEAR OVER YEAR (YoY) COMPARISON ---
    st.subheader(f"📊 Year-Over-Year: {current_month_name} Comparison")
    
    # Filter data to ONLY include the current month, across all years
    yoy_data = df[df['Month_Num'] == current_month_num]
    yoy_stats = yoy_data.groupby('Year').agg(
        Total_Distance=('Distance_km', 'sum'),
        Days_Ridden=('Just_Date', 'nunique')
    ).reset_index()

    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        fig_yoy_dist = px.bar(yoy_stats, x='Year', y='Total_Distance', 
                              title=f"{current_month_name} Distance (km) by Year",
                              text_auto='.1f', color_discrete_sequence=['#FF4B4B'])
        st.plotly_chart(fig_yoy_dist, use_container_width=True)
        
    with chart_col2:
        fig_yoy_days = px.bar(yoy_stats, x='Year', y='Days_Ridden', 
                              title=f"{current_month_name} Days Ridden by Year",
                              text_auto=True, color_discrete_sequence=['#1f77b4'])
        st.plotly_chart(fig_yoy_days, use_container_width=True)

    st.divider()

    # --- ALL-TIME MACRO TREND ---
    st.subheader("📈 All-Time Monthly Trend (Entire History)")
    all_time_stats = df.groupby('Month_Year')['Distance_km'].sum().reset_index()
    fig_all = px.bar(all_time_stats, x='Month_Year', y='Distance_km', 
                     labels={'Month_Year': 'Month', 'Distance_km': 'Distance (km)'})
    st.plotly_chart(fig_all, use_container_width=True)

else:
    st.info("No ride data could be found.")