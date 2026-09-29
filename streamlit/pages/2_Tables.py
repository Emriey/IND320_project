import streamlit as st
import pandas as pd


# Title and the page layout.
st.set_page_config(page_title="Table page", layout="wide")
st.title("Reservoir Data")

# The code below checks the session_state for cached dataframe.
# This way I only process the data once, cache it in the home page and use it on the other pages.
if "processed_data" in st.session_state:
  df = st.session_state["processed_data"]
  st.write("Raw data table from the CSV file:")
  st.dataframe(df)
else:
  st.warning("CSV file could not be found, please return to home page.")


# Main Streamlit execution
st.title("Sparkline Viewer")

# Needed to separate the date information so I could use in plotting and sliders etc...
df_numeric = df.select_dtypes(include=["number"])
df_first_month = df_numeric.iloc[:30]

# Assignment specifically mentions below:
# "There should be one row in the table for each column of the imported data."
# Trasposing it provides this.
df_transposed = df_first_month.T

# 4. Storing row values as lists.
df_table = pd.DataFrame({
    "Data Series": df_transposed.index,
    "First Month Trend": df_transposed.values.tolist()
})

# Using column configuration to render this table.
# https://docs.streamlit.io/develop/api-reference/data/st.column_config/st.column_config.linechartcolumn
st.subheader("Data Series - First Month Overview")
st.dataframe(
    df_table,
    column_config={
        "Data Series": st.column_config.TextColumn("Column Name"),
        "First Month Trend": st.column_config.LineChartColumn(
            "First Month (Sparkline)",
            y_min=0,
            width="medium",
            help="Visual trend of the first month's data"
        ),
    },
    hide_index=True,
    use_container_width=True
)