import streamlit as st
import pandas as pd
import requests
import plotly.express as px # Our new, powerful charting library!

st.set_page_config(layout="wide") # Makes the app use the full width of your screen
st.title("🚴‍♂️ My E-Bike Pro Dashboard")

# 1. Fetch Credentials
try:
    API_KEY = st.secrets["RWGPS_API_KEY"]
    AUTH_TOKEN = st.secrets["RWGPS_AUTH_TOKEN"]
except KeyError:
    st.error("🔒 API keys not found in Streamlit Secrets.")
    st.stop() 

# 2. Fetch Data (Upgraded to pull MORE data)
@st.cache_data(ttl=3600) 
def fetch_rides(api_key, auth_token):
    url = "https://ridewithgps.com/api/v1/trips.json"
    # We add 'limit' and 'per_page' to politely ask the API for a much larger chunk of history
    response = requests.get(url, auth=(api_key, auth_token), params={"limit": 200, "per_page": 200})
    
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch data. Error: {response.status_code}")
        return None

raw_data = fetch_rides(API_KEY, AUTH_TOKEN)

# 3. Process Data
if raw_data is not None:
    rides_list = []
    if isinstance(raw_data, list):
        rides_list = raw_data
    elif isinstance(raw_data, dict):
        rides_list = raw_data.get('results', raw_data.get('trips', []))

    if len(rides_list) > 0:
        df = pd.DataFrame(rides_list)
        
        # Calculate Kilometers
        df['Distance_km'] = df.get('distance', 0) / 1000.0
        
        # Look for elevation data (usually provided in meters)
        df['Elevation_m'] = df.get('elevation_gain', 0)
        
        # Clean up Dates
        date_col = 'departed_at' if 'departed_at' in df.columns else 'created_at'
        df['Date'] = pd.to_datetime(df[date_col])
        df['Month'] = df['Date'].dt.to_period('M').astype(str)
        
        # Sort by date so our trends flow chronologically
        df = df.sort_values(by='Date')
        
        # --- ADVANCED STATS & ANALYSIS ---
        st.divider()
        st.subheader("🏆 All-Time Personal Bests & Averages")
        
        total_dist = df['Distance_km'].sum()
        longest_ride = df['Distance_km'].max()
        avg_ride = df['Distance_km'].mean()
        total_elev = df['Elevation_m'].sum()
        
        # Create 4 columns for our big metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Distance", f"{total_dist:,.1f} km")
        m2.metric("Longest Single Ride", f"{longest_ride:,.1f} km")
        m3.metric("Average Ride Length", f"{avg_ride:,.1f} km")
        m4.metric("Total Elevation Climbed", f"{total_elev:,.0f} m")

        # --- INTERACTIVE CHARTS ---
        st.divider()
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.subheader("📅 Monthly Distance Breakdown")
            monthly_stats = df.groupby('Month')['Distance_km'].sum().reset_index()
            # Plotly creates a bar chart with the numbers printed directly on the bars (text_auto)
            fig_bar = px.bar(monthly_stats, x='Month', y='Distance_km', 
                             text_auto='.1f', 
                             labels={'Distance_km': 'Distance (km)', 'Month': 'Month'},
                             color_discrete_sequence=['#FF4B4B'])
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with col_chart2:
            st.subheader("📈 Cumulative Distance Trend")
            # Calculate how your total distance grows over time
            df['Cumulative_Distance'] = df['Distance_km'].cumsum()
            fig_line = px.line(df, x='Date', y='Cumulative_Distance', 
                               labels={'Cumulative_Distance': 'Total km Ridden', 'Date': 'Date'},
                               color_discrete_sequence=['#1f77b4'])
            # Fill the area under the line for a cool visual effect
            fig_line.update_traces(fill='tozeroy') 
            st.plotly_chart(fig_line, use_container_width=True)

    else:
        st.info("No rides found in the data package.")