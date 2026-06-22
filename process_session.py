# -*- coding: utf-8 -*-
"""
Created on Wed Jun 10 13:46:46 2026

@author: WolrathChristian

KÖR fr cmd!! inte run i Spydern för dset är olika versioner av python och då fungerar inte pickle!!

cd OneDrive - Polestar\Python Scripts\VBox

python process_session.py PBOX_008 Ring_Knutstorp
    borde fungera samma .csv och .dbn


"""


#from csv_to_panda import load_pbox_csv
from DBN_to_Panda import load_dbn_to_df
import pandas as pd
import numpy as np 
import geopandas as gpd

import sys
from pathlib import Path


from shapely.geometry import Point
from shapely.geometry import LineString


import pickle
from geopy.distance import geodesic

# =============================================================================
# INPUT ARGUMENTS
# =============================================================================
if len(sys.argv) < 3:

    print(
        "Usage:\n"
        "python process_session.py <FILE_NAME> <TRACK_NAME>\n"
        "Example:\n"
        "python process_session.py PBOX_008 Ring_Knutstorp"
    )

    sys.exit()
file_name = sys.argv[1]
session_name = sys.argv[2]
track_name = sys.argv[3]
#input_file = f"DATA/{file_name}.csv"
#input_file = f"DATA/{file_name}.DBN"  # <-- behövs när man kör local't




# =============================================================================
# START / FINISH LINE   (google maps och tryck punkt för punkt)
# =============================================================================
# =============================================================================
# TRACK DATABASE
# =============================================================================

tracks = {

    "Ring_Knutstorp": {

        "start_line": [
            (13.113418, 55.987168),
            (13.113613, 55.9873207),
        ],

        "sector_lines": {

            # vänster -> höger i bilens färdriktning

            "S1": [
                (13.110729, 55.988163),
                (13.110902, 55.988340),
            ],

            "S2": [
                (13.113376, 55.988647),
                (13.113004, 55.988411),
            ],

            "S3": [
                (13.117236, 55.987083),
                (13.116645, 55.986504),
            ],

            "S4": [
                (13.120171, 55.986686),
                (13.119882, 55.986196),
            ],

            "S5": [
                (13.118346, 55.985780),
                (13.118093, 55.986235),
            ],
        }
    }

}
''' debug only
track_name = "Ring_Knutstorp"
'''



# =============================================================================
# INPUT FILE
# =============================================================================
'''
input_file = "DATA/PBOX_008_3.csv"
'''

# =============================================================================
# SELECT TRACK
# =============================================================================

if track_name not in tracks:

    print(
        f"\nTrack '{track_name}' not found!\n"
        "Please add start/finish and sector_lines for this track.\n"
    )

    sys.exit()


track_data = tracks[track_name]

start_line = track_data["start_line"]
finish_line = LineString(start_line)
sector_lines = track_data["sector_lines"]


sector_geometries = {}

for name, coords in sector_lines.items():

    sector_geometries[name] = LineString(coords)


# =============================================================================
# LOAD CSV
# =============================================================================

#df = load_pbox_csv(input_file)

df = load_dbn_to_df(input_file)
#df = load_dbn_to_df("DATA/PBOX_008.dbn")



print(df.head())

print(df.tail(30))


#%%
# =============================================================================
# CREATE GEODATAFRAME
# =============================================================================

geometry = [
    Point(xy)
    for xy in zip(df["lon"], df["lat"])
]

gdf = gpd.GeoDataFrame(
    df,
    geometry=geometry,
    crs="EPSG:4326"
)

gdf_3857 = gdf.to_crs(epsg=3857)

finish_gdf = gpd.GeoSeries(
    [finish_line],
    crs="EPSG:4326"
).to_crs(epsg=3857)

finish_line_3857 = finish_gdf.iloc[0]


sector_lines_3857 = {}

for name, line in sector_geometries.items():

    sector_lines_3857[name] = gpd.GeoSeries(
        [line],
        crs="EPSG:4326"
    ).to_crs(epsg=3857).iloc[0]


# =============================================================================
# SIDE OF LINE
# =============================================================================

def side_of_line(px, py, line):

    x1, y1 = line.coords[0]
    x2, y2 = line.coords[1]

    return (
        (x2 - x1) * (py - y1)
        - (y2 - y1) * (px - x1)
    )


# =============================================================================
# LAP + SECTOR DETECTION
# =============================================================================

# =============================================================================
# LAP + SECTOR DETECTION (FINAL VERSION)
# =============================================================================

# Förbered numpy arrays (snabbt!)
px_all = gdf_3857.geometry.x.values
py_all = gdf_3857.geometry.y.values
speed_all = df["Speed (km/h)"].values
time_all = df["Elapsed time (s)"].values

n = len(px_all)

laps = np.zeros(n, dtype=int)
sectors = np.empty(n, dtype=object)

lap_number = 0
last_crossing_index = -10000

prev_finish_side = None

# ✅ separata tidsvariabler
last_lap_time = None
last_sector_time = None

prev_sector_sides = {name: None for name in sector_lines_3857}
sector_crossings = []

current_sector = "START"

# Pre-calc finish line coords
fx1, fy1 = finish_line_3857.coords[0]
fx2, fy2 = finish_line_3857.coords[1]

# Pre-calc sector lines coords
sector_coords = {
    name: line.coords[:]
    for name, line in sector_lines_3857.items()
}

for i in range(n):

    px = px_all[i]
    py = py_all[i]
    speed = speed_all[i]
    t = time_all[i]

    # -------------------------------------------------------------------------
    # FINISH LINE
    # -------------------------------------------------------------------------
    current_finish_side = (
        (fx2 - fx1) * (py - fy1) -
        (fy2 - fy1) * (px - fx1)
    )

    if prev_finish_side is not None:

        crossed = (
            (prev_finish_side < 0) and
            (current_finish_side > 0)
        )

        if (
            crossed and
            (i - last_crossing_index > 300) and
            (speed > 50)
        ):
            crossing_time = t

            # ✅ PRINT VARVTID (rätt nu)
            if last_lap_time is not None:
                lap_time = crossing_time - last_lap_time
                print(f"Lap {lap_number} completed in {lap_time:.2f}s")
            else:
                print(f"Lap crossing -> {lap_number}")

            # gå till nästa lap
            lap_number += 1

            print(f"--- Starting Lap {lap_number} ---")

            # ✅ reset sector timing vid ny lap
            last_lap_time = crossing_time
            last_sector_time = crossing_time

            current_sector = "START"
            last_crossing_index = i

            sector_crossings.append({
                "lap": lap_number,
                "sector": "START",
                "time": crossing_time
            })

    prev_finish_side = current_finish_side

    # -------------------------------------------------------------------------
    # SECTORS
    # -------------------------------------------------------------------------
    for sector_name, (p1, p2) in sector_coords.items():

        sx1, sy1 = p1
        sx2, sy2 = p2

        current_sector_side = (
            (sx2 - sx1) * (py - sy1) -
            (sy2 - sy1) * (px - sx1)
        )

        previous_side = prev_sector_sides[sector_name]

        if previous_side is not None:

            crossed = (
                (previous_side < 0) and
                (current_sector_side > 0)
            )

            if crossed:
                crossing_time = t

                # ✅ PRINT SEKTORTID (rätt nu)
                if last_sector_time is not None:
                    sector_time = crossing_time - last_sector_time

                    print(
                        f"[Lap {lap_number:02d}] "
                        f"{sector_name:<3} | {sector_time:6.2f}s"
                    )
                else:
                    print(f"Lap {lap_number} crossed {sector_name}")

                # ✅ uppdatera sector-tid
                last_sector_time = crossing_time
                current_sector = sector_name

                sector_crossings.append({
                    "lap": lap_number,
                    "sector": sector_name,
                    "time": crossing_time
                })

        prev_sector_sides[sector_name] = current_sector_side

    laps[i] = lap_number
    sectors[i] = current_sector


# skriv tillbaka till df
df["lap"] = laps
df["sector"] = sectors
# =============================================================================
# DISTANCE CHANNEL
# =============================================================================



lat = np.radians(df["lat"].values)
lon = np.radians(df["lon"].values)

dlat = lat[1:] - lat[:-1]
dlon = lon[1:] - lon[:-1]

a = np.sin(dlat / 2)**2 + np.cos(lat[:-1]) * np.cos(lat[1:]) * np.sin(dlon / 2)**2
dists = 2 * 6371000 * np.arcsin(np.sqrt(a))

df["distance_m"] = np.concatenate([[0], np.cumsum(dists)])

"""
distances = [0]

# SNABBT - vektoriserad Haversine med numpy (~100x snabbare)
def haversine_np(lat1, lon1, lat2, lon2):
    R = 6371000  # meter 6_371_000
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    return R * 2 * np.arcsin(np.sqrt(a))

lat = df["lat"].values
lon = df["lon"].values

dists = haversine_np(lat[:-1], lon[:-1], lat[1:], lon[1:])
df["distance_m"] = np.concatenate([[0], np.cumsum(dists)])
"""
# LÅNGSAMT - geodesic() per rad
'''

for i in range(1, len(df)):

    p1 = (
        df["lat"].iloc[i - 1],
        df["lon"].iloc[i - 1]
    )

    p2 = (
        df["lat"].iloc[i],
        df["lon"].iloc[i]
    )

    d = geodesic(p1, p2).meters

    distances.append(
        distances[-1] + d
    )

df["distance_m"] = distances
'''



#%%
# =============================================================================
# LAP DISTANCE
# =============================================================================

df["lap_distance_m"] = (
    df.groupby("lap")["distance_m"]
    .transform(lambda x: x - x.min())
)


# =============================================================================
# LAP TIMES
# =============================================================================

lap_times = df.groupby("lap")[
    "Elapsed time (s)"
].agg(["min", "max"])

lap_times["lap_time"] = (
    lap_times["max"]
    - lap_times["min"]
)



# =============================================================================
# SECTOR TIMES
# =============================================================================

sector_times = []

crossings_df = pd.DataFrame(sector_crossings).sort_values("time")

n_sectors = len(sector_lines)

# loop över alla crossings i tidsordning
previous_time = None
previous_lap = None

for _, row in crossings_df.iterrows():

    current_time = row["time"]
    current_sector = row["sector"]
    current_lap = row["lap"]

    if previous_time is None:
        previous_time = current_time
        previous_lap = current_lap
        continue

    # ------------------------------------------------------
    # NORMAL SEKTOR (inom samma lap)
    # ------------------------------------------------------

    if current_lap == previous_lap:

        if current_sector != "START":

            sector_times.append({
                "lap": current_lap,
                "sector": current_sector,
                "sector_time": current_time - previous_time
            })

    # ------------------------------------------------------
    # NY LAP → skapa S6 för FÖREGÅENDE lap ✅
    # ------------------------------------------------------

    else:

        sector_times.append({
            "lap": previous_lap,
            "sector": f"S{n_sectors + 1}",
            "sector_time": current_time - previous_time
        })

    previous_time = current_time
    previous_lap = current_lap

sector_times_df = pd.DataFrame(sector_times)






# =============================================================================
# SESSION OBJECT
# =============================================================================


session_data = {

    "telemetry": df.to_dict("list"),

    "lap_times":
        lap_times.reset_index().to_dict("list"),

    "sector_times":
        sector_times_df.to_dict("list"),

    "start_line": start_line,

    "sector_lines": sector_lines,
    
    "track_name": track_name   
}

# =============================================================================
# SAVE PICKLE
# =============================================================================

#base_name = Path(input_file).stem

#output_pkl = f"Analysis_{base_name}.pkl"
output_pkl = f"Analysis_{session_name}.pkl"

with open(output_pkl, "wb") as f:

    pickle.dump(
        session_data,
        f
    )

print(f"Saved: {output_pkl}")



#%% TEST print
"""

import matplotlib.pyplot as plt


data_sel = df.iloc[15658:17358]  # +1 för att inkludera 17184

plt.figure(figsize=(10,5))

plt.plot(data_sel.index, data_sel["Longitudinal acceleration (g)"], label="Longitudinal G")
#plt.plot(data_sel.index, data_sel["Lateral acceleration (g)"], label="Lateral acc [g]")
#plt.plot(data_sel.index, data_sel[13], label="Lateral acc [g]")

plt.xlabel("Index")
plt.ylabel("Acceleration (g)")
plt.title("Acceleration vs Index")
plt.legend()
plt.grid()

plt.show()

"""
