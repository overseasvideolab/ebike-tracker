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
    st.error("🔒 API keys missing! Please add them to Streamlit Secrets.")
    st.stop() 

# 2. Fetch Data (with Safety Brakes to prevent infinite loading)
@st.cache_data(ttl=3600) 
def fetch_all_rides(api_key, auth_token):
    all_rides = []
    offset = 0
    limit = 50 
    url = "https://ridewithgps.com/api/v1/trips.json"
    
    seen_ride_ids = set() # Safety net to remember rides we've already seen
    
    with st.spinner('Downloading complete ride history (this may take a moment)...'):
        while True:
            response = requests.get(url, auth=(api_key, auth_token), params={"limit": limit, "offset": offset})
            
            if response.status_code != 200:
                st.error(f"API Error: {response.status_code}")
                break
                
            data = response.json()
            
            # Safely extract the list of rides
            if isinstance(data, list):
                results = data
            elif isinstance(data, dict):
                results = data.get('results', data.get('trips', []))
            else:
                results = []
            
            # Brake #1: If the page is empty, we are done!
            if not results: 
                break
                
            # Brake #2: If we start seeing the exact same rides, the API is stuck. Bail out!
            first_ride_id = results[0].get('id')
            if first_ride_id in seen_ride_ids:
                break 
                
            # Add these new rides to our safety net and our master list
            for r in results:
                seen_ride_ids.add(r.get('id'))
                
            all_rides.extend(results)
            
            # Brake #3: If they gave us fewer rides than we asked for, it's the last page.
            if len(results) < limit:
                break
                
            # Turn the page
            offset += limit 
            
    return all_rides

raw_data = fetch_all_rides(API_KEY, AUTH_TOKEN)

# 3. Process Data & Build Dashboard
if raw_data and len(raw_data) > 0:
    df = pd.DataFrame(raw_data)
    
    # --- DATA CLEANUP ---
    # Convert distance from meters to km
    df['Distance_km'] = df.get('distance', 0) / 1000.0
    
    # Get the correct date column
    date_col = 'departed_at' if 'departed_at' in df.columns else 'created_at'
    df['Date'] = pd.to_datetime(df[date_col])
    
    # Create distinct time markers for analysis
    df['Just_Date'] = df['Date'].dt.date # Strips out time for "Days Ridden" count
    df['Year'] = df['Date'].dt.year.astype(str)
    df['Month_Num'] = df['Date'].dt.month
    df['Month_Name'] = df['Date'].dt.strftime('%B')
    df['Month_Year'] = df['Date'].dt.to_period('M').astype(str)
    
    # Sort chronologically
    df = df.sort_values(by='Date')

    # --- CURRENT TIME CONTEXT ---
    today = datetime.date.today()
    current_year = str(today.year)
    current_month_num = today.month
    current_month_name = today.strftime('%B')

    this_month_data = df[(df['Year'] == current_year) & (df['Month_Num'] == current_month_num)]
    this_year_data = df[df['Year'] == current_year]

    # --- KPI METRICS (Days vs Rides) ---
    st.subheader(f"🎯 Current Focus: {current_month_name} {current_year}")
    
    col1, col2, col3, col4 = st.columns(4)
    
    days_ridden_month = this_month_data['Just_Date'].nunique()
    days_ridden_year = this_year_data['Just_Date'].nunique()
    
    col1.metric(f"Distance in {current_month_name}", f"{this_month_data['Distance_km'].sum():.1f} km")
    col2.metric(f"Days Ridden in {current_month_name}", days_ridden_month, help="Count of unique calendar days")
    col3.metric("Total Distance This Year", f"{this_year_data['Distance_km'].sum():.1f} km")
    col4.metric("Total Days Ridden This Year", days_ridden_year)

    st.divider()

    # --- YEAR OVER YEAR (YoY) COMPARISON ---
    st.subheader(f"📊 Year-Over-Year: {current_month_name} Comparison")
    
    # Filter data to ONLY include the current month, across all years you've ridden
    yoy_data = df[df['Month_Num'] == current_month_num]
    
    if not yoy_data.empty:
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
    else:
        st.write(f"No historical data found for the month of {current_month_name} yet.")

    st.divider()

    # --- ALL-TIME MACRO TREND ---
    st.subheader("📈 All-Time Monthly Trend (Entire History)")
    all_time_stats = df.groupby('Month_Year')['Distance_km'].sum().reset_index()
    fig_all = px.bar(all_time_stats, x='Month_Year', y='Distance_km', 
                     labels={'Month_Year': 'Month', 'Distance_km': 'Distance (km)'})
    st.plotly_chart(fig_all, use_container_width=True)

else:
    st.info("No ride data could be found. Go for a ride!")