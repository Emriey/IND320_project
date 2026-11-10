import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pickle
import openmeteo_requests
import requests_cache
from retry_requests import retry
from scipy.fft import dct, idct
from sklearn.neighbors import LocalOutlierFactor

st.header("Meteorological Outliers & Anomalies Analysis")

# Getting the reservoir data from cache. No need to download it again.
if "processed_data" in st.session_state:
    df_res = st.session_state["processed_data"]
    
    # col1, col2 = st.columns(2)
    # with col1:
        # selected_type = st.selectbox("Area Type:", options=sorted(df_res["areaType"].unique()), key="met_type")
    selected_type = "NO"
    st.write("Selected type is NO.")
    # with col2:
    selected_nr = st.selectbox("Area Number:", options=sorted(df_res[df_res["areaNr"] != 0]["areaNr"].unique()), key="met_nr")
        
    # Mapping area number to electricity zone name (for example, EL 3 to NO 3)
    zone_name = f"NO {selected_nr}"
    st.info(f"Analyzing meteorological data for zone: **{zone_name}**")

    # Load pre-generated points from pickle file. No need to generate everytime.
    @st.cache_resource
    def load_zone_points():
        try:
            with open("zone_weather_points.pkl", "rb") as f:
                return pickle.load(f)
        except FileNotFoundError:
            return None

    zone_points_dict = load_zone_points()

    if zone_points_dict and zone_name in zone_points_dict:
        lats = zone_points_dict[zone_name]["lats"]
        lons = zone_points_dict[zone_name]["lons"]

        # Cached function to download/fetch ERA5 weather data for the selected zone.
        # This is an important one to by pass API limitations.
        # It is also noticable in the app. After fetching once, it won't need to fetch again.
        @st.cache_data
        def fetch_zone_weather(z_name, z_lats, z_lons, year=2024):
            cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
            retry_session = retry(cache_session, retries=5, backoff_factor=0.5)
            openmeteo = openmeteo_requests.Client(session=retry_session)

            # Below code is from API example code from open-meteo.
            url = "https://archive-api.open-meteo.com/v1/archive"
            batch_size = 50  # Larger batch size compared to notebook for faster load times (hopefully).
            all_data = []
            
            for i in range(0, len(z_lats), batch_size):
                params = {
                    "latitude": z_lats[i:i + batch_size],
                    "longitude": z_lons[i:i + batch_size],
                    "start_date": f"{year}-01-01",
                    "end_date": f"{year}-12-31",
                    "hourly": ["temperature_2m", "precipitation"],
                    "models": "era5"}
                
                responses = openmeteo.weather_api(url, params=params)
                for j, response in enumerate(responses):
                    hourly = response.Hourly()
                    if hourly is None:
                        continue
                    hourly_data = {
                        "location_id": i + j,
                        "date": pd.date_range(
                            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                            freq=pd.Timedelta(seconds=hourly.Interval()),
                            inclusive="left"),

                        "temperature_2m": hourly.Variables(0).ValuesAsNumpy(),
                        "precipitation": hourly.Variables(1).ValuesAsNumpy(),}
                    
                    all_data.append(pd.DataFrame(data=hourly_data))
            return pd.concat(all_data, ignore_index=True)

        with st.spinner(f"Loading weather data for {zone_name} (2024)..."):
            weather_df = fetch_zone_weather(zone_name, lats, lons)

        # Creating Tabs for SPC and LOF plots.
        tab_spc, tab_lof = st.tabs(["Precipitation SPC (DCT)", "Temperature Anomalies (LOF)"])

        with tab_spc:
            st.subheader("Statistical Process Control (SPC) for Precipitation")
            
            with st.expander("SPC Parameters"):
                cutoff_freq = st.slider("DCT High-Pass Cutoff Frequency", 1, 20, 10, key="spc_cut")
                num_stds = st.slider("Robust Standard Deviations (SPC Limit)", 1.0, 5.0, 3.5, 0.5, key="spc_std")

            # Aggregating regional mean precipitation over time.
            weather_df['date'] = pd.to_datetime(weather_df['date'])
            time_series = weather_df.groupby('date')['precipitation'].mean().reset_index().sort_values('date').set_index('date')
            signal = time_series['precipitation'].values
            
            # DCT High-pass filtering.
            coeffs = dct(signal, type=2, norm='ortho')
            coeffs_filtered = coeffs.copy()
            coeffs_filtered[:cutoff_freq] = 0
            satv = idct(coeffs_filtered, type=2, norm='ortho')
            
            # Robust boundaries (from MAD).
            median_satv = np.median(satv)
            mad = np.median(np.abs(satv - median_satv))
            robust_std = 1.4826 * mad
            upper_limit = median_satv + (num_stds * robust_std)
            lower_limit = median_satv - (num_stds * robust_std)
            
            outlier_mask = (satv > upper_limit) | (satv < lower_limit)
            time_series['SATV'] = satv
            time_series['Outlier'] = outlier_mask
            time_series['Upper_SPC'] = time_series['precipitation'] + (upper_limit - satv)
            time_series['Lower_SPC'] = time_series['precipitation'] + (lower_limit - satv)
            
            # Plotting the SPC.
            fig, ax = plt.subplots(figsize=(12, 6))
            for spine in ax.spines.values():
                spine.set_edgecolor('white')
            ax.plot(time_series.index, time_series['precipitation'], color='cyan', alpha=0.6, label='Mean Precipitation')
            ax.plot(time_series.index, time_series['Upper_SPC'], color='orange', linestyle='--', label=f'+{num_stds} Robust SD')
            ax.plot(time_series.index, time_series['Lower_SPC'], color='orange', linestyle='--', label=f'-{num_stds} Robust SD')
            
            outliers = time_series[time_series['Outlier']]
            ax.scatter(outliers.index, outliers['precipitation'], color='red', zorder=5, label='Outliers')
            ax.set_title(f"Precipitation SPC Outlier Detection - {zone_name} (2024)", color='white')
            ax.set_xlabel("Date", color='white')
            ax.set_ylabel("Precipitation", color='white')
            ax.legend()

            # Make tick numbers white on both axes.
            ax.tick_params(axis='x', colors='white')
            ax.tick_params(axis='y', colors='white')

            fig.patch.set_facecolor('none')
            ax.set_facecolor('none')
            st.pyplot(fig)

            # Reset back to default style so it doesn't affect other light-themed elements if needed.
            plt.style.use('default')
            
            st.metric("Total Precipitation Outliers Flagged", int(outlier_mask.sum()))

        with tab_lof:
            st.subheader("Local Outlier Factor (LOF) for Temperature")
            
            with st.expander("LOF Parameters"):
                contamination = st.slider("Contamination Proportion", 0.001, 0.05, 0.01, 0.001, format="%.3f", key="lof_cont")

            temp_series = weather_df.groupby('date')['temperature_2m'].mean().reset_index().sort_values('date').set_index('date')
            X = temp_series['temperature_2m'].values.reshape(-1, 1)
            
            lof = LocalOutlierFactor(n_neighbors=20, contamination=contamination)
            preds = lof.fit_predict(X)
            temp_series['is_outlier'] = (preds == -1)
            
            fig, ax = plt.subplots(figsize=(12, 6))
            for spine in ax.spines.values():
                spine.set_edgecolor('white')
            ax.plot(temp_series.index, temp_series['temperature_2m'], color='tab:blue', alpha=0.7, label='Mean Temperature')
            
            temp_outliers = temp_series[temp_series['is_outlier']]
            ax.scatter(temp_outliers.index, temp_outliers['temperature_2m'], color='tab:red', zorder=5, label='LOF Anomalies')
            ax.set_title(f"Temperature LOF Anomalies - {zone_name} (2024)", color='white')
            ax.set_xlabel("Date", color='white')
            ax.set_ylabel("Temperature (°C)", color='white')
            ax.legend()

            # Make tick numbers white on both axes.
            ax.tick_params(axis='x', colors='white')
            ax.tick_params(axis='y', colors='white')

            fig.patch.set_facecolor('none')
            ax.set_facecolor('none')
            st.pyplot(fig)
            # Reset back to default style so it doesn't affect other light-themed elements if needed.
            plt.style.use('default')
            
            st.metric("Total Temperature Anomalies Flagged", int(temp_series['is_outlier'].sum()))
    else:
        st.error(f"Point coordinate pickle file not found or missing zone '{zone_name}'. Please generate and save your `zone_weather_points.pkl` file first.")
else:
    st.warning("Please load your reservoir data first from the home/setup page.")