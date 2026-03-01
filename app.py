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

# 2. Fetch Data (UPGRADED: Extreme Memory Filter)
@st.cache_data(ttl=3600) 
def fetch_lightweight_rides(api_key, auth_token):
    all_rides_filtered = []
    offset = 0
    limit = 50 
    url = "https://ridewithgps.com/api/v1/trips.json"
    seen_ride_ids = set() 
    
    while True:
        response = requests.get(url, auth=(api_key, auth_token), params={"limit": limit, "offset": offset})
        if response.status_code != 200:
            break
            
        data = response.json()
        results = data if isinstance(data, list) else data.get('results', data.get('trips', []))
        
        if not results: 
            break
            
        first_ride_id = results[0].get('id')
        if first_ride_id in seen_ride_ids:
            break 
            
        # --- THE MEMORY FILTER ---
        for r in results:
            ride_id = r.get('id')
            seen_ride_ids.add(ride_id)
            
            # We ONLY save the tiny bits of text we need, throwing away the heavy map data
            date_val = r.get('departed_at', r.get('created_at'))
            dist_val = r.get('distance', 0)
            
            lightweight_ride = {
                'id': ride_id,
                'departed_at': date_val,
                'distance': dist_val
            }
            all_rides_filtered.append(lightweight_ride)
            
        if len(results) < limit:
            break
            
        offset += limit 
            
    return all_rides_filtered

# 3. Process Data & Build Dashboard
# We moved the spinner OUTSIDE the cache function to prevent memory leaks!
with st.spinner("Crunching your historical data..."):
    raw_data = fetch_lightweight_rides(API_KEY, AUTH_TOKEN)

if raw_data and len(raw_data) > 0:
    df = pd.DataFrame(raw_data)
    
    # Clean data
    df['Distance_km'] = df['distance'] / 1000.0
    df['Date'] = pd.to_datetime(df['departed_at'])
    
    # Create time markers
    df['Just_Date'] = df['Date'].dt.date 
    df['Year'] = df['Date'].dt.year.astype(str)
    df['Month_Num'] = df['Date'].dt.month
    df['Month_Name'] = df['Date'].dt.strftime('%B')
    df['Month_Year'] = df['Date'].dt.to_period('M').astype(str)
    df = df.sort_values(by='Date')

    # Current time setup
    today = datetime.date.today()
    current_year = str(today.year)
    current_month_num = today.month
    current_month_name = today.strftime('%B')

    this_month_data = df[(df['Year'] == current_year) & (df['Month_Num'] == current_month_num)]
    this_year_data = df[df['Year'] == current_year]

    # --- KPI METRICS ---
    st.subheader(f"🎯 Current Focus: {current_month_name} {current_year}")
    col1, col2, col3, col4 = st.columns(4)
    
    days_ridden_month = this_month_data['Just_Date'].nunique()
    days_ridden_year = this_year_data['Just_Date'].nunique()
    
    col1.metric(f"Distance in {current_month_name}", f"{this_month_data['Distance_km'].sum():.1f} km")
    col2.metric(f"Days Ridden in {current_month_name}", days_ridden_month)
    col3.metric("Total Distance This Year", f"{this_year_data['Distance_km'].sum():.1f} km")
    col4.metric("Total Days Ridden This Year", days_ridden_year)

    st.divider()

    # --- YEAR OVER YEAR (YoY) COMPARISON ---
    st.subheader(f"📊 Year-Over-Year: {current_month_name} Comparison")
    
    yoy_data = df[df['Month_Num'] == current_month_num]
    if not yoy_data.empty:
        yoy_stats = yoy_data.groupby('Year').agg(
            Total_Distance=('Distance_km', 'sum'),
            Days_Ridden=('Just_Date', 'nunique')
        ).reset_index()

        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            fig_yoy_dist = px.bar(yoy_stats, x='Year', y='Total_Distance', 
                                  title=f"{current_month_name} Total Distance",
                                  text_auto='.1f', color_discrete_sequence=['#FF4B4B'])
            fig_yoy_dist.update_xaxes(type='category', title_text='Year')
            st.plotly_chart(fig_yoy_dist, use_container_width=True)
            
        with chart_col2:
            fig_yoy_days = px.bar(yoy_stats, x='Year', y='Days_Ridden', 
                                  title=f"{current_month_name} Days Ridden",
                                  text_auto=True, color_discrete_sequence=['#1f77b4'])
            fig_yoy_days.update_xaxes(type='category', title_text='Year')
            st.plotly_chart(fig_yoy_days, use_container_width=True)
    else:
        st.write(f"No historical data found for {current_month_name}.")

    st.divider()

    # --- ALL-TIME MACRO TREND ---
    st.subheader("📈 All-Time Monthly Trend (Entire History)")
    all_time_stats = df.groupby('Month_Year')['Distance_km'].sum().reset_index()
    
    fig_all = px.bar(all_time_stats, x='Month_Year', y='Distance_km', 
                     title="Kilometers Ridden per Month",
                     labels={'Month_Year': 'Month', 'Distance_km': 'Distance (km)'},
                     text_auto='.1f') 
    
    fig_all.update_xaxes(type='category', tickangle=-45)
    st.plotly_chart(fig_all, use_container_width=True)

else:
    st.info("No ride data could be found.")