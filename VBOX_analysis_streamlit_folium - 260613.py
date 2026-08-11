# -*- coding: utf-8 -*-
"""
Created on Wed Jun 10 13:52:48 2026

@author: WolrathChristian

kör med cmd sedan 
cd OneDrive - Polestar\Python Scripts\VBox
streamlit run VBOX_analysis_streamlit_folium.py

"""


import streamlit as st

from streamlit_folium import st_folium
import pickle
import pandas as pd
import folium
import matplotlib.pyplot as plt

import numpy as np





# =============================================================================
# LOAD PICKLE
# =============================================================================

uploaded_file = st.file_uploader(
    "Choose session pickle to analyze",
    type=["pkl"]
)

if uploaded_file is None:
    st.stop()

session_data = pickle.load(
    uploaded_file
)

df = pd.DataFrame(
    session_data["telemetry"]
)

lap_times = pd.DataFrame(
    session_data["lap_times"]
)

start_line = session_data["start_line"]


sector_lines = session_data["sector_lines"]

sector_times = pd.DataFrame(
    session_data["sector_times"]
)

track_name = session_data.get("track_name", "Unknown track")


# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="EvilCat performance review",
    layout="wide"
)

st.title(f"EvilCat performance review - {track_name}")




# =============================================================================
# SIDEBAR
# =============================================================================

st.sidebar.header("Controls")

selected_laps = st.sidebar.multiselect(

    "Select laps",

    options=sorted(df["lap"].unique()),

    default=[1]
)

show_brake = st.sidebar.checkbox(
    "Show brake points",
    value=True
)

show_latg = st.sidebar.checkbox(
    "Show lateral G vectors",
    value=False
)


# =============================================================================
# CREATE MAP
# =============================================================================

center = [
    df["lat"].mean(),
    df["lon"].mean()
]


m = folium.Map(
    location=center,
    zoom_start=16,
    tiles=None,
    control_scale=True
)



# OSM
folium.TileLayer(
    "OpenStreetMap",
    name="OpenStreetMap",
    overlay=False,
    control=True
).add_to(m)

# LIGHT
folium.TileLayer(
    "CartoDB positron",
    name="Light",
    overlay=False,
    control=True
).add_to(m)

# DARK
folium.TileLayer(
    "CartoDB dark_matter",
    name="Dark",
    overlay=False,
    control=True
).add_to(m)

# SATELLITE
folium.TileLayer(
    tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
    attr="Google",
    name="Google Satellite",
    overlay=False,
    control=True
).add_to(m)


# -------------------------------------------------------------------------
# COLORS
# -------------------------------------------------------------------------

colors = [
    "red",
    "blue",
    "green",
    "yellow",
    "magenta",
    "cyan",
    "orange"
]


# =============================================================================
# DRAW LAPS
# =============================================================================

for i, lap in enumerate(selected_laps):

    lap_df = df[df["lap"] == lap]

    if len(lap_df) < 2:
        continue

    points = lap_df[
        ["lat", "lon"]
    ].values.tolist()

    lap_time = (
        lap_df["Elapsed time (s)"].max()
        - lap_df["Elapsed time (s)"].min()
    )

    # -------------------------------------------------------------------------
    # TRACK
    # -------------------------------------------------------------------------

    folium.PolyLine(

        points,

        color=colors[i % len(colors)],

        weight=4,

        tooltip=f"Lap {lap} ({lap_time:.2f}s)"

    ).add_to(m)

    # -------------------------------------------------------------------------
    # BRAKING
    # -------------------------------------------------------------------------

    if show_brake:

        brake_df = lap_df[
            lap_df[
                "Longitudinal acceleration (g)"
            ] < -0.6
        ]

        for _, row in brake_df.iterrows():

            brake_g = abs(
                row["Longitudinal acceleration (g)"]
            )

            folium.CircleMarker(

                location=[
                    row["lat"],
                    row["lon"]
                ],

                radius=2 + brake_g * 6,

                color="cyan",

                fill=True,

                fill_opacity=0.8,

                tooltip=(
                    f"Speed: "
                    f"{row['Speed (km/h)']:.1f} km/h"
                )

            ).add_to(m)

    # -------------------------------------------------------------------------
    # LAT G FAN
    # -------------------------------------------------------------------------

    if show_latg:

        lap_df = lap_df.reset_index(drop=True)

        step = 1  # hur många data punter skall hoppas över 1 ör alla datanpunker
        
        for j in range(1, len(lap_df) - 1, step):

            lon1 = lap_df["lon"].iloc[j - 1]
            lat1 = lap_df["lat"].iloc[j - 1]

            lon2 = lap_df["lon"].iloc[j + 1]
            lat2 = lap_df["lat"].iloc[j + 1]

            dx = lon2 - lon1
            dy = lat2 - lat1

            length = np.hypot(dx, dy)

            if length == 0:
                continue

            dx /= length
            dy /= length

            nx = -dy
            ny = dx

            lat_g = lap_df[
                "Lateral acceleration (g)"
            ].iloc[j]

            scale = 0.00008   #   <- längden på . 

            px = lap_df["lon"].iloc[j]
            py = lap_df["lat"].iloc[j]

            x_end = px - nx * lat_g * scale
            y_end = py - ny * lat_g * scale

            folium.PolyLine(

                [
                    [py, px],
                    [y_end, x_end]
                ],

                color="deepskyblue",

                weight=2,

                opacity=0.8

            ).add_to(m)


# =============================================================================
# START / FINISH LINE
# =============================================================================

finish_points = [
    [start_line[0][1], start_line[0][0]],
    [start_line[1][1], start_line[1][0]]
]

folium.PolyLine(

    finish_points,

    color="red",

    weight=6,

    tooltip="Start / Finish"

).add_to(m)

# =============================================================================
# SECTOR LINES
# =============================================================================

for sector_name, coords in sector_lines.items():

    # convert lon/lat -> lat/lon for folium
    points = [

        [coords[0][1], coords[0][0]],
        [coords[1][1], coords[1][0]]

    ]

    folium.PolyLine(

        points,

        color="red",

        weight=3,

        opacity=0.9,

        tooltip=f"Sector {sector_name}"

    ).add_to(m)

    # -------------------------------------------------------------------------
    # SECTOR LABEL (offset från linjen)
    # -------------------------------------------------------------------------
    
   
    # välj ÖVRE punkt (högst lat)
    if coords[0][1] > coords[1][1]:
        lon1, lat1 = coords[0]
        lon2, lat2 = coords[1]
    else:
        lon1, lat1 = coords[1]
        lon2, lat2 = coords[0]
    
    # riktning längs linjen
    dx = lon2 - lon1
    dy = lat2 - lat1
    
    length = np.hypot(dx, dy)
    
    if length == 0:
        dx, dy = 0, 1
    else:
        dx /= length
        dy /= length
    
    # normal
    nx = -dy
    ny = dx
    
    # ----------------------------------------
    # UTGÅ DIREKT FRÅN ÖVRE PUNKT ✅
    # ----------------------------------------
    
    offset = 0.00025
    offset2 = -0.00025
    
    label_lon = lon1 + nx * offset
    label_lat = lat1 + ny * offset2

    
 
    # -------------------------------------------------------------------------
    # LABEL
    # -------------------------------------------------------------------------

    folium.Marker(

        [label_lat, label_lon],

        icon=folium.DivIcon(
            html=f"""
            <div style="
                font-size:14px;
                color:black;
                text-align:center;
            ">
                {sector_name}
            </div>
            """
        )

    
    ).add_to(m)


# =============================================================================
# ADD LAYER CONTROL
# =============================================================================

folium.LayerControl(
    position="topright"
).add_to(m)

# =============================================================================
# SHOW MAP
# =============================================================================

st_data = st_folium(
    m,
    width=None,
    height=700,
    returned_objects=[]
)


# =============================================================================
# LAP TIMES
# =============================================================================

st.subheader("Lap Times")

st.dataframe(
    lap_times[["lap_time"]]
)

# =============================================================================
# SECTOR TIMES
# =============================================================================

st.subheader("Sector Times")

filtered_sector_times = sector_times[
    sector_times["lap"].isin(selected_laps)
]

pivot_sector = filtered_sector_times.pivot(

    index="lap",

    columns="sector",

    values="sector_time"

)


styled_sector_table = pivot_sector.style.highlight_min(
    axis=0,
    color="darkgreen"
)

st.dataframe(
    styled_sector_table
)




# =============================================================================
# GG DIAGRAM
# =============================================================================

st.subheader("GG Diagram")

fig, ax = plt.subplots(
    figsize=(6, 6)
)

for i, lap in enumerate(selected_laps):

    lap_df = df[df["lap"] == lap]

    ax.plot(

        lap_df["Lateral acceleration (g)"],

        lap_df["Longitudinal acceleration (g)"],

        label=f"Lap {lap}",

        color=colors[i % len(colors)],

        linewidth=1.5
    )

# -------------------------------------------------------------------------
# STYLE
# -------------------------------------------------------------------------

ax.set_xlabel("Lateral G")
ax.set_ylabel("Longitudinal G")

ax.grid(True)

ax.set_aspect("equal")

ax.legend()

# friction circles
for r in [0.5, 1.0, 1.5, 2.0]:

    circle = plt.Circle(
        (0, 0),
        r,
        fill=False,
        color="gray",
        linewidth=0.5
    )

    ax.add_artist(circle)

st.pyplot(fig)

