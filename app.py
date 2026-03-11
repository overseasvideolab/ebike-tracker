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
    
    h3 { font-size: 1.1rem !important; font-weight: 800 !important; margin-bottom: 1rem !important; margin-top: 1.5rem !important; text-transform: uppercase; color: #333; border-bottom: 2px solid #eee; padding-bottom: 5px;}
    
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
                    all_rides.append({
                        'd': x.get('departed_at', x.get('created_at')), 
                        'dist': x.get('distance', 0),
                        'elev': x.get('elevation_gain', 0),
                        'time': x.get('moving_time', 0)
                    })
            
            offset += len(res)
            page += 1
            
        except Exception as e:
            error_message = f"Data parsing error: {e}"
            break
            
    return all_rides, error_message

with st.spinner("Crunching historical & topographical data..."):
    raw_data, error_msg = fetch_all_data(API_KEY, AUTH_TOKEN)

if error_msg:
    st.error(f"🛑 Failed to connect to Ride with GPS: {error_msg}")

if raw_data:
    df = pd.DataFrame(raw_data)
    
    # --- TIMEZONE FIX ---
    # Convert UTC data from RideWithGPS to Toronto local time
    df['Date'] = pd.to_datetime(df['d'], errors='coerce', utc=True)
    df = df.dropna(subset=['Date']) 
    df['Date'] = df['Date'].dt.tz_convert('America/Toronto').dt.tz_localize(None)
    
    df['km'] = df['dist'] / 1000.0
    df['Year'] = df['Date'].dt.year.astype(str)
    df['Mo_Num'] = df['Date'].dt.month
    df['Day_Num'] = df['Date'].dt.day
    df['Day_Of_Week'] = df['Date'].dt.day_name()
    df['Day_Of_Year'] = df['Date'].dt.dayofyear
    df['Hour'] = df['Date'].dt.hour
    
    def get_time_of_day(h):
        if 5 <= h < 12: return 'Morning (5am-12pm)'
        elif 12 <= h < 17: return 'Afternoon (12pm-5pm)'
        elif 17 <= h < 21: return 'Evening (5pm-9pm)'
        else: return 'Night (9pm-5am)'
    df['Time_Of_Day'] = df['Hour'].apply(get_time_of_day)
    
    m_data = df[(df['Year'] == c_year) & (df['Mo_Num'] == c_month)].copy()
    y_data = df[df['Year'] == c_year].copy()

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

    def format_horizontal_chart(fig, color_hex):
        fig.update_traces(
            marker_color=color_hex, textposition='inside', insidetextanchor='middle',
            texttemplate='<b>%{x:,.0f} km</b>', textfont=dict(size=20, color='white', family='sans-serif')
        )
        fig.update_layout(
            height=280, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', 
            xaxis=dict(showgrid=False, visible=False)
        )
        fig.update_yaxes(type='category', title="", showgrid=False, tickfont=dict(size=14, weight='bold', color='#333'))
        return fig

    # ==========================================
    # 2x2 CORE DASHBOARD GRID
    # ==========================================
    col_chart1, col_chart2 = st.columns(2)
    col_chart3, col_chart4 = st.columns(2)

    with col_chart1:
        st.write(f"### 📅 WEEKLY: {c_month_name.upper()}")
        def get_week_label(day):
            if day <= 7: return f"Week 1 (1-7)"
            elif day <= 14: return f"Week 2 (8-14)"
            elif day <= 21: return f"Week 3 (15-21)"
            elif day <= 28: return f"Week 4 (22-28)"
            else: return f"Week 5 (29-{days_in_mo})"
        
        m_data['Week'] = m_data['Day_Num'].apply(get_week_label)
        weekly_stats = m_data.groupby('Week')['km'].sum().reset_index()
        all_weeks = pd.DataFrame({'Week': [f"Week 1 (1-7)", f"Week 2 (8-14)", f"Week 3 (15-21)", f"Week 4 (22-28)", f"Week 5 (29-{days_in_mo})"]})
        weekly_stats = pd.merge(all_weeks, weekly_stats, on='Week', how='left').fillna(0)
        weekly_stats = weekly_stats.sort_values(by='Week', ascending=False)
        
        fig1 = px.bar(weekly_stats, x='km', y='Week', orientation='h')
        st.plotly_chart(format_horizontal_chart(fig1, '#2ecc71'), use_container_width=True, config={'displayModeBar': False})

    with col_chart2:
        st.write(f"### 📊 {c_month_name.upper()} COMPARISON")
        full_month_history = df[df['Mo_Num'] == c_month].groupby('Year')['km'].sum().reset_index()
        if not full_month_history.empty:
            avg_km = full_month_history['km'].mean()
            full_month_history['Label'] = c_month_name.upper() + " " + full_month_history['Year']
            avg_row = pd.DataFrame({'Label': [f"AVERAGE ({len(full_month_history)} YRS)"], 'km': [avg_km]})
            seg2_data = pd.concat([full_month_history, avg_row], ignore_index=True).iloc[::-1]
            
            fig2 = px.bar(seg2_data, x='km', y='Label', orientation='h')
            st.plotly_chart(format_horizontal_chart(fig2, '#F28C28'), use_container_width=True, config={'displayModeBar': False})

    with col_chart3:
        st.write("### 📈 6 MONTH TREND")
        df['MP'] = df['Date'].dt.to_period('M')
        six_months_ago = pd.Period(today, 'M') - 5
        trend = df[df['MP'] >= six_months_ago].groupby('MP')['km'].sum().reset_index()
        trend['Month'] = trend['MP'].dt.strftime('%b %y')
        trend = trend.sort_values(by='MP', ascending=False)
        
        fig3 = px.bar(trend, x='km', y='Month', orientation='h')
        st.plotly_chart(format_horizontal_chart(fig3, '#8e44ad'), use_container_width=True, config={'displayModeBar': False})

    with col_chart4:
        st.write(f"### ⏱️ PACING (UP TO {c_month_name.upper()} {c_day})")
        ytd_data = df[(df['Mo_Num'] < c_month) | ((df['Mo_Num'] == c_month) & (df['Day_Num'] <= c_day))]
        ytd_stats = ytd_data.groupby('Year')['km'].sum().reset_index()
        if not ytd_stats.empty:
            ytd_stats = ytd_stats.sort_values(by='Year', ascending=False)
            fig4 = px.bar(ytd_stats, x='km', y='Year', orientation='h')
            st.plotly_chart(format_horizontal_chart(fig4, '#4eb2e8'), use_container_width=True, config={'displayModeBar': False})
        else:
            st.write("No historical pacing data available.")

    # ==========================================
    # FULL-WIDTH YEAR-TO-DATE CUMULATIVE TRAJECTORY
    # ==========================================
    st.write("---")
    st.write("### 🚀 YEAR-TO-DATE TRAJECTORY (CUMULATIVE KM)")
    
    df_sorted = df.sort_values('Date')
    df_sorted['Cumulative_KM'] = df_sorted.groupby('Year')['km'].cumsum()
    
    # Custom dark color palette for high visibility
    dark_colors = ['#1B2631', '#7B241C', '#1E8449', '#884EA0', '#B9770E', '#2874A6']
    
    fig_cum = px.line(df_sorted, x='Day_Of_Year', y='Cumulative_KM', color='Year', 
                      color_discrete_sequence=dark_colors,
                      labels={'Day_Of_Year': 'Day of the Year', 'Cumulative_KM': 'Total KM Ridden'})
    
    # Making lines much thicker
    fig_cum.update_traces(line=dict(width=4))
    
    fig_cum.update_layout(height=450, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', hovermode="x unified",
                          legend=dict(title="Year", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    fig_cum.update_xaxes(showgrid=True, gridcolor='#f0f0f0')
    fig_cum.update_yaxes(showgrid=True, gridcolor='#f0f0f0')
    st.plotly_chart(fig_cum, use_container_width=True, config={'displayModeBar': False})


    # ==========================================
    # TIME OF DAY & WEATHER OVERLAY
    # ==========================================
    st.write("---")
    col_mid1, col_mid2 = st.columns([1, 2])
    
    with col_mid1:
        st.write("### ⏰ PREFERRED RIDING TIMES")
        time_stats = df['Time_Of_Day'].value_counts().reset_index()
        time_stats.columns = ['Time', 'Rides']
        
        fig_time = px.bar(time_stats, x='Rides', y='Time', orientation='h', text_auto=True)
        fig_time.update_traces(marker_color='#e74c3c', textposition='outside')
        fig_time.update_layout(height=250, margin=dict(l=0, r=20, t=10, b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis=dict(visible=False))
        fig_time.update_yaxes(title="")
        st.plotly_chart(fig_time, use_container_width=True, config={'displayModeBar': False})

    with col_mid2:
        st.write("### ⛅ TORONTO WEATHER FOR NEXT 7 DAYS")
        try:
            w_url = "https://api.open-meteo.com/v1/forecast?latitude=43.7&longitude=-79.4&daily=weathercode,temperature_2m_max,precipitation_sum&timezone=America%2FToronto"
            w_res = requests.get(w_url).json()['daily']
            
            weather_html = '<div style="display: flex; gap: 10px; overflow-x: auto; padding-bottom: 10px; height: 100%;">'
            for i in range(7):
                d_name = datetime.datetime.strptime(w_res['time'][i], "%Y-%m-%d").strftime("%a")
                tmp = w_res['temperature_2m_max'][i]
                code = w_res['weathercode'][i]
                precip = w_res['precipitation_sum'][i]
                
                reasons = []
                if tmp < 5: reasons.append("Too Cold")
                if precip > 5.0 or code in [95, 96, 99]: reasons.append("Heavy Rain")
                
                is_ok = "YES" if not reasons else "NO"
                icon = "☀️" if code < 3 else ("🌧️" if precip > 1.0 else "☁️")
                txt_color = "#2e7d32" if is_ok == "YES" else "#c62828"
                reason_text = ", ".join(reasons) if reasons else "Good conditions"
                
                weather_html += f"<div style='background: white; border: 1px solid #eee; border-radius: 10px; padding: 15px 5px; text-align: center; flex: 1; min-width: 90px; box-shadow: 0 4px 6px rgba(0,0,0,0.02);'><div style='font-weight: 700; font-size: 14px; margin-bottom: 8px; color: #555;'>{d_name}</div><div style='color: #d32f2f; font-weight: 900; font-size: 20px; margin-bottom: 5px;'>{tmp:.0f}°C</div><div style='font-size: 24px; margin-bottom: 5px;'>{icon}</div><div style='color: {txt_color}; font-weight: 900; font-size: 16px; margin-top: 5px;'>{is_ok}</div><div style='font-size: 11px; color: #777; height: 15px; margin-top: 5px;'>{reason_text}</div></div>"
            
            weather_html += '</div>'
            st.markdown(weather_html, unsafe_allow_html=True)
        except:
            st.write("Weather update pending...")

    # ==========================================
    # DISTRIBUTION GRAPH & ACTIVITY HEATMAP
    # ==========================================
    st.write("---")
    col_bot1, col_bot2 = st.columns(2)
    
    with col_bot1:
        st.write("### 🚲 TRIP DISTANCE DISTRIBUTION (NUMBER OF RIDES)")
        
        # --- SIMPLIFIED HISTOGRAM ---
        # Grouped by period, showing pure counts instead of confusing probability density
        dist_m = m_data[['km']].copy()
        dist_m['Period'] = f'{c_month_name} {c_year}'
        dist_y = y_data[['km']].copy()
        dist_y['Period'] = f'{c_year} Total'
        
        dist_df = pd.concat([dist_m, dist_y])
        if not dist_df.empty:
            fig_dist = px.histogram(dist_df, x='km', color='Period', barmode='group', 
                                    nbins=15, opacity=0.85,
                                    color_discrete_sequence=['#F28C28', '#1f77b4'])
            fig_dist.update_layout(
                height=350, plot_bgcolor='rgba(0,0,0,0)', 
                xaxis_title="Trip Distance (km)", 
                yaxis_title="Number of Rides", 
                legend_title="",
                legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99)
            )
            fig_dist.update_xaxes(showgrid=True, gridcolor='#f0f0f0')
            fig_dist.update_yaxes(showgrid=True, gridcolor='#f0f0f0')
            st.plotly_chart(fig_dist, use_container_width=True, config={'displayModeBar': False})

    with col_bot2:
        st.write("### ⛰️ EFFORT & TOPOGRAPHY")
        total_elev = df['elev'].sum()
        total_time_hrs = df['time'].sum() / 3600.0
        lifetime_km = df['km'].sum()
        longest_ride = df['km'].max()
        
        st.metric("Total Elevation Climbed", f"{total_elev:,.0f} meters", help="Total historical elevation gain")
        st.metric("Total Time in Saddle", f"{total_time_hrs:,.0f} Hours", help="Total moving time")
        st.metric("Longest Single Ride Ever", f"{longest_ride:,.1f} km")

elif not error_msg:
    st.warning("Awaiting connection to RidewithGPS... Click the 'Force Refresh' button above!")