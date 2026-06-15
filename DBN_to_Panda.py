import math
import pandas as pd
from pathlib import Path
import numpy as np
#from scipy.signal import savgol_filter

FIELD_SIZES = [1,3,4,4,3,2,4,2,2,2,2,2,2]


def decode_time(value):
    total_seconds = value / 100.0
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = total_seconds % 60
    return f"{hours:02d}{minutes:02d}{seconds:06.3f}"


def decode_racelogic(value):
    minutes_total = value / 100000.0
    return minutes_total / 60.0

'''
def time_raw_to_seconds(t):
    cs   = t % 100
    rest = t // 100
    s    = rest % 100
    rest = rest // 100
    m    = rest % 100
    h    = rest // 100
    return h * 3600 + m * 60 + s + cs / 100.0
'''

# =========================
# PARSER (OFÖRÄNDRAD)
# =========================
def read_dbn(filename):
    data = Path(filename).read_bytes()

    start = data.find(b"[DATA]")
    if start < 0:
        raise RuntimeError("DATA-sektion hittades inte")

    records = data[start + len(b"[DATA]"):].split(b"\r\n")
    rows = []

    for rec in records:
        if len(rec) != 34:
            continue

        payload = rec[1:]
        pos = 0
        fields = []

        for size in FIELD_SIZES:
            fields.append(payload[pos:pos+size])
            pos += size

        lat_raw  = int.from_bytes(fields[2], "big", signed=True)
        lon_raw  = int.from_bytes(fields[3], "big", signed=True)
        time_raw = int.from_bytes(fields[1], "big")
        vert_ms  = int.from_bytes(fields[7], "little", signed=True) / 3200.0

        row = {
            "RAW_HEX": rec.hex(),
            "SATS": fields[0][0],
        
            # behåll raw för debug
            "TIME_RAW": time_raw,
        
            # ✅ direkt rätt namn
            #"Elapsed time (s)": time_raw_to_seconds(time_raw),
            "Elapsed time (s)": time_raw / 100.0,
            "lat": decode_racelogic(lat_raw),
            "lon": decode_racelogic(lon_raw),
            "Speed (km/h)": int.from_bytes(fields[4], "big") / 100.0,
            "HEADING_DEG": int.from_bytes(fields[5], "big") / 100.0,
            "HEIGHT_M": int.from_bytes(fields[6], "big", signed=True) / 100.0,
            "VERT_SPEED_KMH": vert_ms * 3.6,
            "YAW_DEG": int.from_bytes(fields[10], "big", signed=True) / 100.0,
        }        
        '''
        row = {
            "RAW_HEX":      rec.hex(),
            "SATS":         fields[0][0],
            "TIME_RAW":     time_raw,
            "TIME":         decode_time(time_raw),
            "LATITUDE":     decode_racelogic(lat_raw),
            "LONGITUDE":    decode_racelogic(lon_raw),
            "VELOCITY_KMH": int.from_bytes(fields[4], "big") / 100.0,
            "HEADING_DEG":  int.from_bytes(fields[5], "big") / 100.0,
            "HEIGHT_M":     int.from_bytes(fields[6], "big", signed=True) / 100.0,
            "VERT_SPEED_KMH": vert_ms * 3.6,
            "YAW_DEG":      int.from_bytes(fields[10], "big", signed=True) / 100.0,
        }
        '''
        rows.append(row)



    return pd.DataFrame(rows)


# =========================
# HUVUDFUNKTION
# =========================
def load_dbn_to_df(filename):

    filename = Path(filename)

    if not filename.exists():
        raise FileNotFoundError(f"Hittar inte filen: {filename}")

    # =====================================
    # Läs DBN (din parser)
    # =====================================
    data_panda = read_dbn(filename)


    # =====================================
    # FILTRERA DÅLIG GPS (viktigt!)
    # =====================================

    data_panda = data_panda[
        (data_panda["SATS"] > 3) &
        (data_panda["lat"].abs() > 0.001) &
        (data_panda["lon"].abs() > 0.001)
    ]

    data_panda = data_panda.reset_index(drop=True)




    # =====================================
    # Tid
    # =====================================
    dt = data_panda["Elapsed time (s)"].diff()
    dt = dt.replace(0, np.nan)
    dt[dt < 0] = np.nan  # hantera midnattsövergång

    # =====================================
    # Koordinater (XY)
    # =====================================
    R = 6371000

    lat = np.radians(data_panda["lat"])
    lon = np.radians(data_panda["lon"])

    lat0 = lat.iloc[0]
    lon0 = lon.iloc[0]

    data_panda["x"] = R * (lon - lon0) * np.cos(lat0)
    data_panda["y"] = R * (lat - lat0)

    # =====================================
    # Acceleration
    # =====================================
    data_panda["VEL_MS"] = data_panda["Speed (km/h)"] / 3.6

    # Longitudinell
    data_panda["ACC_LONG_MS2"] = data_panda["VEL_MS"].diff() / dt
    data_panda["Longitudinal acceleration (g)"] = (
        data_panda["ACC_LONG_MS2"] / 9.81
    )

    # Lateral
    heading_rad = np.radians(data_panda["HEADING_DEG"])
    d_heading = heading_rad.diff()
    d_heading = (d_heading + np.pi) % (2 * np.pi) - np.pi

    heading_rate = d_heading / dt

    data_panda["ACC_LAT_MS2"] = -data_panda["VEL_MS"] * heading_rate
    data_panda["Lateral acceleration (g)"] = (
        data_panda["ACC_LAT_MS2"] / 9.81
    )

    # =====================================
    # Städning
    # =====================================
    mask = data_panda["Speed (km/h)"] < 2

    data_panda.loc[mask, [
        "ACC_LONG_MS2",
        "Longitudinal acceleration (g)",
        "ACC_LAT_MS2",
        "Lateral acceleration (g)"
    ]] = 0

    # klipp spikes
    data_panda["Longitudinal acceleration (g)"] = (
        data_panda["Longitudinal acceleration (g)"].clip(-3, 3)
    )

    data_panda["Lateral acceleration (g)"] = (
        data_panda["Lateral acceleration (g)"].clip(-3, 3)
    )

    # =====================================
    # Returnera
    # =====================================
    df = data_panda
    return df