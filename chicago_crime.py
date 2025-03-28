# Save this script as e.g., chicago_crime_app.py
# Run using: streamlit run chicago_crime_app.py

import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import pydeck as pdk
from datetime import datetime, timedelta
import numpy as np # Keep NumPy for potential checks if needed later

# --- Configuration ---
st.set_page_config(layout="wide", page_title="Chicago Crime Data Explorer")

DATA_URL_TEMPLATE = "https://data.cityofchicago.org/resource/t7ek-mgzi.json"
START_DATE_QUERY = "2023-01-01T00:00:00.000"
QUERY_PARAMS = f"?$limit=100000&$where=date > '{START_DATE_QUERY}'"
FULL_DATA_URL = DATA_URL_TEMPLATE + QUERY_PARAMS
MAP_POINTS_LIMIT = 1000

# --- Data Loading ---
@st.cache_data(ttl=3600)
def load_data(url):
    """Fetches data from the Socrata API and returns a Pandas DataFrame."""
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data)

        # --- Basic Data Cleaning ---
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
        df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
        df['arrest'] = df['arrest'].astype(bool)
        df['domestic'] = df['domestic'].astype(bool)
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['day_of_week'] = df['date'].dt.day_name()
        df['hour'] = df['date'].dt.hour
        # Format date string for tooltip
        df['date_str'] = df['date'].apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S') if pd.notnull(x) else 'N/A')

        # Ensure essential text columns for tooltip exist and fill NA
        tooltip_text_cols = ['block', 'primary_type', 'description', 'location_description']
        for col in tooltip_text_cols:
             if col not in df.columns:
                 df[col] = 'N/A'
             df[col] = df[col].fillna('N/A')

        # Drop rows with invalid essential data (including NaNs from coordinate conversion)
        df.dropna(subset=['date', 'latitude', 'longitude', 'primary_type', 'community_area'], inplace=True)
        df['community_area'] = df['community_area'].astype(str)

        return df
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"An error occurred during data processing: {e}")
        st.exception(e)
        return pd.DataFrame()

# --- Main App Logic ---
st.title("Chicago Crime Data Explorer 🏙️")
st.markdown("""
Explore recent crime data reported in Chicago. Data is sourced from the
[City of Chicago Data Portal](https://data.cityofchicago.org/Public-Safety/Crimes-2001-to-Present/ijzp-q8t2).
*Note: 2025 data might be limited or unavailable.*
""")

with st.spinner("Fetching latest crime data... Please wait."):
    df_full = load_data(FULL_DATA_URL)

if df_full.empty:
    st.warning("Could not load data. Please check the data source or try again later.")
    st.stop()

# --- Sidebar Filters ---
st.sidebar.header("📊 Filters")
min_date = df_full['date'].min().date()
max_date = df_full['date'].max().date()
default_start_date = max(min_date, max_date - timedelta(days=90))
date_range = st.sidebar.date_input(
    "📅 Select Date Range", value=(default_start_date, max_date),
    min_value=min_date, max_value=max_date,
)
start_date = datetime.min.date(); end_date = datetime.max.date()
if len(date_range) == 2: start_date, end_date = date_range
else: st.sidebar.warning("Please select a start and end date."); start_date, end_date = default_start_date, max_date

all_crime_types = sorted(df_full['primary_type'].unique())
selected_crime_types = st.sidebar.multiselect(
    "🔪 Select Crime Type(s)", options=all_crime_types, default=all_crime_types[:5]
)
st.sidebar.markdown("--- \n *Note: Zip Code data not directly available. Using Community Area instead.*")
all_areas = sorted(df_full['community_area'].unique(), key=lambda x: float(x) if x.replace('.','',1).isdigit() else float('inf'))
selected_areas = st.sidebar.multiselect(
    "📍 Select Community Area(s)", options=all_areas, default=[]
)
arrest_filter = st.sidebar.radio(
    "⚖️ Arrest Status", options=['All', 'Arrest Made', 'No Arrest'], index=0
)

# --- Filter Data ---
start_datetime = pd.to_datetime(start_date); end_datetime = pd.to_datetime(end_date) + timedelta(days=1)
df_filtered = df_full.copy()
df_filtered = df_filtered[(df_filtered['date'] >= start_datetime) & (df_filtered['date'] < end_datetime)]
if selected_crime_types: df_filtered = df_filtered[df_filtered['primary_type'].isin(selected_crime_types)]
if selected_areas: df_filtered = df_filtered[df_filtered['community_area'].isin(selected_areas)]
if arrest_filter == 'Arrest Made': df_filtered = df_filtered[df_filtered['arrest'] == True]
elif arrest_filter == 'No Arrest': df_filtered = df_filtered[df_filtered['arrest'] == False]

# --- Display Results ---
st.header(f"📊 Analysis Results ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})")
st.write(f"Found **{len(df_filtered):,}** crimes matching your criteria.")

with st.expander("View Raw Data Table (Filtered)"):
    if not df_filtered.empty: st.dataframe(df_filtered)
    else: st.write("No data matches the current filters.")

# --- Prepare Map Data (Outside Expander) ---
map_data = pd.DataFrame() # Initialize empty

if not df_filtered.empty:
    # Select all columns needed for the detailed tooltip
    cols_for_map = ['latitude', 'longitude', 'primary_type', 'description', 'block', 'date_str', 'arrest']
    available_cols = [col for col in cols_for_map if col in df_filtered.columns]
    map_data = df_filtered[available_cols].copy()

    # Drop rows with missing coordinates (essential for plotting)
    map_data.dropna(subset=['latitude', 'longitude'], inplace=True)

    # Ensure text columns for tooltip are strings and NA filled
    tooltip_text_cols_prep = ['primary_type', 'description', 'block', 'date_str']
    for col in tooltip_text_cols_prep:
        if col in map_data.columns:
            map_data[col] = map_data[col].fillna('N/A').astype(str)
        else: # Should not happen if load_data ran correctly, but safety check
            map_data[col] = 'N/A'

    # Ensure arrest column is present (should be bool from load_data)
    if 'arrest' not in map_data.columns:
        map_data['arrest'] = False # Default if somehow missing

    # Apply limit after cleaning
    if len(map_data) > MAP_POINTS_LIMIT:
        # Removed the st.info message from here, limit applied silently now
        map_data = map_data.head(MAP_POINTS_LIMIT)


# --- Map Expander (Using Prepared map_data) ---
with st.expander(f"View Crime Location Map (Limited to {MAP_POINTS_LIMIT} points)"):
    if not map_data.empty:
        try:
            valid_lat = map_data['latitude'].dropna()
            valid_lon = map_data['longitude'].dropna()
            if not valid_lat.empty and not valid_lon.empty:
                mid_lat = valid_lat.median()
                mid_lon = valid_lon.median()
            else:
                mid_lat, mid_lon = 41.88, -87.63 # Default Chicago coordinates

            # --- Detailed HTML Tooltip Config ---
            tooltip_config = {
                "html": "<b>Type:</b> {primary_type}<br/>"
                        "<b>Description:</b> {description}<br/>"
                        "<b>Location:</b> {block}<br/>"
                        "<b>Date:</b> {date_str}<br/>"
                        "<b>Arrest:</b> {arrest}",
                "style": {
                    "backgroundColor": "rgba(60, 60, 60, 0.8)",
                    "color": "white",
                    "padding": "5px",
                    "border-radius": "3px"
                }
            }

            layer = pdk.Layer(
                'ScatterplotLayer',
                data=map_data, # Use the prepared map_data
                get_position='[longitude, latitude]',
                get_color='[200, 30, 0, 160]',
                get_radius=50,
                radius_min_pixels=2,
                radius_max_pixels=50,
                pickable=True,
                auto_highlight=True
            )
            view_state = pdk.ViewState(
                latitude=mid_lat,
                longitude=mid_lon,
                zoom=11,
                pitch=45
            )
            deck = pdk.Deck(
                layers=[layer],
                initial_view_state=view_state,
                map_style='mapbox://styles/mapbox/light-v9',
                tooltip=tooltip_config # Use the detailed HTML tooltip
            )

            st.pydeck_chart(deck)
            st.caption("Hover over red points for crime details.")

        except Exception as e:
            st.error("An error occurred while rendering the map:")
            st.exception(e)
    else:
        st.warning("No map data available to display based on filters and processing.")


# --- Visualizations ---
st.header("📈 Visualizations")
if df_filtered.empty:
    st.warning("No data for the selected filters, visualizations cannot be generated.")
else:
    try:
        # (Visualization code remains the same)
        st.subheader("Crime Trends Over Time")
        crimes_over_time = df_filtered.set_index('date').resample('D').size().reset_index(name='count')
        fig_time = px.line(crimes_over_time, x='date', y='count', title="Daily Crime Count", labels={'date': 'Date', 'count': 'Number of Crimes'})
        st.plotly_chart(fig_time, use_container_width=True)

        st.subheader("Most Common Crime Types")
        crime_counts = df_filtered['primary_type'].value_counts().reset_index(); crime_counts.columns = ['primary_type', 'count']
        fig_types = px.bar(crime_counts.head(15), x='count', y='primary_type', orientation='h', title="Top 15 Crime Types (by Frequency)", labels={'primary_type': 'Crime Type', 'count': 'Number of Crimes'})
        fig_types.update_layout(yaxis={'categoryorder':'total ascending'}); st.plotly_chart(fig_types, use_container_width=True)

        st.subheader("Crimes by Hour of Day")
        crimes_by_hour = df_filtered['hour'].value_counts().sort_index().reset_index(); crimes_by_hour.columns = ['hour', 'count']
        fig_hour = px.bar(crimes_by_hour, x='hour', y='count', title="Crime Count by Hour", labels={'hour': 'Hour of Day (0-23)', 'count': 'Number of Crimes'})
        st.plotly_chart(fig_hour, use_container_width=True)

        st.subheader("Crimes by Community Area")
        if not selected_areas or len(selected_areas) > 1:
            area_counts = df_filtered['community_area'].value_counts().reset_index(); area_counts.columns = ['community_area', 'count']
            try:
                area_counts['community_area_num'] = pd.to_numeric(area_counts['community_area']); area_counts = area_counts.sort_values(by='community_area_num', ascending=True).head(25)
            except ValueError: area_counts = area_counts.sort_values(by='count', ascending=False).head(25)
            fig_area = px.bar(area_counts, x='count', y='community_area', orientation='h', title="Crimes in Top 25 Community Areas (by Frequency)", labels={'community_area': 'Community Area', 'count': 'Number of Crimes'})
            fig_area.update_layout(yaxis={'categoryorder':'total ascending'}); st.plotly_chart(fig_area, use_container_width=True)
        elif len(selected_areas) == 1: st.info(f"Displaying data for Community Area {selected_areas[0]} only.")

    except Exception as e:
        st.error(f"An error occurred while generating visualizations: {e}")
        st.exception(e)

# --- Footer ---
st.markdown("---")
st.markdown(f"*Data last fetched: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
st.markdown(f"*Data URL used: `{DATA_URL_TEMPLATE}`*")