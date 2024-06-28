from __future__ import annotations


# Constants and configuration
SURGE_FOLDER = "./obs/surge/"
STATS_JSON = "assets/stats_all.json"
TMIN = "2023-01-01"
TMAX = "2023-12-31"
VERSIONS = {
    "Global 50km": "v0.0",
    "Global 20km": "v0.2",
    "Global 7km": "v1.2",
    "Global 3km, L5 GSSHS": "v2.1",
    "Global 3km, L6 GSSHS": "v2.2",
}

PLOT_OPTS = {
    "ts_view": dict(width=1000, height=600),
    "taylor_view": dict(width=700, height=700),
    "radar_view": dict(width=500, height=500),
    "hist_view": dict(width=1000, height=400),
    "mod_opts_raster": dict(cmap=["blue"]),
    "mod_opts": dict(color="blue"),
    "obs_opts_raster": dict(cmap=["red"]),
    "obs_opts": dict(color="red"),
}

METRICS = {
    "Root Mean Square Error": "rmse",
    "Root Mean Square [m]": "rms",
    "Root Mean Square >95th percentile": "rms_95",
    "Bias [m]": "bias",
    "Kling-Guplta efficiency": "kge",
    "Nash-Sutcliffe model efficiency": "nse",
    "Lamba index": "lamba",
    "Slope": "slope",
    "Slope of percentiles": "slope_pp",
    "Correation Coefficient": "cr",
    "Correlation Coefficient >95th percentile": "cr_95",
    "Mean Absolute deviation": "mad",
    "Mean Absolute deviation of percentiles": "madp",
    "Normalized error on highest peak": "R1_norm",
    "Normalized error on 3 highest peaks": "R3_norm",
    "Normalized error on peaks >95th percentile": "error95",
    "Normalized error on peaks >99th percentile": "error99",
    "Error on highest peak [m]": "R1",
    "Error on 3 highest peaks [m]": "R3",
    "Error on peaks >95th percentile [m]": "error95m",
    "Error on peaks >99th percentile [m]": "error99m",
}

METRICS_SPIDER = {
    "Slope": "slope",
    "Root Mean Square [m]": "rms",
    "Correlation Coefficient": "cr",
    "Root Mean Square >95th percentile": "rms_95",
    "Correlation Coefficient >95th percentile": "cr_95",
    "Error on highest peak [m]": "R1",
    "Error on 3 highest peaks [m]": "R3",
    "Error on peaks >95th percentile [m]": "error95m",
    "Error on peaks >99th percentile [m]": "error99m",
}

OCEANS_SPIDER = [
    "North Pacific Ocean",
    "South Pacific Ocean",
    "North Atlantic Ocean US",
    "English Channel",
    "North Sea",
    "Bay of Biscay",
    "Mediterranean Sea",
    "South Atlantic Ocean",
    "INDIAN OCEAN",
    "Sea of Japan",
    "Yellow Sea",
    "North Atlantic Ocean EU",
]

PLOT_TYPE = {
    "Box Plot": "box",
    "Violin Plot": "violin",
    "Histogram": "hist",
}
