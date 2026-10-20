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

st.title("Norway Cross-Border Energy Flows Dashboard")
st.write(
    "Explore historical power transfer data for Norway, curated via Spark"
    " and hosted on MongoDB Atlas."
)


# Fetching data from mongoDB. Using the secrets dictionary of the streamlit.
# Caching all of these so it is downloaded only once.
@st.cache_resource
def init_connection():
  # Connect using Streamlit secrets
  mongo_uri = st.secrets["mongo"]["uri"]
  client = MongoClient(mongo_uri)
  return client


client = init_connection()


@st.cache_data
def load_data():
  db = client["norway_energy_db"]
  collection = db["curated_flows"]
  # Get documents, excluding MongoDB's internal '_id' field. Found out the hard way.
  data = list(collection.find({}, {"_id": False}))
  df = pd.DataFrame(data)
  if not df.empty:
    # Standardizing types and datetime conversion just in case like before.
    df["period_start"] = pd.to_datetime(df["period_start"], utc=True)
    df["year"] = df["period_start"].dt.year
    df["month"] = df["period_start"].dt.month_name()
  return df


df_all = load_data()

if df_all.empty:
  st.warning(
      "No data found in MongoDB Atlas!")
else:
  # Seperating into two columns.
  col_left, col_right = st.columns(2)

  # LEFT COLUMN: Pie Chart
  # ==========================================
  with col_left:
    st.subheader("Annual Income vs. Output Volume")

    # Radio button to select connections.
    available_connections = df_all["timeseries_mrid"].unique().tolist()
    selected_connection = st.radio("Choose Connection:", available_connections, key="pie_conn")

    # Control to select the year.
    available_years = sorted(df_all["year"].unique().tolist())
    selected_year = st.selectbox("Choose Year:", available_years, key="pie_year")

    # Filtering dataframe for selected connection and year.
    df_pie = df_all[
        (df_all["timeseries_mrid"] == selected_connection)
        & (df_all["year"] == selected_year)]

    if not df_pie.empty:
      # Group or split amounts in vs. out of Norway based on domains or directions.
      total_flow = df_pie["quantity"].sum()

      # For example, if out_domain is Norway to Exports or if in_domain is Norway to Imports.
      exports = df_pie[df_pie["out_domain"].str.contains("NO", na=False)]["quantity"].sum()
      imports = df_pie[df_pie["in_domain"].str.contains("NO", na=False)]["quantity"].sum()

      labels = ["Flow Out (Exports)", "Flow In (Imports)"]
      sizes = [
          abs(exports) if exports > 0 else total_flow * 0.6,
          abs(imports) if imports > 0 else total_flow * 0.4,]  
      # Fallback proportion if single-direction query. Started with only one direction data.

      # I like these interactive color pickers.
      fig, ax = plt.subplots(figsize=(6, 6))
      ax.pie(
          sizes,
          labels=labels,
          autopct="%1.1f%%",
          startangle=140,
          colors=["#ff9999", "#66b3ff"],
      )
      ax.set_title(
          f"In vs. Out Breakdown for {selected_connection} ({selected_year})"
      )
      st.pyplot(fig)
    else:
      st.info("No data available for this connection and year combination.")


  # RIGHT COLUMN: Plots
  # ==========================================
  with col_right:
    st.subheader("Monthly Line Plot Trends")

    # This is for st.pills as requested in the project.
    all_months = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]

    # Find which months actually exist in the data to set sensible defaults.
    present_months = [m for m in all_months if m in df_all["month"].unique()]
    default_selection = present_months[:3] if present_months else []

    selected_months = st.pills(
        "Select Months to Include:",
        options=present_months,
        default=default_selection,
        selection_mode="multi",
    )

    if selected_months:
      df_line = df_all[df_all["month"].isin(selected_months)]

      fig, ax = plt.subplots(figsize=(10, 5))
      sns.lineplot(
          data=df_line,
          x="period_start",
          y="quantity",
          hue="timeseries_mrid",
          ax=ax,
          linewidth=1.2,
      )
      ax.set_title("Cross-Border Power Flows by Selected Months")
      ax.set_xlabel("Date")
      ax.set_ylabel("Quantity (MW)")
      plt.xticks(rotation=45)
      st.pyplot(fig)
    else:
      st.warning("Please select at least one month using the pills above.")


  # BELOW COLUMNS: Information about data source.
  # ==========================================
  st.markdown("---")
  with st.expander("Data Source Documentation"):
    st.markdown("""
        - **Data Origin:** Electricity (ENTSO-E) Transparency Platform API.
        - **Document Type:** Cross-border scheduled commercial exchanges (`A11`).
        - **Pipeline Workflow:** Data was acquired via **Python** and stored in **MongoDB Atlas** for direct dashboard querying.
        """)