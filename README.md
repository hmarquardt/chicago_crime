# Chicago Crime Data Explorer 🏙️

A Streamlit web application to explore and visualize recent crime data from the City of Chicago using its public Socrata API.

## Features

- **Data Fetching:** Retrieves recent crime data (defaulting to 2023 onwards) directly from the City of Chicago's open data portal.
- **Caching:** Uses Streamlit's data caching (`@st.cache_data`) to minimize API calls and speed up interactions after the initial load.
- **Interactive Filtering:** Sidebar controls allow users to filter the data by:
  - Date Range
  - Primary Crime Type (multi-select)
  - Community Area (multi-select, as Zip Code is not available in the dataset)
  - Arrest Status (All, Arrest Made, No Arrest)
- **Data Views:**
  - Displays the total count of crimes matching the selected filters.
  - An expandable section shows the filtered data in a raw table format (`st.dataframe`).
  - An expandable, interactive map (`st.pydeck_chart`) plots the locations of filtered crimes (limited to 1000 points for performance). Hovering over a point reveals details about the crime (Type, Description, Location, Date, Arrest Status).
- **Visualizations (Plotly Express):**
  - **Crime Trends Over Time:** Line chart showing the daily count of selected crimes.
  - **Most Common Crime Types:** Horizontal bar chart displaying the frequency of the top 15 crime types.
  - **Crimes by Hour of Day:** Bar chart showing crime distribution throughout the day.
  - **Crimes by Community Area:** Horizontal bar chart showing the top 25 community areas with the most selected crimes.

## Data Source

- **API Endpoint:** City of Chicago - Crimes - 2001 to Present
- **URL:** `https://data.cityofchicago.org/resource/t7ek-mgzi.json`
- **Portal Link:** [https://data.cityofchicago.org/Public-Safety/Crimes-2001-to-Present/ijzp-q8t2](https://data.cityofchicago.org/Public-Safety/Crimes-2001-to-Present/ijzp-q8t2)
- **Note:** Data freshness depends on the City's update frequency. The script fetches data from a specified start date (e.g., 2023-01-01) up to the present, subject to API availability.

## Requirements

- Python 3.8+
- Libraries:
  - `streamlit`
  - `pandas`
  - `requests`
  - `plotly`
  - `pydeck`
  - `numpy`

## Installation

1.  **Clone the repository or download the script:**

    ```bash
    # If using Git
    git clone <repository_url>
    cd <repository_directory>

    # Or just download chicago_crime_app.py
    ```

2.  **Create and activate a virtual environment (Recommended):**

    ```bash
    # On macOS/Linux
    python3 -m venv venv
    source venv/bin/activate

    # On Windows
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install the required libraries:**
    ```bash
    pip install streamlit pandas requests plotly pydeck numpy
    ```
    _(Alternatively, if a `requirements.txt` file is provided: `pip install -r requirements.txt`)_

## Running the Application

1.  Navigate to the directory containing the `chicago_crime_app.py` script in your terminal.
2.  Make sure your virtual environment is activated.
3.  Run the Streamlit application:
    ```bash
    streamlit run chicago_crime_app.py
    ```
4.  Streamlit will start the server and typically open the application automatically in your default web browser. The URL will usually be `http://localhost:8501`.

## Notes

- **Map Points Limit:** The interactive map displays a maximum of 1000 points (`MAP_POINTS_LIMIT`) for performance reasons. If the filtered data exceeds this limit, only the first 1000 points are shown.
- **Community Area vs. Zip Code:** The source dataset does not contain reliable Zip Code information for all entries. Community Area is used as the geographic filter instead.
- **Pydeck Map Styling:** The map uses a default Mapbox style (`light-v9`). For more advanced styles or potentially higher usage limits, you might need a Mapbox API token set as an environment variable (`MAPBOX_API_KEY`). However, the basic functionality works without it.
- **Error Handling:** Basic error handling for data fetching and processing is included, displaying messages within the Streamlit app if issues occur.
