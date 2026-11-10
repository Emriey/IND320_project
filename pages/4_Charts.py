from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st
from pymongo import MongoClient

# Basic page configuration.
st.set_page_config(
    page_title="Norway Energy Cross-Border Dashboard", layout="wide"
)

st.title("Norway Cross-Border Energy Transfer Dashboard")
st.write("In this page you can explore the power import and export between Norway and foreign countries.")
st.write("Use the settings on the sidebar to the left to select data from different areas and years.")

# Fetching data from mongoDB. Using the secrets setting of the streamlit.
# Caching all of these so it is downloaded only once.
@st.cache_resource  
def init_connection():
  # Using streamlit secret int the share app here.
  mongo_uri = st.secrets["mongo"]["uri"]
  client = MongoClient(mongo_uri)
  return client

client = init_connection()

@st.cache_data
def load_data():
    # Fecthing the data from mongoDB here.
    db = client["norway_energy_db"]
    collection = db["curated_flows"]
    data = list(collection.find({}, {"_id": False}))
    df = pd.DataFrame(data)
    
    if not df.empty:
        df["period_start"] = pd.to_datetime(df["period_start"], utc=True)
        df["year"] = df["period_start"].dt.year
        df["month"] = df["period_start"].dt.month_name()
        
        # This is not optimal. However, I didn't have much time so instead of having to fix the issue on the mongoDB side,
        # I decided to fix it here. I had logged all the directions separately. This is why it showed 0% and 100%
        # on the pie-chart. Below code merges the same regions with different directions together. 
        df["timeseries_mrid"] = df["timeseries_mrid"].str.replace("DE_LU_NO_2_flow", "NO_2_DE_LU_flow", regex=False)
        df["timeseries_mrid"] = df["timeseries_mrid"].str.replace("GB_NO_2_flow", "NO_2_GB_flow", regex=False)
        df["timeseries_mrid"] = df["timeseries_mrid"].str.replace("NL_NO_2_flow", "NO_2_NL_flow", regex=False)
        df["timeseries_mrid"] = df["timeseries_mrid"].str.replace("FI_NO_4_flow", "NO_4_FI_flow", regex=False)
        df["timeseries_mrid"] = df["timeseries_mrid"].str.replace("NO_3_SE_2_flow", "SE_2_NO_3_flow", regex=False)
        df["timeseries_mrid"] = df["timeseries_mrid"].str.replace("NO_4_SE_2_flow", "SE_2_NO_4_flow", regex=False)
        df["timeseries_mrid"] = df["timeseries_mrid"].str.replace("DK_1_NO_2_flow", "NO_2_DK_1_flow", regex=False)
        df["timeseries_mrid"] = df["timeseries_mrid"].str.replace("NO_4_SE_1_flow", "SE_1_NO_4_flow", regex=False)
        df["timeseries_mrid"] = df["timeseries_mrid"].str.replace("NO_1_SE_3_flow", "SE_3_NO_1_flow", regex=False)
        
    return df

df_all = load_data()

if df_all.empty:
  st.warning("No data found in MongoDB Atlas!")
else:
  # Decided to move the selection options to the sidebar.
  st.sidebar.header("Dashboard Filters")
  
  available_connections = sorted(df_all["timeseries_mrid"].unique().tolist())
  selected_connection = st.sidebar.radio("Choose Connection:", available_connections, key="global_conn")

  available_years = sorted(df_all["year"].unique().tolist())
  selected_year = st.sidebar.selectbox("Choose Year:", available_years, key="global_year")

  # Seperating into two columns.
  col_left, col_right = st.columns(2)

  # LEFT COLUMN: Pie Chart
  # ==========================================
  with col_left:
    st.subheader("Annual Import vs. Export")

    # Filtering dataframe for selected connection and year.
    df_pie = df_all[(df_all["timeseries_mrid"] == selected_connection) & (df_all["year"] == selected_year)]

    if not df_pie.empty:
      exports = df_pie[df_pie["flow_direction"].str.lower() == "export"]["quantity"].sum()
      imports = df_pie[df_pie["flow_direction"].str.lower() == "import"]["quantity"].sum()

      labels = ["Flow Out (Exports)", "Flow In (Imports)"]
      sizes = [exports, imports]  

      if sum(sizes) > 0:
        fig, ax = plt.subplots(figsize=(6, 6))

        # Set background colors to match Streamlit's dark theme
        fig.patch.set_facecolor('#0e1117')
        ax.set_facecolor('#0e1117')

        # Fix the aspect ratio and radius so the pie never resizes itself
        ax.set_aspect('equal')

        ax.pie(
            sizes,
            labels=labels,
            autopct="%1.1f%%",
            startangle=140,
            colors=["#ff9999", "#66b3ff"],
            shadow=True,
            radius=0.75,  # Locks the circle size to a fixed proportion
            textprops={'color': 'white'})
        
        ax.set_title(f"In vs. Out Breakdown for {selected_connection} ({selected_year})", color='white')
        st.pyplot(fig)
      else:
        st.warning("Quantity sums to zero for this selection.")
    else:
      st.info("No data available for this connection and year combination.")

  # RIGHT COLUMN: Plots (Now filtered by connection, year, and selected months)
  # ==========================================
  with col_right:
    st.subheader("Monthly Line Plots")
    st.write("Average power transfer plots can be seen below. This data is resampled by the mean of the function.")
    st.write("Resampling was necessary for performance purposes.")

    all_months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]

    # Filtering available months based on the selected connection and year.
    df_filtered_base = df_all[(df_all["timeseries_mrid"] == selected_connection) & (df_all["year"] == selected_year)]
    present_months = [m for m in all_months if m in df_filtered_base["month"].unique()]
    default_selection = ["August", "September", "October"]

    selected_months = st.pills(
        "Select Months to Include:",
        options=all_months,
        default=default_selection,
        selection_mode="multi",
    )

    if selected_months:
      df_line = df_filtered_base[df_filtered_base["month"].isin(selected_months)]

      if not df_line.empty:
        # Resampling here. It was taking too long to draw the plot because of so many data points.
        df_line = df_line.sort_values("period_start")
        df_line.set_index("period_start", inplace=True)
        
        # Resampling to daily averages. Could use .mean or .sum here. Either works. 
        df_plot_resampled = df_line.resample("D")["quantity"].mean().reset_index()

        fig, ax = plt.subplots(figsize=(10, 5))
        
        # Changing plots to dark theme to fit the app better.
        fig.patch.set_facecolor('#0e1117')
        ax.set_facecolor('#0e1117')
        ax.tick_params(colors='white', which='both')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.title.set_color('white')
        for spine in ax.spines.values():
            spine.set_edgecolor('white')

        # Changed to matplotlib from seaborn to reduce loading times.
        ax.plot(
            df_plot_resampled["period_start"],
            df_plot_resampled["quantity"],
            color="#66b3ff",
            linewidth=1.2
        )
        
        ax.set_title(f"Daily Average Power Transfer for {selected_connection} ({selected_year})")
        ax.set_xlabel("Date")
        ax.set_ylabel("Quantity (MW)")
        plt.xticks(rotation=45)
        st.pyplot(fig)
      else:
        st.warning("No data matches the selected months for this connection and year.")
    else:
      st.warning("Please select at least one month above.")

  # BELOW COLUMNS: Information about data source.
  # ==========================================
  st.markdown("---")
  with st.expander("Data Source Documentation"):
    st.markdown("""
        - **Data Origin:** Electricity (ENTSO-E) Transparency Platform API.
        - **Pipeline Workflow:** Data was acquired via **Python** and stored in **MongoDB Atlas** for direct dashboard querying.
        """)