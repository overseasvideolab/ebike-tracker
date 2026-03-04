import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import datetime
import calendar

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="Ebike Analytics Engine")

# 2. Advanced Styling (CSS) - Making it feel like a Native Mobile App
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
    
    /* Chart and Table adjustments */
    .stTable { font-size: 14px !important; }
    h3 { font-size: 1.2rem !important; font-weight: 700 !important; margin-bottom: 1rem !important; }
</style>
""", unsafe_allow_html=True)

# 3. Time Context
today = datetime.date.today()
c_year, c_month = str(today.year), today.month
c_month_name = today.strftime('%B')

# 4. Header Section
col_h1, col_h2 = st.columns([2, 1])
with col_h1: 
    st.title("🚴‍♂️ Ebike Analytics")
with col_h2: 
    st.write(f"**Current: {c_month_name} {c_year}**")

# 5. Data Fetching
try:
    API_KEY = st.secrets["RWGPS_API_KEY"]
    AUTH_TOKEN = st.secrets["RWGPS_AUTH_TOKEN"]
except Exception:
    st.error("Credentials missing in Streamlit Secrets.")
    st.stop()

@st.cache_data(ttl=3600)
def fetch_all_data(api, auth):
    all_rides = []
    url = "https://ridewithgps.com/api/v1/trips.json"
    # Pagination: Pulling last ~500 rides to ensure 2+ years of history
    for offset in range(0, 500, 50):
        try:
            r = requests.get(url, auth=(api, auth), params={"limit": 50, "offset": offset}).json()
            res = r if isinstance(r, list) else r.get('results', [])
            if not res: break
            for x in res:
                all_rides.append({'d': x.get('departed_at'), 'dist': x.get('distance', 0)})
        except:
            break
    return all_rides

raw_data = fetch_all_data(API_KEY, AUTH_TOKEN)

if raw_data:
    df = pd.DataFrame(raw_data)
    df['Date'] = pd.to_datetime(df['d'])
    df['km'] = df['dist'] / 1000.0
    df['Year'] = df['Date'].dt.year.astype(str)
    df['Mo_Num'] = df['Date'].dt.month
    
    # Slice data for KPIs
    m_data = df[(df['Year'] == c_year) & (df['Mo_Num'] == c_month)]
    y_data = df[df['Year'] == c_year]
    
    # 6. Top Metrics (Mobile-First Cards)
    days_in_mo = calendar.monthrange(today.year, c_month)[1]
    days_in_yr = today.timetuple().tm_yday
    
    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-box"><div class="kpi-val">{m_data['km'].sum():.0f}km</div><div class="kpi-lab">in {c_month_name}</div></div>
        <div class="kpi-box"><div class="kpi-val">{m_data['Date'].dt.date.nunique()}/{days_in_mo}</div><div class="kpi-lab">Days in {c_month_name}</div></div>
        <div class="kpi-box"><div class="kpi-val">{y_data['km'].sum():.0f}km</div><div class="kpi-lab">in {c_year}</div></div>
        <div class="kpi-box"><div class="kpi-val">{y_data['Date'].dt.date.nunique()}/{days_in_yr}</div><div class="kpi-lab">Days in {c_year}</div></div>
    </div>
    """, unsafe_allow_html=True)

    # 7. Weather
    st.write("### ⛅ Weather Forecast")
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

    # 8. Year over Year (Full Month Comparison)
    st.write(f"### 📊 Year by Year: {c_month_name}")
    yoy = df[df['Mo_Num'] == c_month].groupby('Year')['km'].sum().reset_index()
    c1, c2 = st.columns([2, 1])
    with c1:
        fig = px.bar(yoy, x='Year', y='km', text_auto='.0f')
        fig.update_xaxes(type='category')
        fig.update_layout(height=280, margin=dict(l=0,r=0,t=20,b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        fig.update_traces(marker_color='#1f77b4', width=0.4)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    with c2:
        yoy_disp = yoy.rename(columns={'Year': 'Yr', 'km': 'Dist'})
        yoy_disp['Dist'] = yoy_disp['Dist'].map('{:,.0f}km'.format)
        st.table(yoy_disp.set_index('Yr'))

    # 9. Recent Trend
    st.write("### 📈 Recent Monthly Trend")
    df['MP'] = df['Date'].dt.to_period('M')
    trend = df[df['MP'] >= (pd.Period(today, 'M') - 5)].groupby('MP')['km'].sum().reset_index()
    trend['Month'] = trend['MP'].dt.strftime('%b %y')
    fig2 = px.bar(trend, x='Month', y='km', text_auto='.0f')
    fig2.update_xaxes(type='category')
    fig2.update_layout(height=280, margin=dict(l=0,r=0,t=20,b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    fig2.update_traces(marker_color='#1f77b4', width=0.5)
    st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})

else:
    st.warning("Awaiting connection to RidewithGPS...")