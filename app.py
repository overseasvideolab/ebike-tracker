import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import datetime
import calendar

# Set page to wide mode and hide default padding
st.set_page_config(layout="wide", page_title="Ebike Analytics Engine")

# --- CUSTOM CSS INJECTION ---
# This block completely changes how the app looks, creating modern cards and hiding ugly borders
st.markdown("""
<style>
    /* Clean up the main background and padding */
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    
    /* Custom styling for our top KPI cards */
    .kpi-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 20px 10px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
    }
    .kpi-value { font-size: 32px; font-weight: 800; color: #1f77b4; margin-bottom: 5px; }
    .kpi-label { font-size: 16px; color: #666666; font-weight: 500;}
    
    /* Custom styling for the Weather cards */
    .weather-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px 5px;
        text-align: center;
    }
    .weather-day { font-size: 18px; font-weight: bold; color: #333; }
    .weather-temp { font-size: 24px; font-weight: bold; color: #FF4B4B; margin: 5px 0; }
    .weather-cond { font-size: 14px; color: #555; margin-bottom: 10px; height: 40px;}
    .ride-label { font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px;}
    .ride-yes { color: #28a745; font-weight: 900; font-size: 18px; }
    .ride-no { color: #dc3545; font-weight: 900; font-size: 18px; }
</style>
""", unsafe_allow_html=True)

# --- APP HEADER ---
today = datetime.date.today()
current_year = str(today.year)
current_month_num = today.month
current_month_name = today.strftime('%B')
current_day = today.day

col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.title("🚴‍♂️ Ebike Analytics Engine")
with col_head2:
    st.subheader(f"Current: {current_month_name} {current_year}")

st.write("") # Adds a little breathing room

# --- 1. FETCH CREDENTIALS ---
try:
    API_KEY = st.secrets["RWGPS_API_KEY"]
    AUTH_TOKEN = st.secrets["RWGPS_AUTH_TOKEN"]
except KeyError:
    st.error("🔒 API keys missing! Please add them to Streamlit Secrets.")
    st.stop() 

# --- 2. FETCH RIDE DATA ---
@st.cache_data(ttl=3600) 
def fetch_lightweight_rides(api_key, auth_token):
    all_rides_filtered = []
    offset = 0
    limit = 50 
    url = "https://ridewithgps.com/api/v1/trips.json"
    seen_ride_ids = set() 
    
    while True:
        response = requests.get(url, auth=(api_key, auth_token), params={"limit": limit, "offset": offset})
        if response.status_code != 200: break
        data = response.json()
        results = data if isinstance(data, list) else data.get('results', data.get('trips', []))
        if not results: break
        
        first_ride_id = results[0].get('id')
        if first_ride_id in seen_ride_ids: break 
            
        for r in results:
            ride_id = r.get('id')
            seen_ride_ids.add(ride_id)
            lightweight_ride = {
                'id': ride_id,
                'departed_at': r.get('departed_at', r.get('created_at')),
                'distance': r.get('distance', 0)
            }
            all_rides_filtered.append(lightweight_ride)
            
        if len(results) < limit: break
        offset += limit 
    return all_rides_filtered

# --- 3. FETCH WEATHER DATA ---
@st.cache_data(ttl=3600)
def fetch_weather():
    url = "https://api.open-meteo.com/v1/forecast?latitude=43.7001&longitude=-79.4163&daily=weathercode,temperature_2m_max&timezone=America%2FNew_York"
    resp = requests.get(url)
    if resp.status_code == 200: return resp.json()['daily']
    return None

def get_weather_condition(code):
    if code <= 3: return "☀️ Sunny / Clear"
    if code in [45, 48]: return "🌫️ Foggy"
    if code in [51, 53, 55, 61, 63, 65, 80, 81, 82]: return "🌧️ Rain"
    if code in [71, 73, 75, 77, 85, 86]: return "❄️ Snow"
    if code in [95, 96, 99]: return "⛈️ Storm"
    return "☁️ Cloudy"

with st.spinner("Crunching your data..."):
    raw_data = fetch_lightweight_rides(API_KEY, AUTH_TOKEN)
    weather_data = fetch_weather()

# --- 4. PROCESS RIDE DATA ---
if raw_data and len(raw_data) > 0:
    df = pd.DataFrame(raw_data)
    df['Distance_km'] = df['distance'] / 1000.0
    df['Date'] = pd.to_datetime(df['departed_at'])
    df['Just_Date'] = df['Date'].dt.date 
    df['Year'] = df['Date'].dt.year.astype(str)
    df['Month_Num'] = df['Date'].dt.month
    df['Day_Num'] = df['Date'].dt.day
    df['Month_Year'] = df['Date'].dt.to_period('M').astype(str)
    
    days_in_current_month = calendar.monthrange(today.year, today.month)[1]
    days_passed_this_year = today.timetuple().tm_yday
    
    this_month_data = df[(df['Year'] == current_year) & (df['Month_Num'] == current_month_num)]
    this_year_data = df[df['Year'] == current_year]

    # --- TOP KPI METRICS ROW (Using our Custom CSS Cards) ---
    month_dist = this_month_data['Distance_km'].sum()
    month_days = this_month_data['Just_Date'].nunique()
    year_dist = this_year_data['Distance_km'].sum()
    year_days = this_year_data['Just_Date'].nunique()
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    kpi1.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{month_dist:,.0f}km</div>
            <div class="kpi-label">in {current_month_name}</div>
        </div>
    """, unsafe_allow_html=True)
    
    kpi2.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{month_days}/{days_in_current_month} Days</div>
            <div class="kpi-label">in {current_month_name}</div>
        </div>
    """, unsafe_allow_html=True)
    
    kpi3.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{year_dist:,.0f}km</div>
            <div class="kpi-label">in {current_year}</div>
        </div>
    """, unsafe_allow_html=True)
    
    kpi4.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{year_days}/{days_passed_this_year} Days</div>
            <div class="kpi-label">in {current_year}</div>
        </div>
    """, unsafe_allow_html=True)

    st.write("---")

    # --- WEATHER FORECAST ROW ---
    st.markdown("### Weather for next 7 days")
    if weather_data:
        weather_cols = st.columns(7)
        for i in range(7):
            date_str = weather_data['time'][i]
            day_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            day_name = day_obj.strftime("%a")
            temp = weather_data['temperature_2m_max'][i]
            code = weather_data['weathercode'][i]
            condition = get_weather_condition(code)
            
            # Logic for Yes/No
            is_good = True
            if "Rain" in condition or "Snow" in condition or "Storm" in condition or temp < 2.0:
                is_good = False
                
            ride_html = '<div class="ride-yes">YES</div>' if is_good else '<div class="ride-no">NO</div>'
            
            with weather_cols[i]:
                st.markdown(f"""
                <div class="weather-card">
                    <div class="weather-day">{day_name}</div>
                    <div class="weather-temp">{temp}°C</div>
                    <div class="weather-cond">{condition}</div>
                    <div class="ride-label">Good to ride?</div>
                    {ride_html}
                </div>
                """, unsafe_allow_html=True)
    else:
        st.write("Weather data temporarily unavailable.")

    st.write("---")

    # --- YEAR OVER YEAR (By this date) ---
    st.markdown(f"### Year by Year by this date: (Mar 1 - Mar {current_day})")
    
    yoy_data = df[(df['Month_Num'] == current_month_num) & (df['Day_Num'] <= current_day)]
    
    if not yoy_data.empty:
        yoy_stats = yoy_data.groupby('Year')['Distance_km'].sum().reset_index()
        
        col_chart, col_table = st.columns([2, 1])
        
        with col_chart:
            fig_yoy = px.bar(yoy_stats, x='Year', y='Distance_km', text_auto='.0f')
            
            # Apply Modern Chart Styling
            fig_yoy.update_traces(marker_color='#1f77b4', textposition='outside')
            fig_yoy.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False, title=""),
                yaxis=dict(showgrid=True, gridcolor='#f0f0f0', title="Distance (km)"),
                margin=dict(l=0, r=0, t=20, b=0)
            )
            st.plotly_chart(fig_yoy, use_container_width=True)
            
        with col_table:
            # Clean Table View
            yoy_display = yoy_stats.copy()
            yoy_display['Distance'] = yoy_display['Distance_km'].apply(lambda x: f"{x:,.0f}km")
            yoy_display = yoy_display[['Year', 'Distance']]
            yoy_display.columns = [current_month_name, ' ']
            st.dataframe(yoy_display, hide_index=True, use_container_width=True)

    st.write("---")

    # --- ALL-TIME MACRO TREND ---
    st.markdown("### All-Time Monthly Trend (Entire History)")
    all_time_stats = df.groupby('Month_Year')['Distance_km'].sum().reset_index()
    
    fig_all = px.bar(all_time_stats, x='Month_Year', y='Distance_km', text_auto='.0f') 
    
    # Apply Modern Chart Styling
    fig_all.update_traces(marker_color='#1f77b4', textposition='outside')
    fig_all.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, type='category', tickangle=-45, title=""),
        yaxis=dict(showgrid=True, gridcolor='#f0f0f0', title="Distance (km)"),
        margin=dict(l=0, r=0, t=20, b=0)
    )
    st.plotly_chart(fig_all, use_container_width=True)

else:
    st.info("No ride data could be found.")