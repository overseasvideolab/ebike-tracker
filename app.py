import streamlit as st
import pandas as pd

# 1. App Header
st.title("🚴‍♂️ My E-Bike Ride Tracker")
st.write("Upload your Ride with GPS spreadsheet to see your stats!")

# 2. File Uploader
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

# 3. Process the file only IF one is uploaded
if uploaded_file is not None:
    # Read the data
    df = pd.read_csv(uploaded_file)
    
    st.success("File uploaded successfully!")
    
    # Show a quick preview of the raw data
    with st.expander("Click here to peek at your raw data"):
        st.dataframe(df.head())

    # --- DATA PROCESSING ---
    # Ride with GPS CSVs usually have 'Date' and 'Distance' columns.
    # (Distance might be 'Distance (km)' or 'Distance (mi)', we will look for the word 'Distance')
    
    # Find the column that contains the word "Distance"
    distance_col = [col for col in df.columns if 'Distance' in col]
    
    if 'Date' in df.columns and distance_col:
        dist_name = distance_col[0] # Grab the exact name of the distance column
        
        # Convert the Date column to a proper time format
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Create a Month-Year column for grouping
        df['Month'] = df['Date'].dt.to_period('M').astype(str)
        
        # Calculate monthly totals
        monthly_stats = df.groupby('Month')[dist_name].sum().reset_index()

        # --- DASHBOARD VISUALS ---
        st.divider() # Adds a nice horizontal line
        
        # Big Numbers
        total_dist = df[dist_name].sum()
        total_rides = len(df)
        
        col1, col2 = st.columns(2)
        col1.metric(label="Total Distance", value=f"{total_dist:,.1f}")
        col2.metric(label="Total Rides", value=total_rides)
        
        # Chart
        st.subheader("📊 Distance by Month")
        st.bar_chart(data=monthly_stats, x='Month', y=dist_name)
        
    else:
        st.error("Uh oh! We couldn't find a 'Date' or 'Distance' column in this file.")

else:
    st.info("👆 Please upload your spreadsheet to get started.")