import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import time
from branca.element import Template, MacroElement

# Function to geocode country names
@st.cache_data
def geocode_country(country):
    try:
        geolocator = Nominatim(user_agent="my_geocoding_app", timeout=10)
        location = geolocator.geocode(country)
        if location:
            return location.latitude, location.longitude
        else:
            return None, None
    except GeocoderTimedOut:
        st.warning(f"Geocoding timed out for {country}. Retrying...")
        time.sleep(2)
        return geocode_country(country)
    except Exception as e:
        st.warning(f"Error geocoding {country}: {e}")
        return None, None

# Function to add a legend to the Folium map
def add_legend(map_object):
    legend_html = """
    {% macro html(this, kwargs) %}
    <div style="
    position: fixed; 
    bottom: 50px; left: 50px; width: 250px; height: 180px; 
    background-color: white; z-index:9999; font-size:14px;
    border:2px solid grey; padding: 10px; color: black;">
    <strong>Values Info</strong><br>
    <i style="background: pink; width: 10px; height: 10px; display: inline-block; border-radius:50%;"></i> ≤ 20 (Low)<br>
    <i style="background: blue; width: 10px; height: 10px; display: inline-block; border-radius:50%;"></i> 21–30 (Moderate)<br>
    <i style="background: orange; width: 10px; height: 10px; display: inline-block; border-radius:50%;"></i> 31–40 (High)<br>
    <i style="background: green; width: 10px; height: 10px; display: inline-block; border-radius:50%;"></i> 41–50 (Very High)<br>
    <i style="background: magenta; width: 10px; height: 10px; display: inline-block; border-radius:50%;"></i> > 50 (Critical)
    </div>
    {% endmacro %}
    """
    legend = MacroElement()
    legend._template = Template(legend_html)
    map_object.get_root().add_child(legend)



# Set the title of the app
st.title('Countries Visualization with Geocoding')

# File uploader for Excel files
uploaded_file = st.file_uploader('Upload Excel File', type=['xlsx'])

if uploaded_file is not None:
    try:
        # Read the uploaded file
        sheet_name = 'Sheet 1'  # Adjust this to match your sheet name
        data_df = pd.read_excel(
            uploaded_file,
            sheet_name=sheet_name,
            header=0,
            usecols='A:BM',
            skiprows=10,
            nrows=39,
            na_values=[':', 'b']
        )

        # Clean the DataFrame
        data_df = data_df.loc[:, ~data_df.columns.str.contains('^Unnamed')]
        data_df_new = data_df.iloc[3:, :].reset_index(drop=True)
        data_df_new.rename(columns={'TIME': 'Country'}, inplace=True)

        # Extract years from the columns and create a slider
        years = [int(col) for col in data_df_new.columns[1:] if col.isdigit()]
        selected_year = st.slider('Select a year', min_value=min(years), max_value=max(years), value=min(years))

        # Filter and prepare data for the selected year
        data_df_new['SelectedYearValue'] = data_df_new[str(selected_year)]
        data_df_filtered = data_df_new[['Country', 'SelectedYearValue']].rename(columns={'SelectedYearValue': 'AverageValue'})

        # Show the data structure for debugging
        st.write("DataFrame structure before geocoding:")
        st.write(data_df_filtered)

        # Ensure the 'Country' column exists
        if 'Country' in data_df_filtered.columns:
            if data_df_filtered['Country'].isnull().any():
                st.warning("There are missing values in the 'Country' column.")
            else:
                # Create the Folium map
                m = folium.Map(location=[20, 0], zoom_start=2)

                # Define color mapping
                def get_color(value):
                    if value <= 20:
                        return 'pink'
                    elif 20 <= value <= 30:
                        return 'blue'
                    elif 30 <= value <= 40:
                        return 'orange'
                    elif 40 <= value <= 50:
                        return 'green'
                    else:
                        return 'magenta'

                # Add CircleMarkers for each country
                for _, row in data_df_filtered.iterrows():
                    country = row['Country']
                    avg_value = row['AverageValue']
                    latitude, longitude = geocode_country(country)

                    if latitude and longitude:
                        folium.CircleMarker(
                            location=[latitude, longitude],
                            radius=10,
                            popup=f'{country}: {avg_value:.2f}',
                            color=get_color(avg_value),
                            fill=True,
                            fill_color=get_color(avg_value),
                            fill_opacity=0.7
                        ).add_to(m)
                    else:
                        st.warning(f'Could not geocode {country}. It may not be recognized.')

                    time.sleep(2)  # Add delay to avoid exceeding API limits

                # Add the legend to the map
                add_legend(m)

                # Display the map in Streamlit
                st_folium(m, width=800, height=600)
        else:
            st.warning('The dataset must contain a "Country" column.')

    except Exception as e:
        st.error(f'Error processing the file: {e}')
