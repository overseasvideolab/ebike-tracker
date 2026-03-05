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
    .block-container { padding-top: 1.5rem; max-width: 1200px; margin: auto; font-family: sans-serif; }
    
    .kpi-container { display: flex; gap: 15px; margin-bottom: 25px; flex-wrap: wrap; }
    .kpi-box { 
        background: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; 
        padding: 20px 10px; text-align: center; flex: 1; min-width: 150px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.04);
    }
    .kpi-val { font-size: 32px; font-weight: 900; color: #1f77b4; line-height: 1.2; }
    .kpi-lab { font-size: 12px; color: #666; text-transform: uppercase; margin-top: 5px; font-weight: 700; }
    .kpi-lab span { color: #000; }
    
    h3 { font-size: 1.1rem !important; font-weight: 800 !important; margin-bottom: 1rem !important; margin-top: 0.5rem !important; text-transform: uppercase; color: #333;}
    
    [data-testid="stMetric"] {
        background-color: #f8f9fa; border: 1px solid #e9ecef; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
</style>
""", unsafe_allow_html=True)

# Header Row
col_h1, col_h2, col_h3 = st.columns([2, 1, 1])
with col_h1: 
    st.markdown(f"<h2>🚴‍♂️ Ebike Analytics Engine</h2>", unsafe_allow_html=True)
with col_h2: 
    st.markdown(f"<div style='text-align:right; color:#666; font-weight:bold; margin-top:10px;'>Current: {datetime.date.today().strftime('%B %Y')}</div>", unsafe_allow_html=True)
with col_h3:
    if st.button("🔄 Force Refresh Data"):
        st.cache_data.clear()
        st.rerun()

st.write("---")

# 3. Time Context
today = datetime.date.today()
c_year, c_month, c_day = str(today.year), today.month, today.day
c_month_name = today.strftime('%B')

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
    
    while True:
        try:
            params = {"page": page, "offset": offset, "limit": 100, "per_page": 100}
            response = requests.get(url, auth=(api, auth), params=params)
            
            if response.status_code != 200:
                error_message = f"API Error {response.status_code}: {response.text}"
                break
                
            r = response.json()
            res = r if isinstance(r, list) else r.get('results', r.get('trips', []))
            
            if not res: break
            if res[0].get('id') in seen_ids: break 
            
            for x in res:
                ride_id = x.get('id')
                if ride_id not in seen_ids:
                    seen_ids.add(ride_id)
                    all_rides.append({'d': x.get('departed_at', x.get('created_at')), 'dist': x.get('distance', 0)})
            
            offset += len(res)
            page += 1
            
        except Exception as e:
            error_message = f"Data parsing error: {e}"
            break
            
    return all_rides, error_message

with st.spinner("Crunching historical data..."):
    raw_data, error_msg = fetch_all_data(API_KEY, AUTH_TOKEN)

if error_msg:
    st.error(f"🛑 Failed to connect to Ride with GPS: {error_msg}")

if raw_data:
    df = pd.DataFrame(raw_data)
    
    # Standardize Timezones
    df['Date'] = pd.to_datetime(df['d'], errors='coerce', utc=True)
    df = df.dropna(subset=['Date']) 
    df['Date'] = df['Date'].dt.tz_convert(None)
    
    df['km'] = df['dist'] / 1000.0
    df['Year'] = df['Date'].dt.year.astype(str)
    df['Mo_Num'] = df['Date'].dt.month
    df['Day_Num'] = df['Date'].dt.day
    df['Day_Of_Week'] = df['Date'].dt.day_name()
    
    m_data = df[(df['Year'] == c_year) & (df['Mo_Num'] == c_month)].copy()
    y_data = df[df['Year'] == c_year].copy()

    # ==========================================
    # GLOBAL CHART FORMATTING FUNCTION
    # Ensures all 4 charts look absolutely identical
    # ==========================================
    def format_dashboard_chart(fig, color_hex):
        fig.update_traces(
            marker_color=color_hex, 
            textposition='inside', 
            insidetextanchor='middle',
            texttemplate='<b>%{x:,.0f} km</b>', 
            textfont=dict(size=16, color='white', family='sans-serif')
        )
        fig.update_layout(
            height=260, 
            margin=dict(l=0, r=20, t=10, b=0), 
            plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)', 
            xaxis=dict(showgrid=False, visible=False)
        )
        fig.update_yaxes(type='category', title="", showgrid=False, tickfont=dict(size=14, weight='bold', color='#333'))
        return fig

    # ==========================================
    # SEGMENT 1: The Snapshot
    # ==========================================
    days_in_mo = calendar.monthrange(today.year, c_month)[1]
    days_in_yr = today.timetuple().tm_yday
    
    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-box"><div class="kpi-val">{m_data['km'].sum():,.0f} km</div><div class="kpi-lab">IN <span>{c_month_name.upper()} {c_year}</span></div></div>
        <div class="kpi-box"><div class="kpi-val">{m_data['Date'].dt.date.nunique()} / {days_in_mo} Days</div><div class="kpi-lab">IN <span>{c_month_name.upper()} {c_year}</span></div></div>
        <div class="kpi-box"><div class="kpi-val">{y_data['km'].sum():,.0f} km</div><div class="kpi-lab">IN {c_year} <span>TOTAL</span></div></div>
        <div class="kpi-box"><div class="kpi-val">{y_data['Date'].dt.date.nunique()} / {days_in_yr} Days</div><div class="kpi-lab">IN {c_year} <span>TOTAL</span></div></div>
    </div>
    """, unsafe_allow_html=True)

    # ==========================================
    # 2x2 DASHBOARD GRID (Segments 1-4)
    # ==========================================
    col_chart1, col_chart2 = st.columns(2)
    col_chart3, col_chart4 = st.columns(2)

    # 1. WEEKLY CURRENT MONTH
    with col_chart1:
        st.write(f"### 📅 WEEKLY: {c_month_name.upper()}")
        if not m_data.empty:
            # Group by ISO week and map to date ranges for labels
            m_data['Week_Start'] = m_data['Date'] - pd.to_timedelta(m_data['Date'].dt.dayofweek, unit='d')
            m_data['Week_Label'] = "Week of " + m_data['Week_Start'].dt.strftime('%b %d')
            weekly_stats = m_data.groupby('Week_Label')['km'].sum().reset_index()
            # Sort chronologically
            weekly_stats = weekly_stats.sort_values(by='Week_Label', ascending=False)
            
            fig1 = px.bar(weekly_stats, x='km', y='Week_Label', orientation='h')
            fig1 = format_dashboard_chart(fig1, '#2ecc71') # Green
            st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})
        else:
            st.write(f"No rides yet in {c_month_name}.")

    # 2. MONTHLY COMPARE
    with col_chart2:
        st.write(f"### 📊 {c_month_name.upper()} COMPARISON")
        full_month_history = df[df['Mo_Num'] == c_month].groupby('Year')['km'].sum().reset_index()
        if not full_month_history.empty:
            avg_km = full_month_history['km'].mean()
            full_month_history['Label'] = c_month_name.upper() + " " + full_month_history['Year']
            avg_row = pd.DataFrame({'Label': [f"AVERAGE ({len(full_month_history)} YRS)"], 'km': [avg_km]})
            
            seg2_data = pd.concat([full_month_history, avg_row], ignore_index=True)
            # Sort so average is at the top or bottom cleanly
            seg2_data = seg2_data.iloc[::-1] 
            
            fig2 = px.bar(seg2_data, x='km', y='Label', orientation='h')
            fig2 = format_dashboard_chart(fig2, '#F28C28') # Orange
            st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})

    # 3. 6 MONTH TREND (Now Horizontal!)
    with col_chart3:
        st.write("### 📈 6 MONTH TREND")
        df['MP'] = df['Date'].dt.to_period('M')
        six_months_ago = pd.Period(today, 'M') - 5
        trend = df[df['MP'] >= six_months_ago].groupby('MP')['km'].sum().reset_index()
        trend['Month'] = trend['MP'].dt.strftime('%b %y')
        # Sort so most recent is at the top
        trend = trend.sort_values(by='MP', ascending=False)
        
        fig3 = px.bar(trend, x='km', y='Month', orientation='h')
        fig3 = format_dashboard_chart(fig3, '#8e44ad') # Purple
        st.plotly_chart(fig3, use_container_width=True, config={'displayModeBar': False})

    # 4. YEAR BY YEAR TO DATE
    with col_chart4:
        st.write(f"### ⏱️ PACING (UP TO {c_month_name.upper()} {c_day})")
        ytd_data = df[(df['Mo_Num'] < c_month) | ((df['Mo_Num'] == c_month) & (df['Day_Num'] <= c_day))]
        ytd_stats = ytd_data.groupby('Year')['km'].sum().reset_index()
        
        if not ytd_stats.empty:
            # Sort descending to match others
            ytd_stats = ytd_stats.sort_values(by='Year', ascending=False)
            fig4 = px.bar(ytd_stats, x='km', y='Year', orientation='h')
            fig4 = format_dashboard_chart(fig4, '#4eb2e8') # Light Blue
            st.plotly_chart(fig4, use_container_width=True, config={'displayModeBar': False})
        else:
            st.write("No historical pacing data available.")

    st.write("---")

    # ==========================================
    # SMARTER WEATHER & AI HABITS
    # ==========================================
    col_w1, col_w2 = st.columns([2, 1])
    
    with col_w1:
        st.write("### ⛅ WEATHER FOR NEXT 7 DAYS")
        try:
            # UPGRADED API: Pulls exact precipitation_sum in mm
            w_url = "https://api.open-meteo.com/v1/forecast?latitude=43.7&longitude=-79.4&daily=weathercode,temperature_2m_max,precipitation_sum&timezone=auto"
            w_res = requests.get(w_url).json()['daily']
            
            weather_html = '<div style="display: flex; gap: 10px; overflow-x: auto; padding-bottom: 10px;">'
            for i in range(7):
                d_name = datetime.datetime.strptime(w_res['time'][i], "%Y-%m-%d").strftime("%a")
                tmp = w_res['temperature_2m_max'][i]
                code = w_res['weathercode'][i]
                precip = w_res['precipitation_sum'][i]
                
                # SMARTER LOGIC: Only say NO if it's freezing OR actually raining heavily (>4mm)
                reasons = []
                if tmp < 5: reasons.append("Too Cold")
                if precip > 4.0 or code in [95, 96, 99]: reasons.append("Heavy Rain/Storm")
                
                is_ok = "YES" if not reasons else "NO"
                icon = "☀️" if code < 3 else ("🌧️" if precip > 2.0 else "☁️")
                txt_color = "#2e7d32" if is_ok == "YES" else "#c62828"
                reason_text = ", ".join(reasons) if reasons else "Clear/Light conditions"
                
                weather_html += f"<div style='background: white; border: 1px solid #eee; border-radius: 10px; padding: 15px 5px; text-align: center; flex: 1; min-width: 90px; box-shadow: 0 4px 6px rgba(0,0,0,0.02);'><div style='font-weight: 700; font-size: 14px; margin-bottom: 8px; color: #555;'>{d_name}</div><div style='color: #d32f2f; font-weight: 900; font-size: 20px; margin-bottom: 5px;'>{tmp:.0f}°C</div><div style='font-size: 24px; margin-bottom: 5px;'>{icon}</div><div style='color: {txt_color}; font-weight: 900; font-size: 16px; margin-top: 5px;'>{is_ok}</div><div style='font-size: 11px; color: #777; height: 15px; margin-top: 5px;'>{reason_text}</div></div>"
            
            weather_html += '</div>'
            st.markdown(weather_html, unsafe_allow_html=True)
        except:
            st.write("Weather update pending...")

    with col_w2:
        st.write("### 🤖 RIDING HABITS")
        fav_day = df['Day_Of_Week'].value_counts().idxmax()
        longest_ride = df['km'].max()
        lifetime_km = df['km'].sum()
        
        st.metric("All-Time Favorite Riding Day", fav_day)
        st.metric("Longest Single Ride Ever", f"{longest_ride:,.1f} km")

    st.write("---")

    # ==========================================
    # DISTRIBUTION GRAPH
    # ==========================================
    st.write("### 🚲 DISTRIBUTION OF TRIPS BY DISTANCE")
    
    # Prepare combined data for overlaid histogram
    dist_m = m_data[['km']].copy()
    dist_m['Period'] = f'{c_month_name} {c_year}'
    
    dist_y = y_data[['km']].copy()
    dist_y['Period'] = f'{c_year} Total'
    
    dist_df = pd.concat([dist_m, dist_y])
    
    if not dist_df.empty:
        # Create an overlaid density-style histogram to match your image
        fig_dist = px.histogram(dist_df, x='km', color='Period', barmode='overlay', 
                                nbins=30, histnorm='probability density', opacity=0.7,
                                color_discrete_sequence=['#F28C28', '#1f77b4'])
        
        fig_dist.update_layout(
            height=350, 
            plot_bgcolor='rgba(0,0,0,0)', 
            xaxis_title="Trip Distance (km)", 
            yaxis_title="Relative Frequency",
            legend_title="",
            legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99)
        )
        fig_dist.update_xaxes(showgrid=True, gridcolor='#f0f0f0')
        fig_dist.update_yaxes(showgrid=True, gridcolor='#f0f0f0', showticklabels=False)
        st.plotly_chart(fig_dist, use_container_width=True, config={'displayModeBar': False})

elif not error_msg:
    st.warning("Awaiting connection to RidewithGPS... Click the 'Force Refresh' button above!")