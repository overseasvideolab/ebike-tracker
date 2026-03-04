import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import datetime
import calendar

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="Ebike Analytics Engine")

# 2. Advanced Styling (CSS) - Making it feel like a Mobile App
st.markdown("""
<style>
    .block-container { padding-top: 1rem; max-width: 1000px; }
    [data-testid="stMetric"] { background-color: #f8f9fa; border-radius: 10px; padding: 15px; border: 1px solid #eee; }
    .kpi-container { display: flex; justify-content: space-between; gap: 10px; margin-bottom: 20px; }
    .kpi-box { background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 15px; flex: 1; text-align: center; }
    .kpi-val { font-size: 24px; font-weight: bold; color: #1f77b4; }
    .kpi-lab { font-size: 12px; color: #666; text-transform: uppercase; }
    .weather-card { background: white; border: 1px solid #eee; border-radius: 8px; padding: 10px; text-align: center; font-size: 13px; }
    .weather-day { font-weight: bold; border-bottom: 1px solid #eee; margin-bottom: 5px; }
    .weather-temp { color: #d32f2f; font-weight: bold; font-size: 18px; }
    .ride-yes { color: #2e7d32; font-weight: bold; }
    .ride-no { color: #c62828; font-weight: bold; }
    table { font-size: 14px !important; }
</style>
""", unsafe_allow_html=True)

# 3. Header [cite: 1, 2]
today = datetime.date.today()
c_year, c_month, c_day = str(today.year), today.month, today.day
c_month_name = today.strftime('%B')

col_h1, col_h2 = st.columns([2, 1])
with col_h1: st.title("🚴‍♂️ Ebike Analytics Engine") [cite: 1]
with col_h2: st.write(f"### Current: {c_month_name} {c_year}") [cite: 2]

# 4. Data Fetching (Memory Protected)
try:
    API_KEY, AUTH_TOKEN = st.secrets["RWGPS_API_KEY"], st.secrets["RWGPS_AUTH_TOKEN"]
except:
    st.error("API Keys missing.")
    st.stop()

@st.cache_data(ttl=3600)
def get_data(api, auth):
    all_r = []
    url = "https://ridewithgps.com/api/v1/trips.json"
    for offset in range(0, 500, 50): # Fetches last 500 rides
        r = requests.get(url, auth=(api, auth), params={"limit": 50, "offset": offset}).json()
        res = r if isinstance(r, list) else r.get('results', [])
        if not res: break
        for x in res:
            all_r.append({'d': x.get('departed_at'), 'dist': x.get('distance', 0)})
    return all_r

data = get_data(API_KEY, AUTH_TOKEN)

# 5. Dashboard Logic [cite: 3, 4, 5, 6, 7]
if data:
    df = pd.DataFrame(data)
    df['Date'] = pd.to_datetime(df['d'])
    df['km'] = df['dist'] / 1000.0
    df['Year'] = df['Date'].dt.year.astype(str)
    df['Mo_Num'] = df['Date'].dt.month
    
    m_data = df[(df['Year'] == c_year) & (df['Mo_Num'] == c_month)]
    y_data = df[df['Year'] == c_year]
    
    # KPI Metrics [cite: 3, 4, 5, 6, 7]
    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-box"><div class="kpi-val">{m_data['km'].sum():.0f}km</div><div class="kpi-lab">in {c_month_name}</div></div>
        <div class="kpi-box"><div class="kpi-val">{m_data['Date'].dt.date.nunique()}/{calendar.monthrange(today.year, c_month)[1]}</div><div class="kpi-lab">Days in {c_month_name}</div></div>
        <div class="kpi-box"><div class="kpi-val">{y_data['km'].sum():.0f}km</div><div class="kpi-lab">in {c_year}</div></div>
        <div class="kpi-box"><div class="kpi-val">{y_data['Date'].dt.date.nunique()}/{today.timetuple().tm_yday}</div><div class="kpi-lab">Days in {c_year}</div></div>
    </div>
    """, unsafe_allow_html=True)

    # 6. Weather [cite: 22, 23, 24, 25, 26, 27, 28, 29, 30]
    st.markdown("### Weather for next 7 days") [cite: 22]
    w_url = "https://api.open-meteo.com/v1/forecast?latitude=43.7&longitude=-79.4&daily=weathercode,temperature_2m_max&timezone=auto"
    w_raw = requests.get(w_url).json()['daily']
    w_cols = st.columns(7)
    for i in range(7):
        day_n = datetime.datetime.strptime(w_raw['time'][i], "%Y-%m-%d").strftime("%a")
        tmp = w_raw['temperature_2m_max'][i]
        code = w_raw['weathercode'][i]
        is_ok = "YES" if tmp > 5 and code < 50 else "NO"
        color = "ride-yes" if is_ok == "YES" else "ride-no"
        with w_cols[i]:
            st.markdown(f"""<div class="weather-card"><div class="weather-day">{day_n}</div><div class="weather-temp">{tmp}°C</div>{is_ok == "YES" and "☀️" or "☁️"}<br><span class="ride-label">Ride?</span><br><span class="{color}">{is_ok}</span></div>""", unsafe_allow_html=True)

    # 7. Year over Year [cite: 31, 35]
    st.write("---")
    st.markdown(f"### Year by Year: {c_month_name}") [cite: 31]
    yoy = df[df['Mo_Num'] == c_month].groupby('Year')['km'].sum().reset_index()
    c1, c2 = st.columns([2, 1])
    with c1:
        fig = px.bar(yoy, x='Year', y='km', text_auto='.0f')
        fig.update_xaxes(type='category') # Fixes the 2025.5 decimal issue
        fig.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0), plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        yoy_t = yoy.copy()
        yoy_t['km'] = yoy_t['km'].map('{:,.0f}km'.format)
        st.table(yoy_t.set_index('Year')) [cite: 35]

    # 8. Trend [cite: 19, 20, 21]
    st.markdown("### Recent Monthly Trend")
    df['MP'] = df['Date'].dt.to_period('M')
    trend = df[df['MP'] >= (pd.Period(today, 'M') - 5)].groupby('MP')['km'].sum().reset_index()
    trend['Month'] = trend['MP'].dt.strftime('%b %y')
    fig2 = px.bar(trend, x='Month', y='km', text_auto='.0f')
    fig2.update_xaxes(type='category')
    fig2.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0), plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.warning("No data found.")