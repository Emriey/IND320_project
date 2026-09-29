import pandas as pd
import streamlit as st


# Title of the page.
st.header("Data Visualization Dashboard")

# The code below checks the session_state for cached dataframe. Just like the tables page.
# This way I only process the data once, cache it in the home page and use it on the other pages.
if "processed_data" in st.session_state:
  df = st.session_state["processed_data"]
  st.success("CSV file successfully loaded.")
else:
  st.warning("Please upload and process a CSV file on Page 1 first.")

st.subheader("Plot Overview of the data")

# We double check that the dataframe is loaded.
if "df" in locals() and df is not None:
    # Creating a month column (YYYY-MM).
    df["date_Id"] = pd.to_datetime(df["date_Id"])
    df["Month"] = df["date_Id"].dt.strftime("%Y-%m")

    # Got multiple months before, we only need one of each for the slider.
    months = sorted(df["Month"].unique())

    # https://docs.streamlit.io/develop/api-reference/widgets/st.select_slider
    selected_months = st.select_slider(
        "Select a subset of months:",
        options=months,
        # Can set the default months below. I picked the first month.
        value=(months[0], months[1]),)

    # The code below just filters the data according to the selected months.
    filtered_df = df[
        (df["Month"] >= selected_months[0])
        & (df["Month"] <= selected_months[1])]

    # Setting the drop-down menu.
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    column_options = ["All Columns"] + numeric_cols
    selected_column = st.selectbox("Choose a column to plot:", options=column_options)

    # Plotting the data (using date_id for a proper time-series x-axis & the data filtered according to month slider).
    st.subheader(f"Plot for: {selected_column}")

    if selected_column == "All Columns":
        st.line_chart(filtered_df.set_index("date_Id")[numeric_cols])
    else:
        st.line_chart(filtered_df.set_index("date_Id")[selected_column])
else:
    st.warning("CSV file could not be found, please return to home page.")