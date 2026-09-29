# Import streamlit
import streamlit as st
import pandas as pd

# Add a header to the app
st.header("Reservoir Data App")
st.write("Feel free to press the button and adjust the slider while the data loads!")

# Add a button with a label
if st.button("Press me!"):
    st.write("You pressed the button!")

# Add a slider with a range from 0 to 100 in increments of 2, starting at 50
slider_num = st.slider("Select a value", 0, 100, value=50, step=2)
st.write("Slider value:", slider_num)

# Caching the data here.
# I only pre-process and cache the data here.
# The other pages just pull the dataframe from a session_state.
@st.cache_data
def load_data(path):
    df = pd.read_csv(path)
    return df

# Pre-processing the data from CSV file.
# Correcting names, sorting etc...
reservoir_df = load_data('data/reservoirs.csv')

reservoir_df = reservoir_df.rename(columns={"dato_Id": "date_Id", "omrType": "areaType", "omrnr": "areaNr", "iso_aar": "iso_year",
                                            "iso_uke": "iso_week", "fyllingsgrad": "fill level", "kapasitet_TWh": "capacity_TWh",
                                            "fylling_TWh": "fill_TWh", "neste_Publiseringsdato": "next_publishdate",
                                            "fyllingsgrad_forrige_uke": "fill_level_lastweek", "endring_fyllingsgrad": "fill_level_change"})

# Converting the "date_Id" column to datetime.
reservoir_df['date_Id'] = pd.to_datetime(reservoir_df['date_Id'])

# Sorting the dataframe according to date.
reservoir_df = reservoir_df.sort_values(by='date_Id').reset_index(drop=True)

# Saving to session state.
st.session_state["processed_data"] = reservoir_df
st.success("Data is processed and saved to session state!")