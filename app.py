import streamlit as st
import pandas as pd
import requests

st.title("🚴‍♂️ My E-Bike Ride Tracker")
st.write("Automatically pulling your latest rides from Ride with GPS!")

# 1. Securely fetch your API credentials from Streamlit Secrets
try:
    API_KEY = st.secrets["RWGPS_API_KEY"]
    AUTH_TOKEN = st.secrets["RWGPS_AUTH_TOKEN"]
except KeyError:
    st.error("🔒 API keys not found! Please add them to Streamlit Secrets.")
    st.stop() # Stops the app from running further and crashing

# 2. Function to securely fetch data
@st.cache_data(ttl=3600) # This caches the data for 1 hour so the app loads faster
def fetch_rides(api_key, auth_token):
    url = "https://ridewithgps.com/api/v1/trips.json"
    # Send a request to the API proving who we are
    response = requests.get(url, auth=(api_key, auth_token))
    
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch data. Error code: {response.status_code}")
        return None

# 3. Load the data
data = fetch_rides(API_KEY, AUTH_TOKEN)

# 4. Process and display the data
if data and 'results' in data:
    rides = data['results']
    
    if len(rides) > 0:
        # Convert raw JSON data into a Pandas data table
        df = pd.DataFrame(rides)
        
        # --- DATA CLEANUP ---
        # Convert dates and calculate kilometers
        df['Date'] = pd.to_datetime(df['departed_at'])
        df['Distance_km'] = df['distance'] / 1000.0
        
        # Group by month
        df['Month-Year'] = df['Date'].dt.to_period('M').astype(str)
        monthly_stats = df.groupby('Month-Year')['Distance_km'].sum().reset_index()
        
        # --- DASHBOARD VISUALS ---
        # 1. Big number metrics
        total_km = df['Distance_km'].sum()
        total_rides = len(df)
        
        col1, col2 = st.columns(2)
        col1.metric("Total All-Time Distance", f"{total_km:.2f} km")
        col2.metric("Total Rides", f"{total_rides}")
        
        # 2. The interactive chart
        st.subheader("📊 Total Distance by Month (km)")
        st.bar_chart(data=monthly_stats, x='Month-Year', y='Distance_km')
        
    else:
        st.info("No rides found in your account yet.")