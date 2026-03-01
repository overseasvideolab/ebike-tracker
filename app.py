import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import datetime
import calendar

st.set_page_config(layout="wide", page_title="Ebike Analytics Engine")

# --- APP HEADER ---
st.title("🚴‍♂️ Ebike Analytics Engine")

today = datetime.date.today()
current_year = str(today.year)
current_month_num = today.month
current_month_name = today.strftime('%B')
current_day = today.day

st.subheader(f"Current: {current_month_name} {current_year}")

# --- 1. FETCH CREDENTIALS ---
try:
    API_KEY = st.secrets["RWGPS_API_KEY"]
    AUTH_TOKEN = st.secrets["RWGPS_AUTH_TOKEN"]
except KeyError:
    st.error("🔒 API keys missing! Please add them to Streamlit Secrets.")
    st.stop() 

# --- 2. FETCH RIDE DATA (With Memory Filter to prevent crashes!) ---
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
            
        for r in results:
            ride_id = r.get('id')
            seen_ride_ids.add(ride_id)
            
            # Memory filter: Keep only the tiny text data
            lightweight_ride = {
                'id': ride_id,
                'departed_at': r.get('departed_at', r.get('created_at')),
                'distance': r.get('distance', 0)
            }
            all_rides_filtered.append(lightweight_ride)
            
        if len(results) < limit:
            break
        offset += limit 
            
    return all_rides_filtered

# --- 3. FETCH WEATHER DATA (Free Open-Meteo API for Toronto) ---
@st.cache_data(ttl=3600)
def fetch_weather():
    # Coordinates for Toronto, ON
    url = "https://api.open-meteo.com/v1/forecast?latitude=43.7001&longitude=-79.4163&daily=weathercode,temperature_2m_max&timezone=America%2FNew_York"
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.json()['daily']
    return None

def get_weather_condition(code):
    # Mapping standard WMO weather codes to simple terms
    if code <= 3: return "Sunny / Clear"
    if code in [45, 48]: return "Foggy"
    if code in [51, 53, 55, 61, 63, 65, 80, 81, 82]: return "Rain"
    if code in [71, 73, 75, 77, 85, 86]: return "Snow"
    if code in [95, 96, 99]: return "Storm"
    return "Cloudy"

with st.spinner("Crunching your data..."):
    raw_data = fetch_lightweight_rides(API_KEY, AUTH_TOKEN)
    weather_data = fetch_weather()

# --- 4. PROCESS RIDE DATA ---
if raw_data and len(raw_data) > 0:
    df = pd.DataFrame(raw_data)
    
    # Clean data
    df['Distance_km'] = df['distance'] / 1000.0
    df['Date'] = pd.to_datetime(df['departed_at'])
    df['Just_Date'] = df['Date'].dt.date 
    df['Year'] = df['Date'].dt.year.astype(str)
    df['Month_Num'] = df['Date'].dt.month
    df['Day_Num'] = df['Date'].dt.day
    df['Month_Year'] = df['Date'].dt.to_period('M').astype(str)
    
    # Time logic for your custom fractions
    days_in_current_month = calendar.monthrange(today.year, today.month)[1]
    days_passed_this_year = today.timetuple().tm_yday
    
    this_month_data = df[(df['Year'] == current_year) & (df['Month_Num'] == current_month_num)]
    this_year_data = df[df['Year'] == current_year]

    # --- TOP KPI METRICS ROW ---
    st.divider()
    col1, col2, col3, col4 = st.columns(4)
    
    month_dist = this_month_data['Distance_km'].sum()
    month_days = this_month_data['Just_Date'].nunique()
    year_dist = this_year_data['Distance_km'].sum()
    year_days = this_year_data['Just_Date'].nunique()
    
    col1.metric(f"Distance in {current_month_name}", f"{month_dist:,.0f} km")
    col2.metric(f"Days Ridden in {current_month_name}", f"{month_days} / {days_in_current_month} Days")
    col3.metric(f"Distance in {current_year}", f"{year_dist:,.0f} km")
    col4.metric(f"Days Ridden in {current_year}", f"{year_days} / {days_passed_this_year} Days")

    st.divider()

    # --- WEATHER FORECAST ROW ---
    st.subheader("⛅ Weather for next 7 days")
    if weather_data:
        weather_cols = st.columns(7)
        for i in range(7):
            # Parse weather data for each day
            date_str = weather_data['time'][i]
            day_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            day_name = day_obj.strftime("%a") # Mon, Tue, etc.
            
            temp = weather_data['temperature_2m_max'][i]
            code = weather_data['weathercode'][i]
            condition = get_weather_condition(code)
            
            # Custom logic: If it's raining/snowing or below 2°C, say NO
            good_to_ride = "✅ Yes"
            if "Rain" in condition or "Snow" in condition or "Storm" in condition or temp < 2.0:
                good_to_ride = "❌ NO"
                
            with weather_cols[i]:
                st.markdown(f"**{day_name}**")
                st.markdown(f"**{temp}°C**")
                st.write(f"*{condition}*")
                st.write("**Good to ride?**")
                st.write(good_to_ride)
    else:
        st.write("Weather data temporarily unavailable.")

    st.divider()

    # --- YEAR OVER YEAR (By this date) ---
    st.subheader(f"📅 Year by Year by this date ({current_month_name} 1st to {current_day}th)")
    
    # Filter data to ONLY include the current month, and ONLY up to today's date
    yoy_data = df[(df['Month_Num'] == current_month_num) & (df['Day_Num'] <= current_day)]
    
    if not yoy_data.empty:
        yoy_stats = yoy_data.groupby('Year')['Distance_km'].sum().reset_index()
        
        col_chart, col_table = st.columns([2, 1])
        
        with col_chart:
            fig_yoy = px.bar(yoy_stats, x='Year', y='Distance_km', 
                             text_auto='.0f', color_discrete_sequence=['#1f77b4'])
            fig_yoy.update_xaxes(type='category', title_text='')
            fig_yoy.update_yaxes(title_text='Distance (km)')
            st.plotly_chart(fig_yoy, use_container_width=True)
            
        with col_table:
            # Format table to match sketch
            yoy_stats['Distance_km'] = yoy_stats['Distance_km'].apply(lambda x: f"{x:,.0f} km")
            yoy_stats = yoy_stats.rename(columns={'Year': f'{current_month_name}', 'Distance_km': 'Distance'})
            st.dataframe(yoy_stats, hide_index=True, use_container_width=True)
    else:
        st.write(f"No historical data found for {current_month_name} yet.")

    st.divider()

    # --- ALL-TIME MACRO TREND ---
    st.subheader("📈 All-Time Monthly Trend")
    all_time_stats = df.groupby('Month_Year')['Distance_km'].sum().reset_index()
    
    fig_all = px.bar(all_time_stats, x='Month_Year', y='Distance_km', 
                     text_auto='.0f', color_discrete_sequence=['#1f77b4']) 
    fig_all.update_xaxes(type='category', tickangle=-45, title_text='')
    fig_all.update_yaxes(title_text='Distance (km)')
    st.plotly_chart(fig_all, use_container_width=True)

else:
    st.info("No ride data could be found.")