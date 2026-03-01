import streamlit as st
import pandas as pd
import requests

# 1. App Header
st.title("🚴‍♂️ My E-Bike Ride Tracker")
st.write("Live data pulled directly from your Ride with GPS account!")

# 2. Securely fetch your API credentials
try:
    API_KEY = st.secrets["RWGPS_API_KEY"]
    AUTH_TOKEN = st.secrets["RWGPS_AUTH_TOKEN"]
except KeyError:
    st.error("🔒 API keys not found! Please make sure they are in your Streamlit Secrets.")
    st.stop() 

# 3. Function to fetch data from the internet
@st.cache_data(ttl=3600) # Memorize this for 1 hour so the app loads instantly
def fetch_rides(api_key, auth_token):
    url = "https://ridewithgps.com/api/v1/trips.json"
    response = requests.get(url, auth=(api_key, auth_token))
    
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch data. Error code: {response.status_code}")
        return None

# 4. Ask Ride with GPS for the data
raw_data = fetch_rides(API_KEY, AUTH_TOKEN)

# 5. Process the data and build the dashboard
if raw_data is not None:
    
    # --- SMART SORTING ---
    # APIs can be tricky, so we check exactly how they sent the list of rides
    rides_list = []
    if isinstance(raw_data, list):
        rides_list = raw_data
    elif isinstance(raw_data, dict):
        if 'results' in raw_data:
            rides_list = raw_data['results']
        elif 'trips' in raw_data:
            rides_list = raw_data['trips']
        else:
            # If we don't recognize the format, show the raw data instead of a blank screen!
            st.warning("Data received, but the format is unexpected. Here is the raw data:")
            st.json(raw_data)
            st.stop()

    # --- DASHBOARD CREATION ---
    if len(rides_list) > 0:
        # Convert the raw list into a Pandas spreadsheet format
        df = pd.DataFrame(rides_list)
        
        # Ride with GPS sends distance in meters, so we divide by 1000 for km
        if 'distance' in df.columns:
            df['Distance_km'] = df['distance'] / 1000.0
        else:
            df['Distance_km'] = 0 # Fallback if distance is missing
            
        # Figure out which column has the date (usually departed_at or created_at)
        date_col = 'departed_at' if 'departed_at' in df.columns else 'created_at'
        df['Date'] = pd.to_datetime(df[date_col])
        
        # Group by Month and Year
        df['Month'] = df['Date'].dt.to_period('M').astype(str)
        monthly_stats = df.groupby('Month')['Distance_km'].sum().reset_index()
        
        # Visuals
        st.divider()
        col1, col2 = st.columns(2)
        
        total_dist = df['Distance_km'].sum()
        col1.metric("Total All-Time Distance", f"{total_dist:,.1f} km")
        col2.metric("Total Rides Logged", len(df))
        
        st.subheader("📊 Distance by Month")
        st.bar_chart(data=monthly_stats, x='Month', y='Distance_km')
        
        with st.expander("Click here to view the raw data table"):
            st.dataframe(df)
            
    else:
        st.info("No rides found in your account yet! Go for a ride!")