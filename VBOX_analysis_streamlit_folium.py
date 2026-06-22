# -*- coding: utf-8 -*-
"""
Created on Wed Jun 10 13:52:48 2026

@author: WolrathChristian

kör med cmd sedan 
cd OneDrive - Polestar\Python Scripts\VBox
streamlit run VBOX_analysis_streamlit_folium.py

ToDo:
- lägg in fler banor.
- strukturera om koden så alla beräkningar sker i process session. 
- gör GitHub repot provat.
- lägg till option på att analysera varje segment. (de begöver ju inte vara med fr start.)
- analysera förare mot förare. dvs 2st dbm mot varandra.




"""


import streamlit as st

from streamlit_folium import st_folium
import pickle
import pandas as pd
import folium
import matplotlib.pyplot as plt

import numpy as np

import matplotlib.patheffects as path_effects

import subprocess
import os
import io
import sys






# ==========================================
# HEADER
# ==========================================



col1, col2 = st.columns([4, 1])

with col1:
    st.title("EvilCat VBox Data Analyzer App")
    #st.write(os.getcwd())
    #st.write(os.listdir("."))

with col2:
    #st.image("EvilCat_racing_team.jpg", width=120)
    st.write("No image")


#------------
#  mode selector
# ----------

#st.sidebar.title("Mode")
st.sidebar.title("Session")
print("SESSION STATE:", st.session_state)



# ==========================================
# SESSION STATE INIT
# ==========================================

if "data_loaded" not in st.session_state:
    st.session_state["data_loaded"] = False

if "use_prepared" not in st.session_state:
    st.session_state["use_prepared"] = False


# ==========================================
# STEP 1: LOAD OR PREPARE DATA
# ==========================================

if not st.session_state["data_loaded"]:

    st.title("Load or Prepare Data")

    tab1, tab2 = st.tabs(["Prepare data", "Load pickle file"])

    # -------------------------
    # PREPARE DATA
    # -------------------------
    with tab1:

        dbn_file = st.file_uploader("Drop DBN file", type=["dbn"])
        track = st.selectbox("Track", ["Ring_Knutstorp", "Mantorp"])

        if st.button("Prepare data"):

            if dbn_file is None:
                st.warning("Please upload a DBN file")
            else:
                session_name = os.path.splitext(dbn_file.name)[0]

                with open("temp.dbn", "wb") as f:
                    f.write(dbn_file.getbuffer())

                #cmd = ["python", "process_session.py", session_name, track]
                       
                cmd = [
                    sys.executable,
                    "process_session.py",
                    "temp.dbn",
                    track
                ]


                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True
                )
                
                st.write("Files in folder:")
                st.write(os.listdir("."))

                st.write("Return code:", result.returncode)
                st.code(result.stdout)
                st.code(result.stderr)

                st.session_state["use_prepared"] = True
                st.session_state["session_name"] = session_name
                st.session_state["data_loaded"] = True

                st.success("Data prepared!")
                st.rerun()

    # -------------------------
    # LOAD PICKLE
    # -------------------------
    with tab2:

        uploaded_file = st.file_uploader("Drop pickle file", type=["pkl"])

        if uploaded_file is not None:
            st.session_state["uploaded_file"] = uploaded_file
            st.session_state["use_prepared"] = False
            st.session_state["data_loaded"] = True

            st.rerun()

    st.stop()


# ✅ AUTO SWITCH
if st.session_state.get("force_analyze"):
    mode = "Analyze data"
    #st.session_state["force_analyze"] = False


# ✅ AUTO SWITCH till Analyze
#if st.session_state.get("use_prepared"):
#    st.sidebar.success("Using prepared data")







# ==========================================
# LOAD SESSION DATA
# ==========================================

session_data = None
current_file_name = None

# ✅ prepared data
if st.session_state.get("use_prepared"):

    session_name = st.session_state["session_name"]
    pkl_file_path = f"Analysis_{session_name}.pkl"

    if os.path.exists(pkl_file_path):
        with open(pkl_file_path, "rb") as f:
            session_data = pickle.load(f)

        current_file_name = session_name
    else:
        st.error("Pickle not found!")
        st.stop()

# ✅ uploaded pickle
else:


    uploaded_file = st.session_state["uploaded_file"]

    session_data = pickle.load(
        io.BytesIO(uploaded_file.getvalue())
    )

    current_file_name = uploaded_file.name






# ✅ safety
if session_data is None:
    st.stop()


# ==========================================
# RESET BUTTON SIDEBAR
# ==========================================

#st.sidebar.title("Session")
st.sidebar.success("Data loaded ✅")

if st.sidebar.button("Reset"):
    st.session_state.clear()
    st.rerun()






df = pd.DataFrame(
    session_data["telemetry"]
)
df = df[df["lap"] > 0]



if "last_file_name" not in st.session_state or st.session_state.last_file_name != current_file_name:
    st.session_state.selected_laps = sorted(df["lap"].unique())
    st.session_state.last_file_name = current_file_name



lap_times = pd.DataFrame(
    session_data["lap_times"]
)
lap_times = lap_times[lap_times["lap"] > 0]


start_line = session_data["start_line"]


sector_lines = session_data["sector_lines"]

sector_times = pd.DataFrame(
    session_data["sector_times"]
)
sector_times = sector_times[sector_times["lap"] > 0]

track_name = session_data.get("track_name", "Unknown track")




# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="EvilCat performance review",
    layout="wide"
)

st.title(f"EvilCat performance review - {track_name}")


if st.session_state.get("use_prepared"):
    st.info(f"Using prepared data: {st.session_state.get('session_name')}")



# =============================================================================
# SIDEBAR
# =============================================================================

st.sidebar.header("Controls")


all_laps = sorted(df["lap"].unique())

st.sidebar.write("### Lap selection")

col1, col2 = st.sidebar.columns(2)

select_all = col1.button("Select all")
clear_all = col2.button("Clear")


# init state
if "selected_laps" not in st.session_state:
    st.session_state.selected_laps = all_laps.copy()

# ✅ FILTERA bort laps som inte finns längre
st.session_state.selected_laps = [
    lap for lap in st.session_state.selected_laps
    if lap in all_laps
]

# knappar
if select_all:
    st.session_state.selected_laps = all_laps.copy()

if clear_all:
    st.session_state.selected_laps = []

# multiselect
selected_laps = st.sidebar.multiselect(
    "Select laps",
    options=all_laps,
    default=st.session_state.selected_laps,
    key="selected_laps"
)



show_brake = st.sidebar.checkbox(
    "Show brake points",
    value=True
)

brake_threshold = st.sidebar.slider(
    "Brake threshold (g)",
    min_value=-1.0,
    max_value=-0.2,
    value=-0.6,
    step=0.05
)


show_latg = st.sidebar.checkbox(
    "Show lateral G vectors",
    value=False
)

st.sidebar.markdown("###")   # ✅ mellanrum

st.sidebar.image(
    "EvilCat_racing_team.jpg", width=80,
    
)

# + fade med little hack
st.sidebar.markdown(
    """
    <style>
    img {opacity: 0.3;}
    </style>
    """,
    unsafe_allow_html=True
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
            lap_df["Longitudinal acceleration (g)"] < brake_threshold
            #lap_df[
            #    "Longitudinal acceleration (g)"
            #] < -0.6
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

                color="red", # "cyan"

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



# -----------------------------
# FILTER DATA
# -----------------------------


# Lap times
lap_df_times = lap_times.copy()   # ✅ DENNA SAKNAS

lap_df_times["lap"] = lap_df_times.index

lap_df_times = lap_df_times[
    lap_df_times["lap"].isin(selected_laps)
]

lap_df_times = lap_df_times.set_index("lap")

# Sector times
filtered_sector_times = sector_times[
    sector_times["lap"].isin(selected_laps)
].copy()

# ✅ viktigt (fixar duplicate crash utan att ändra logik)
filtered_sector_times = filtered_sector_times.drop_duplicates(
    subset=["lap", "sector"],
    keep="first"
)

sector_pivot = filtered_sector_times.pivot(
    index="lap",
    columns="sector",
    values="sector_time"
)

# -----------------------------
# MERGE → EN TABELL
# -----------------------------

combined = lap_df_times[["lap_time"]].join(sector_pivot)


combined = combined.sort_index()
# sortera på lap time (valfritt men nice)
#combined = combined.sort_values("lap_time")



# -----------------------------
# BUILD IDEAL LAP
# -----------------------------

# bästa sektor per kolumn
best_sectors = sector_pivot.min()

# summera till ideal lap time
ideal_lap_time = best_sectors.sum()

# skapa rad
ideal_row = pd.DataFrame(
    [[ideal_lap_time] + best_sectors.tolist()],
    columns=combined.columns,
    index=["Ideal"]
)

# lägg till längst ner
combined = pd.concat([combined, ideal_row])






# -----------------------------
# STYLING
# -----------------------------

fastest_lap_time = combined.loc[
    combined.index != "Ideal", "lap_time"
].min()

# ✅ Highlight BARA lap_time cell
def highlight_fastest_lap(col):
    return [
        "background-color: darkgreen; color: white"
        if (v == fastest_lap_time and idx != "Ideal")
        else ""
        for v, idx in zip(col, col.index)
    ]

# ✅ sektorer
def highlight_best_sectors(col):
    if col.name == "lap_time":
        return [""] * len(col)

    min_val = col.loc[col.index != "Ideal"].min()

    return [
        "background-color: darkgreen; color: white"
        if (v == min_val and idx != "Ideal")
        else ""
        for v, idx in zip(col, col.index)
    ]

# ✅ highlight ideal row (lite annan färg)
def highlight_ideal_row(row):
    if row.name == "Ideal":
        return ["background-color: #222; color: yellow"] * len(row)
    else:
        return [""] * len(row)

styled = (
    combined.style
    # center
    .set_properties(**{"text-align": "center"})
    .set_table_styles([
        {"selector": "th", "props": [("text-align", "center")]},
        {"selector": "td", "props": [("text-align", "center")]},
        {"selector": ".row_heading", "props": [("text-align", "center")]}
    ])
    # highlights
    .apply(highlight_fastest_lap, axis=0, subset=["lap_time"])
    .apply(highlight_best_sectors, axis=0)
    .apply(highlight_ideal_row, axis=1)
    # bold lap time
    .set_properties(subset=["lap_time"], **{"font-weight": "bold"})
    # format
    .format("{:.3f}")
)





# =============================================================================
# GG DIAGRAM
# =============================================================================

#st.subheader("GG Diagram")

fig, ax = plt.subplots(figsize=(4, 4))

# -----------------------------
# STYLE (dark theme)
# -----------------------------
ax.set_facecolor("#0b0b0b")
fig.patch.set_facecolor("#0b0b0b")


# -----------------------------
# DATA
# -----------------------------

for i, lap in enumerate(selected_laps):

    lap_df = df[df["lap"] == lap]

    ax.plot(

        lap_df["Lateral acceleration (g)"],

        lap_df["Longitudinal acceleration (g)"],

        #label=f"Lap {lap}",

        color=colors[i % len(colors)],

        linewidth=1.2
    )


# -----------------------------
# LIMITS
# -----------------------------
ax.set_xlim(-2, 2)
ax.set_ylim(-2, 2)
ax.set_aspect("equal")


# -----------------------------
# GRID (circles)
# -----------------------------
radii = np.arange(0.4, 2.1, 0.4)

for r in radii:
    circle = plt.Circle(
        (0, 0),
        r,
        fill=False,
        color="white",
        alpha=0.3,
        linewidth=1
    )
    ax.add_artist(circle)

# -----------------------------
# CROSS LINES
# -----------------------------
ax.axhline(0, color="white", linewidth=1)
ax.axvline(0, color="white", linewidth=1)

# -----------------------------
# CENTER POINT
# -----------------------------

ax.scatter(
    0, 0,
    color="orange",
    s=75,                # lite större
    edgecolor="black",    # ✅ svart ring
    linewidth=0.5,          # ✅ tjocklek på ringen
    zorder=6
)



# -----------------------------
# REMOVE AXES
# -----------------------------
ax.set_xticks([])
ax.set_yticks([])


# -------------------------------------------------------------------------
# STYLE
# -------------------------------------------------------------------------

ax.set_xlabel("Lateral G", color="white", fontsize=6)
ax.set_ylabel("Longitudinal G", color="white", fontsize=6)

ax.xaxis.label.set_color((1, 1, 1, 0.8))
ax.yaxis.label.set_color((1, 1, 1, 0.8))

#ax.grid(True)

ax.set_aspect("equal")

ax.legend()


# -----------------------------
# OPTIONAL: LABEL RINGS
# -----------------------------

for r in radii:
    txt = ax.text(
        r, 0,
        f"{r:.1f}",
        color="white",
        fontsize=8,
        alpha=0.9
    )

    # ✅ Lägg outline (svart kant)
    txt.set_path_effects([
        path_effects.Stroke(linewidth=2, foreground="black"),
        path_effects.Normal()
    ])


# -----------------------------
# SHOW
# -----------------------------





col_times, col_gg = st.columns([1.2, 1])

with col_times:
    st.subheader("Times")
    st.markdown(styled.to_html(), unsafe_allow_html=True)

with col_gg:
    st.subheader("GG Diagram")
    st.pyplot(fig, use_container_width=False)



# -----------------------------
# SECTOR ANALYSIS
# -----------------------------
# -----------------------------
# SECTOR ANALYSIS (SAFE VERSION)
# -----------------------------

st.subheader("Sector Analysis")

# 👉 snabbaste varv (använd redan existerande data)
valid_laps = combined.loc[combined.index != "Ideal"]

if len(valid_laps) == 0:
    st.warning("No laps selected")
else:
    fastest_lap = valid_laps["lap_time"].idxmin()

    # 👉 lokal mapping (påverkar inget annat)
    sector_map = {
        "START": "S1",
        "S1": "S2",
        "S2": "S3",
        "S3": "S4",
        "S4": "S5",
        "S5": "S6"
    }

    for sector in sorted(sector_pivot.columns):

        st.markdown(f"### Sector {sector}")

        col_map, col_plot = st.columns([1, 1])

        # -----------------------------
        # HÄMTA DATA
        # -----------------------------

        best_sector_row = filtered_sector_times[
            filtered_sector_times["sector"] == sector
        ].sort_values("sector_time").iloc[0]

        best_lap = best_sector_row["lap"]

        # 👉 OBS: använder ORIGINAL df (ingen mutation)
        df_sector_best = df[
            (df["lap"] == best_lap) &
            (df["sector"].map(sector_map) == sector)
        ]

        df_sector_fast = df[
            (df["lap"] == fastest_lap) &
            (df["sector"].map(sector_map) == sector)
        ]

        if df_sector_best.empty or df_sector_fast.empty:
            continue

        # -----------------------------
        # MAP
        # -----------------------------
        
        with col_map:

            m_sector = folium.Map(
                location=center,
                zoom_start=16,
                tiles="OpenStreetMap"
            )

            folium.PolyLine(
                df_sector_best[["lat", "lon"]].values,
                color="red",
                weight=5
            ).add_to(m_sector)

            folium.PolyLine(
                df_sector_fast[["lat", "lon"]].values,
                color="blue",
                weight=3
            ).add_to(m_sector)

            st_folium(m_sector, height=300)

        # -----------------------------
        # PLOT
        # -----------------------------
        
  
        with col_plot:
        
            fig_s, ax_s = plt.subplots(figsize=(4, 3))
        
            # ✅ NORMALISERA TID (starta på 0)
            t_best = df_sector_best["Elapsed time (s)"]
            t_best = t_best - t_best.iloc[0]
        
            t_fast = df_sector_fast["Elapsed time (s)"]
            t_fast = t_fast - t_fast.iloc[0]
        
            # ✅ BEST
            ax_s.plot(
                t_best,
                df_sector_best["Speed (km/h)"],
                color="red",
                label=f"Best {sector}"
            )
        
            # ✅ FASTEST LAP
            ax_s.plot(
                t_fast,
                df_sector_fast["Speed (km/h)"],
                color="blue",
                linestyle="--",
                label="Fastest lap"
            )
        
            ax_s.set_title(sector)
            ax_s.set_xlabel("Time (s)")
            ax_s.set_ylabel("Speed (km/h)")
            ax_s.grid(True)
            ax_s.legend(fontsize=8)
        
            st.pyplot(fig_s)
