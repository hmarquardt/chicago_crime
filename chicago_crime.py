# Save this script as e.g., chicago_crime_app.py
# Run using: streamlit run chicago_crime_app.py

from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# --- Configuration ---
st.set_page_config(layout="wide", page_title="Chicago Crime Data Explorer")

DATA_URL_TEMPLATE = "https://data.cityofchicago.org/resource/t7ek-mgzi.json"
# Fetch a larger limit initially, focused on recent years using Socrata Query Language ($where)
# Let's fetch data from Jan 1, 2023 onwards to have a good base for analysis
# Adjust the start date if needed for more/less data
START_DATE_QUERY = "2023-01-01T00:00:00.000"
QUERY_PARAMS = f"?$limit=100000&$where=date > '{START_DATE_QUERY}'"
FULL_DATA_URL = DATA_URL_TEMPLATE + QUERY_PARAMS


# --- Data Loading ---
@st.cache_data(ttl=3600)  # Cache data for 1 hour
def load_data(url):
    """Fetches data from the Socrata API and returns a Pandas DataFrame."""
    try:
        response = requests.get(url, timeout=60)  # Increased timeout
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        df = pd.DataFrame(data)

        # --- Basic Data Cleaning ---
        # Convert date column to datetime objects
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        # Convert coordinates to numeric, coercing errors
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
        # Convert boolean fields
        df["arrest"] = df["arrest"].astype(bool)
        df["domestic"] = df["domestic"].astype(bool)
        # Extract useful date parts
        df["year"] = df["date"].dt.year
        df["month"] = df["date"].dt.month
        df["day_of_week"] = df["date"].dt.day_name()
        df["hour"] = df["date"].dt.hour
        # Drop rows with invalid dates or coordinates needed for core features
        df.dropna(
            subset=["date", "latitude", "longitude", "primary_type", "community_area"],
            inplace=True,
        )
        # Ensure community_area is treated as string/object for filtering
        df["community_area"] = df["community_area"].astype(str)

        return df
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()  # Return empty DataFrame on error
    except Exception as e:
        st.error(f"An error occurred during data processing: {e}")
        return pd.DataFrame()


# --- Main App Logic ---
st.title("Chicago Crime Data Explorer 🏙️")  # Changed title to English
st.markdown("""
Explore recent crime data reported in Chicago. Data is sourced from the
[City of Chicago Data Portal](https://data.cityofchicago.org/Public-Safety/Crimes-2001-to-Present/ijzp-q8t2).
*Note: 2025 data might be limited or unavailable.*
""")

# Load data with spinner
with st.spinner("Fetching latest crime data... Please wait."):
    df_full = load_data(FULL_DATA_URL)

if df_full.empty:
    st.warning("Could not load data. Please check the data source or try again later.")
    st.stop()  # Stop execution if data loading failed

# --- Sidebar Filters ---
st.sidebar.header("📊 Filters")  # Changed header to English

# Date Range Filter
min_date = df_full["date"].min().date()
max_date = df_full["date"].max().date()
# Default: Last 90 days or full range if less than 90 days
default_start_date = max(min_date, max_date - timedelta(days=90))

date_range = st.sidebar.date_input(
    "📅 Select Date Range",  # Changed label to English
    value=(default_start_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

# Ensure date_range has two values
start_date = datetime.min.date()
end_date = datetime.max.date()
if len(date_range) == 2:
    start_date = date_range[0]
    end_date = date_range[1]
else:
    st.sidebar.warning(
        "Please select a start and end date."
    )  # Changed warning to English
    # Use default range if selection is incomplete
    start_date = default_start_date
    end_date = max_date


# Crime Type Filter
all_crime_types = sorted(df_full["primary_type"].unique())
selected_crime_types = st.sidebar.multiselect(
    "🔪 Select Crime Type(s)",  # Changed label to English
    options=all_crime_types,
    default=all_crime_types[
        :5
    ],  # Default to top 5 for brevity, or all_crime_types for all
)

# Community Area Filter (Replacing Zip Code)
st.sidebar.markdown(
    "--- \n *Note: Zip Code data not directly available. Using Community Area instead.*"
)
# Convert community area numbers to string for proper filtering if needed, handled in load_data
all_areas = sorted(
    df_full["community_area"].unique(),
    key=lambda x: float(x) if x.replace(".", "", 1).isdigit() else float("inf"),
)  # Sort numerically
selected_areas = st.sidebar.multiselect(
    "📍 Select Community Area(s)",  # Changed label to English
    options=all_areas,
    default=[],  # Default to none selected means all areas initially
)

# Arrest Filter
arrest_filter = st.sidebar.radio(
    "⚖️ Arrest Status",  # Changed label to English
    options=["All", "Arrest Made", "No Arrest"],
    index=0,  # Default to 'All'
)


# --- Filter Data ---
# Convert selected dates to datetime for comparison
start_datetime = pd.to_datetime(start_date)
# Add one day to end_date and convert to datetime to include the full end day
end_datetime = pd.to_datetime(end_date) + timedelta(days=1)

# Apply filters sequentially
df_filtered = df_full[
    (df_full["date"] >= start_datetime) & (df_full["date"] < end_datetime)
]

if selected_crime_types:
    df_filtered = df_filtered[df_filtered["primary_type"].isin(selected_crime_types)]

if selected_areas:
    df_filtered = df_filtered[df_filtered["community_area"].isin(selected_areas)]

if arrest_filter == "Arrest Made":
    df_filtered = df_filtered[df_filtered["arrest"] == True]
elif arrest_filter == "No Arrest":
    df_filtered = df_filtered[df_filtered["arrest"] == False]

# --- Display Results ---
st.header(
    f"📊 Analysis Results ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})"
)  # Changed header to English
st.write(
    f"Found **{len(df_filtered):,}** crimes matching your criteria."
)  # Changed text to English

# Expandable Dataframe
with st.expander("View Raw Data Table (Filtered)"):  # Changed label to English
    st.dataframe(df_filtered)

# Expandable Map
with st.expander(
    "View Crime Location Map (Limited to 500 points)"
):  # Changed label to English
    if not df_filtered.empty:
        map_data = df_filtered[["latitude", "longitude"]].dropna()
        if len(map_data) > 500:
            st.info(
                f"Too many points ({len(map_data)}) to display on map. Showing the first 500."
            )  # Changed info message to English
            map_data = map_data.head(500)

        if not map_data.empty:
            st.map(map_data)
        else:
            st.warning(
                "No valid geographic coordinates available for the filtered data."
            )  # Changed warning to English
    else:
        st.warning(
            "No data available to display the map."
        )  # Changed warning to English

# --- Visualizations ---
st.header("📈 Visualizations")  # Changed header to English

if df_filtered.empty:
    st.warning(
        "No data for the selected filters, visualizations cannot be generated."
    )  # Changed warning to English
else:
    # Visualization 1: Crime Trends Over Time
    st.subheader("Crime Trends Over Time")  # Changed subheader to English
    crimes_over_time = (
        df_filtered.set_index("date").resample("D").size().reset_index(name="count")
    )
    fig_time = px.line(
        crimes_over_time,
        x="date",
        y="count",
        title="Daily Crime Count",  # Changed title to English
        labels={"date": "Date", "count": "Number of Crimes"},
    )  # Changed labels to English
    st.plotly_chart(fig_time, use_container_width=True)

    # Visualization 2: Top Crime Types
    st.subheader("Most Common Crime Types")  # Changed subheader to English
    crime_counts = df_filtered["primary_type"].value_counts().reset_index()
    crime_counts.columns = ["primary_type", "count"]
    fig_types = px.bar(
        crime_counts.head(15),
        x="count",
        y="primary_type",
        orientation="h",
        title="Top 15 Crime Types (by Frequency)",  # Changed title to English
        labels={"primary_type": "Crime Type", "count": "Number of Crimes"},
    )  # Changed labels to English
    fig_types.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig_types, use_container_width=True)

    # Visualization 3: Crimes by Hour of Day
    st.subheader("Crimes by Hour of Day")  # Changed subheader to English
    crimes_by_hour = df_filtered["hour"].value_counts().sort_index().reset_index()
    crimes_by_hour.columns = ["hour", "count"]
    fig_hour = px.bar(
        crimes_by_hour,
        x="hour",
        y="count",
        title="Crime Count by Hour",  # Changed title to English
        labels={"hour": "Hour of Day (0-23)", "count": "Number of Crimes"},
    )  # Changed labels to English
    st.plotly_chart(fig_hour, use_container_width=True)

    # Visualization 4: Crimes by Community Area
    st.subheader("Crimes by Community Area")  # Changed subheader to English
    # Only show if specific areas weren't selected, or show selected ones
    if not selected_areas or len(selected_areas) > 1:
        area_counts = df_filtered["community_area"].value_counts().reset_index()
        area_counts.columns = ["community_area", "count"]
        # Sort numerically if possible
        area_counts["community_area_num"] = pd.to_numeric(
            area_counts["community_area"], errors="coerce"
        )
        area_counts = area_counts.sort_values(
            by="community_area_num", ascending=True
        ).head(25)  # Show top 25 areas

        fig_area = px.bar(
            area_counts,
            x="count",
            y="community_area",
            orientation="h",
            title="Crimes in Top 25 Community Areas (by Frequency)",  # Changed title to English
            labels={"community_area": "Community Area", "count": "Number of Crimes"},
        )  # Changed labels to English
        fig_area.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_area, use_container_width=True)
    elif len(selected_areas) == 1:
        st.info(
            f"Displaying data for Community Area {selected_areas[0]} only."
        )  # Changed info message to English


# --- Footer ---
st.markdown("---")
st.markdown(
    f"*Data last fetched: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
)  # Changed text to English
st.markdown(f"*Data URL used: `{DATA_URL_TEMPLATE}`*")  # Changed text to English
