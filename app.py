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
    .block-container { padding-top: 1rem; max-width: 1000px; margin: auto; }
    .kpi-container { 
        display: grid; 
        grid-template-columns: repeat(2, 1fr); 
        gap: 10px; 
        margin-bottom: 20px; 
    }
    @media (min-width: 600px) {
        .kpi-container { grid-template-columns: repeat(4, 1fr); }
    }
    .kpi-box { 
        background: #ffffff; 
        border: 1px solid #e0e0e0; 
        border-radius: 12px; 
        padding: 20px 10px; 
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .kpi-val { font-size: 28px; font-weight: 800; color: #1f77b4; line-height: 1.2; }
    .kpi-lab { font-size: 12px; color: #888; text-transform: uppercase; margin-top: 5px; font-weight: 600; }
    
    .weather-card { 
        background: white; 
        border: 1px solid #eee; 
        border-radius: 10px; 
        padding: 10px; 
        text-align: center; 
        min-width: 80px;
    }
    .weather-day { font-weight: bold; font-size: 14px; margin-bottom: 5px; color: #444; }
    .weather-temp { color: #d32f2f; font-weight: 800; font-size: 20px; }
    .ride-yes { color: #2e7d32; font-weight: 900; }
    .ride-no { color: #c62828; font-weight: 900; }
    
    .stTable { font-size: 14px !important; }
    h3 { font-size: 1.2rem !important; font-weight: 700 !important; margin-bottom: 1rem !important; }
</style>
""", unsafe_allow_html=True)

if st.button("🔄 Force Refresh Data (Clear Cache)"):
    st.cache_data.clear()
    st.rerun()

# 3. Time Context
today = datetime.date.today()
c_year, c_month, c_day = str(today.year), today.month, today.day
c_month_name = today.strftime('%B')

# 4. Header Section
col_h1, col_h2 = st.columns([2, 1])
with col_h1: 
    st.title("🚴‍♂️ Ebike Analytics Engine")
with col_h2: 
    st.write(f"**Current: {c_month_name} {c_year}**")

# 5. Data Fetching
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
    
    for offset in range(0, 500, 50):
        try:
            response = requests.get(url, auth=(api, auth), params={"limit": 50, "offset": offset})
            if response.status_code != 200:
                error_message = f"API Error {response.status_code}: {response.text}"
                break
                
            r = response.json()
            res = r if isinstance(r, list) else r.get('results', r.get('trips', []))
            if not res: break
            
            for x in res:
                all_rides.append({'d': x.get('departed_at', x.get('created_at')), 'dist': x.get('distance', 0)})
        except Exception as e:
            error_message = f"Data parsing error: {e}"
            break
            
    return all_rides, error_message

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
    
    # Slice data for KPIs
    m_data = df[(df['Year'] == c_year) & (df['Mo_Num'] == c_month)]
    y_data = df[df['Year'] == c_year]
    
    # 6. Top Metrics (Matched exactly to sketch fractions)
    days_in_mo = calendar.monthrange(today.year, c_month)[1]
    days_in_yr = today.timetuple().tm_yday
    
    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-box"><div class="kpi-val">{m_data['km'].sum():.0f}km</div><div class="kpi-lab">in {c_month_name}</div></div>
        <div class="kpi-box"><div class="kpi-val">{m_data['Date'].dt.date.nunique()}/{days_in_mo} Days</div><div class="kpi-lab">in {c_month_name}</div></div>
        <div class="kpi-box"><div class="kpi-val">{y_data['km'].sum():.0f}km</div><div class="kpi-lab">in {c_year}</div></div>
        <div class="kpi-box"><div class="kpi-val">{y_data['Date'].dt.date.nunique()}/{days_in_yr} Days</div><div class="kpi-lab">in {c_year}</div></div>
    </div>
    """, unsafe_allow_html=True)

    # 7. Weather
    st.write("### ⛅ Weather for next 7 days")
    try:
        w_res = requests.get("https://api.open-meteo.com/v1/forecast?latitude=43.7&longitude=-79.4&daily=weathercode,temperature_2m_max&timezone=auto").json()['daily']
        w_cols = st.columns(7)
        for i in range(7):
            d_name = datetime.datetime.strptime(w_res['time'][i], "%Y-%m-%d").strftime("%a")
            tmp = w_res['temperature_2m_max'][i]
            code = w_res['weathercode'][i]
            is_ok = "YES" if tmp > 4 and code < 50 else "NO"
            icon = "☀️" if is_ok == "YES" else "☁️"
            with w_cols[i]:
                st.markdown(f"""<div class="weather-card"><div class="weather-day">{d_name}</div><div class="weather-temp">{tmp:.0f}°C</div>{icon}<br><span class="ride-yes" style="color:{'#2e7d32' if is_ok=='YES' else '#c62828'}">{is_ok}</span></div>""", unsafe_allow_html=True)
    except:
        st.write("Weather update pending...")

    st.write("---")

    # 8. EXACT PDF MATH: Year over Year by THIS DATE
    st.write(f"### 📊 Year by Year by this date:")
    
    # Filter for the current month AND only days leading up to today's current date
    yoy_data = df[(df['Mo_Num'] == c_month) & (df['Day_Num'] <= c_day)]
    
    yoy = yoy_data.groupby('Year')['km'].sum().reset_index()
    c1, c2 = st.columns([2, 1])
    with c1:
        fig = px.bar(yoy, x='Year', y='km', text_auto='.0f')
        fig.update_xaxes(type='category', title="")
        fig.update_yaxes(title="")
        fig.update_layout(height=280, margin=dict(l=0,r=0,t=20,b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        fig.update_traces(marker_color='#1f77b4', width=0.4, textposition='outside')
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    with c2:
        # Format table exactly like the PDF: Header is "March", rows are "2024", "500km"
        if not yoy.empty:
            yoy_disp = yoy.copy()
            yoy_disp['km'] = yoy_disp['km'].map('{:,.0f}km'.format)
            yoy_disp.columns = [c_month_name, ' ']
            st.table(yoy_disp.set_index(c_month_name))
        else:
            st.write(f"No rides yet between {c_month_name} 1 - {c_day}")

    st.write("---")

    # 9. EXACT PDF MATH: Recent Trend (Exactly 5 months: Nov, Dec, Jan, Feb, Mar)
    st.write("### 📈 Recent Monthly Trend")
    df['MP'] = df['Date'].dt.to_period('M')
    
    # Pull exactly the last 5 months to match the 5 bars in your sketch
    five_months_ago = pd.Period(today, 'M') - 4
    trend = df[df['MP'] >= five_months_ago].groupby('MP')['km'].sum().reset_index()
    
    # Format labels exactly like sketch: "Nov 25", "Dec 25"
    trend['Month'] = trend['MP'].dt.strftime('%b %y')
    
    fig2 = px.bar(trend, x='Month', y='km', text_auto='.0f')
    fig2.update_xaxes(type='category', title="")
    fig2.update_yaxes(title="")
    fig2.update_layout(height=280, margin=dict(l=0,r=0,t=20,b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    fig2.update_traces(marker_color='#1f77b4', width=0.5, textposition='outside')
    st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})

elif not error_msg:
    st.warning("Awaiting connection to RidewithGPS... Click the 'Force Refresh' button above!")