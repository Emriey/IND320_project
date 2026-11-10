import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.tsa.seasonal import STL
from scipy.signal import spectrogram, detrend

st.header("Hydrological Decomposition & Spectral Analysis")

# Checking if reservoir data exists in session state.
if "processed_data" in st.session_state:
    df = st.session_state["processed_data"]
    
    col1, col2 = st.columns(2)
    with col1:
        selected_type = st.selectbox("Area Type:", options=sorted(df["areaType"].unique()), key="stl_type")
    with col2:
        selected_nr = st.selectbox("Area Number:", options=sorted(df["areaNr"].unique()), key="stl_nr")
        
    # Filtering here and making sure there are no empty subsets.
    df["areaNr_str"] = df["areaNr"].astype(str)
    df_filtered = df[(df["areaType"] == selected_type) & (df["areaNr_str"] == str(selected_nr))].sort_values("date_Id").set_index("date_Id")
    
    fill_series = df_filtered["fill level"].dropna()

    st.info("Area number '0' only has data for 'NO' type areas. Please choose another area number for other types.")

    # This turned about to be important because if there is minimal data, seasonal part becomes very messy or 
    # straight up crashes.
    if len(fill_series) > 0:
        
        tab_stl, tab_spec = st.tabs(["STL Decomposition", "Spectrogram"])

        with tab_stl:
            st.subheader("Seasonal-Trend Decomposition using LOESS")
            
            with st.expander("STL Parameters"):
                seasonal_window = st.slider("Seasonal Smoother", min_value=3, max_value=51, value=13, step=2)
                robust_flag = st.checkbox("Robust Fit", value=True)

            if len(fill_series) > 52:
                stl = STL(fill_series, period=52, seasonal=seasonal_window, robust=robust_flag)
                res = stl.fit()
                
                fig, ax = plt.subplots(figsize=(10, 8))
                plt.style.use('dark_background')
                fig = res.plot()

                # Loop through every subplot axis to make spines, ticks, and labels white.
                for a in fig.axes:
                    for spine in a.spines.values():
                        spine.set_edgecolor('white')
    
                    # Making everything white because dark background.
                    a.tick_params(colors='white')
                    a.xaxis.label.set_color('white')
                    a.yaxis.label.set_color('white')
                    a.title.set_color('white')

                fig.patch.set_facecolor('none')
                ax.set_facecolor('none')
                st.pyplot(fig)

                # Resetting back to default style so it doesn't affect other light-themed elements if needed.
                plt.style.use('default')
            else:
                st.warning("Not enough data points for STL decomposition (requires more than 52 weeks).")

        with tab_spec:
            st.subheader("Spectrogram Analysis")
            
            with st.expander("Spectrogram Parameters"):
                nperseg = st.slider("Window Length (nperseg)", min_value=26, max_value=208, value=104, step=10)
                noverlap = st.slider("Window Overlap", min_value=10, max_value=100, value=52, step=5)

            signal = detrend(fill_series.values)
            f, t, Sxx = spectrogram(signal, fs=52, nperseg=nperseg, noverlap=noverlap)
            
            start_date = fill_series.index[0]
            dates = start_date + pd.to_timedelta(t * 365.25, unit='D')
            
            fig, ax = plt.subplots(figsize=(12, 6))
            plt.style.use('dark_background')

            # Loop through every subplot axis to make spines, ticks, and labels white again.
            for a in fig.axes:
                # Change frame/spine color
                for spine in a.spines.values():
                    spine.set_edgecolor('white')
    
                # Making everything white because dark background.
                a.tick_params(colors='white')
                a.xaxis.label.set_color('white')
                a.yaxis.label.set_color('white')
                a.title.set_color('white')
            Sxx_db = 10 * np.log10(Sxx + 1e-10)
            im = ax.pcolormesh(dates, f, Sxx_db, shading='gouraud', cmap='viridis')
            ax.set_ylabel('Frequency (Cycles / Year)')
            ax.set_xlabel('Time')
            fig.colorbar(im, ax=ax, label='Power Spectrum (dB/Hz)')

            fig.patch.set_facecolor('none')
            ax.set_facecolor('none')
            st.pyplot(fig)
    else:
        st.warning(f"No reservoir data found for Area Type: **{selected_type}** and Area Number: **{selected_nr}**. Please check your selections.")
else:
    st.warning("Please load your reservoir data first from the home/setup page.")