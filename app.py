import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import datetime
import calendar

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="Ebike Analytics Engine")

# 2. Advanced Styling (CSS)
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; max-width: 900px; margin: auto; font-family: sans-serif; }
    
    .kpi-container { display: flex; gap: 15px; margin-bottom: 25px; flex-wrap: wrap; }
    .kpi-box { 
        background: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; 
        padding: 15px 10px; text-align: center; flex: 1; min-width: 150px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02);
    }
    .kpi-val { font-size: 26px; font-weight: 900; color: #1f77b4; line-height: 1.2; }
    .kpi-lab { font-size: 11px; color: #666; text-transform: uppercase; margin-top: 5px; font-weight: 700; }
    .kpi-lab span { color: #000; }
    
    h3 { font-size: 1.1rem !important; font-weight: 800 !important; margin-bottom: 0.5rem !important; margin-top: 1.5rem !important; text-transform: uppercase; color: #222;}
</style>
""", unsafe_allow_html=True)

if st.button("🔄 Force Refresh Data (Pull Full History)"):
    st.cache_data.clear()
    st.rerun()

# 3. Time Context
today = datetime.date.today()
c_year, c_month, c_day = str(today.year), today.month, today.day
c_month_name = today.strftime('%B')

# Header
col_h1, col_h2 = st.columns([3, 1])
with col_h1: 
    st.markdown(f"<h2>🚴‍♂️ Ebike Analytics Engine</h2>", unsafe_allow_html=True)
with col_h2: 
    st.markdown(f"<div style='text-align:right; color:#666; font-weight:bold; margin-top:10px;'>Current: {c_month_name} {c_year}</div>", unsafe_allow_html=True)

# 4. Data Fetching
try:
    API_KEY = st.secrets["RWGPS_API_KEY"]
    AUTH_TOKEN = st.secrets["RWGPS_AUTH_TOKEN"]
except Exception:
    st.error("🔒 Credentials missing in Streamlit Secrets.")
    st.stop()

@st.cache_data(ttl=3600)
def fetch_all_data(api, auth):
    all_rides = []
    error_message = None
    url = "https://ridewithgps.com/api/v1/trips.json"
    
    page = 1
    offset = 0
    seen_ids = set()
    
    # FIX: Bulletproof loop. Will not stop until the API hands over 0 rides.
    while True:
        try:
            params = {"page": page, "offset": offset, "limit": 100, "per_page": 100}
            response = requests.get(url, auth=(api, auth), params=params)
            
            if response.status_code != 200:
                error_message = f"API Error {response.status_code}: {response.text}"
                break
                
            r = response.json()
            res = r if isinstance(r, list) else r.get('results', r.get('trips', []))
            
            # If the page is literally empty, we've finally hit the bottom!
            if not res: 
                break
            
            # If API ignores pagination and gets stuck handing us Page 1, break the loop
            if res[0].get('id') in seen_ids: 
                break 
            
            for x in res:
                ride_id = x.get('id')
                if ride_id not in seen_ids:
                    seen_ids.add(ride_id)
                    all_rides.append({'d': x.get('departed_at', x.get('created_at')), 'dist': x.get('distance', 0)})
            
            # Move exact number of pages forward, bypassing the API's strict limits
            offset += len(res)
            page += 1
            
        except Exception as e:
            error_message = f"Data parsing error: {e}"
            break
            
    return all_rides, error_message

with st.spinner("Downloading full history... This may take a moment."):
    raw_data, error_msg = fetch_all_data(API_KEY, AUTH_TOKEN)

if error_msg:
    st.error(f"🛑 Failed to connect to Ride with GPS: {error_msg}")

if raw_data:
    df = pd.DataFrame(raw_data)
    df['Date'] = pd.to_datetime(df['d'])
    df['km'] = df['dist'] / 1000.0
    df['Year'] = df['Date'].dt.year.astype(str)
    df['Mo_Num'] = df['Date'].dt.month
    df['Day_Num'] = df['Date'].dt.day
    df['Day_Of_Week'] = df['Date'].dt.day_name()
    
    m_data = df[(df['Year'] == c_year) & (df['Mo_Num'] == c_month)]
    y_data = df[df['Year'] == c_year]
    
    # --- DIAGNOSTIC TRACKER ---
    oldest_ride = df['Date'].min().strftime('%B %Y')
    st.success(f"✅ Successfully loaded **{len(df)}** total rides. Oldest ride found: **{oldest_ride}**.")

    # ==========================================
    # SEGMENT 1: The Snapshot
    # ==========================================
    days_in_mo = calendar.monthrange(today.year, c_month)[1]
    days_in_yr = today.timetuple().tm_yday
    
    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-box"><div class="kpi-val">{m_data['km'].sum():,.0f}km</div><div class="kpi-lab">IN <span>{c_month_name.upper()} {c_year}</span></div></div>
        <div class="kpi-box"><div class="kpi-val">{m_data['Date'].dt.date.nunique()}/{days_in_mo} Days</div><div class="kpi-lab">IN <span>{c_month_name.upper()} {c_year}</span></div></div>
        <div class="kpi-box"><div class="kpi-val">{y_data['km'].sum():,.0f}km</div><div class="kpi-lab">IN {c_year} <span>TOTAL</span></div></div>
        <div class="kpi-box"><div class="kpi-val">{y_data['Date'].dt.date.nunique()}/{days_in_yr} Days</div><div class="kpi-lab">IN {c_year} <span>TOTAL</span></div></div>
    </div>
    """, unsafe_allow_html=True)

    # ==========================================
    # SEGMENT 2: Current Month Comparison
    # ==========================================
    full_month_history = df[df['Mo_Num'] == c_month].groupby('Year')['km'].sum().reset_index()
    
    if not full_month_history.empty:
        avg_km = full_month_history['km'].mean()
        full_month_history['Label'] = "TOTAL KM - " + c_month_name.upper() + " " + full_month_history['Year']
        avg_row = pd.DataFrame({'Label': [f"AVERAGE {c_month_name.upper()} KM ({len(full_month_history)} YRS)"], 'km': [avg_km]})
        
        seg2_data = pd.concat([full_month_history, avg_row], ignore_index=True)
        
        fig2 = px.bar(seg2_data, x='km', y='Label', orientation='h', text_auto='.0f')
        fig2.update_traces(marker_color='#F28C28', textposition='inside', texttemplate='<b>%{x:,.0f} km</b>', textfont=dict(size=18, color='white'))
        fig2.update_layout(height=250, margin=dict(l=0,r=40,t=10,b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis=dict(showgrid=False, visible=False))
        fig2.update_yaxes(type='category', title="", showgrid=False, tickfont=dict(size=14, weight='bold', color='#000'))
        st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})

    # ==========================================
    # SEGMENT 3: 6 Month History
    # ==========================================
    df['MP'] = df['Date'].dt.to_period('M')
    six_months_ago = pd.Period(today, 'M') - 5
    trend = df[df['MP'] >= six_months_ago].groupby('MP')['km'].sum().reset_index()
    trend['Month'] = trend['MP'].dt.strftime('%b %y')
    
    fig3 = px.bar(trend, x='Month', y='km', text_auto='.0f')
    fig3.update_traces(marker_color='#8e44ad', textposition='inside', texttemplate='<b>%{y:,.0f} km</b>', textfont=dict(size=18, color='white'))
    fig3.update_layout(height=250, margin=dict(l=0,r=0,t=20,b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis=dict(type='category', title="", tickfont=dict(size=14, color='#000')), yaxis=dict(visible=False, showgrid=False))
    st.plotly_chart(fig3, use_container_width=True, config={'displayModeBar': False})

    # ==========================================
    # SEGMENT 4: Weather for next 7 days
    # ==========================================
    st.write("### ⛅ Weather for next 7 days")
    try:
        w_res = requests.get("https://api.open-meteo.com/v1/forecast?latitude=43.7&longitude=-79.4&daily=weathercode,temperature_2m_max&timezone=auto").json()['daily']
        
        # FIX: Flattened HTML completely onto single lines to prevent markdown formatting issues
        weather_html = '<div style="display: flex; gap: 10px; overflow-x: auto; padding-bottom: 10px;">'
        for i in range(7):
            d_name = datetime.datetime.strptime(w_res['time'][i], "%Y-%m-%d").strftime("%a")
            tmp = w_res['temperature_2m_max'][i]
            code = w_res['weathercode'][i]
            
            reasons = []
            if tmp < 5: reasons.append("Too Cold")
            if code >= 50: reasons.append("Precipitation")
            
            is_ok = "YES" if not reasons else "NO"
            icon = "☀️" if code < 3 else ("☁️" if code < 50 else "🌧️")
            txt_color = "#2e7d32" if is_ok == "YES" else "#c62828"
            reason_text = ", ".join(reasons) if reasons else ""
            
            weather_html += f"<div style='background: white; border: 1px solid #eee; border-radius: 10px; padding: 12px 5px; text-align: center; flex: 1; min-width: 85px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);'><div style='font-weight: 700; font-size: 13px; margin-bottom: 8px; color: #555;'>{d_name}</div><div style='color: #d32f2f; font-weight: 900; font-size: 18px; margin-bottom: 5px;'>{tmp:.0f}°C</div><div style='font-size: 20px; margin-bottom: 5px;'>{icon}</div><div style='color: {txt_color}; font-weight: 900; font-size: 14px; margin-top: 5px;'>{is_ok}</div><div style='font-size: 10px; color: #777; height: 15px; margin-top: 2px;'>{reason_text}</div></div>"
        
        weather_html += '</div>'
        st.markdown(weather_html, unsafe_allow_html=True)
    except:
        st.write("Weather update pending...")

    # ==========================================
    # SEGMENT 5: Year by Year up to this date
    # ==========================================
    st.write(f"### YEAR BY YEAR UP TO THIS DATE ({c_month_name.upper()} {c_day})")
    
    ytd_data = df[(df['Mo_Num'] < c_month) | ((df['Mo_Num'] == c_month) & (df['Day_Num'] <= c_day))]
    ytd_stats = ytd_data.groupby('Year')['km'].sum().reset_index()
    
    if not ytd_stats.empty:
        fig5 = px.bar(ytd_stats, x='km', y='Year', orientation='h', text_auto='.0f')
        fig5.update_traces(marker_color='#4eb2e8', textposition='inside', texttemplate='<b>%{x:,.0f} km</b>', textfont=dict(size=18, color='white'))
        fig5.update_layout(height=200, margin=dict(l=0,r=20,t=10,b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis=dict(showgrid=False, visible=False))
        fig5.update_yaxes(type='category', title="", showgrid=False, autorange="reversed", tickfont=dict(size=16, color='#000'))
        st.plotly_chart(fig5, use_container_width=True, config={'displayModeBar': False})
    else:
        st.write("No rides logged before this date historically.")

    # ==========================================
    # SEGMENT 6: AI Habit Analysis
    # ==========================================
    st.write("### 🤖 Riding Habits & Analytics")
    
    col_a1, col_a2, col_a3 = st.columns(3)
    
    fav_day = df['Day_Of_Week'].value_counts().idxmax()
    longest_ride = df['km'].max()
    longest_ride_date = df.loc[df['km'].idxmax(), 'Date'].strftime('%b %d, %Y')
    lifetime_km = df['km'].sum()
    
    col_a1.metric("Favorite Day to Ride", fav_day)
    col_a2.metric("Longest Single Ride", f"{longest_ride:,.1f} km", help=f"Achieved on {longest_ride_date}")
    col_a3.metric("Lifetime Distance Logged", f"{lifetime_km:,.0f} km")

elif not error_msg:
    st.warning("Awaiting connection to RidewithGPS... Click the 'Force Refresh' button above!")