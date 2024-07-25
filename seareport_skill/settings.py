from __future__ import annotations

import colorcet as cc

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
    "Correlation Coefficient": "cr",
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


TYPE_SELECT = {
    "Oceans": "ocean",
    "Maritime Sectors": "name",
}

OCEANS = [
    "Arctic",
    "Atlantic",
    "Antarctic",
    "Baltic Sea",
    "Black Sea",
    "Caribbeans",
    "Caspian",
    "Indian",
    "Mediterranean",
    "Pacific",
    "SE Asia",
]

SECTORS = [
    "Arctic US",
    "Arctic Europe",
    "Arctic Russia",
    "NE Pacific",
    "NW Pacific",
    "SE Pacific",
    "SW Pacific",
    "North Western Passages",
    "Hudson Bay",
    "NW Atlantic",
    "Gulf of Mexico" "Caribbean Sea",
    "NE Atlantic",
    "Irish Sea",
    "English Channel",
    "North Sea",
    "Baltic Sea",
    "Bay of Biscay" "Adriatic Sea",
    "Mediterranean Sea",
    "Aegean Sea",
    "Sea of Marmara",
    "Black Sea",
    "SW Atlantic",
    "SE Atlantic",
    "Red Sea",
    "East Africa",
    "Persian Gulf",
    "North Indian",
    "West Australia",
    "Okhotsk Sea",
    "Japan Sea",
    "Yellow Sea",
    "South China Sea",
    "Andaman Sea",
    "Sibuyan Sea",
    "Celebes Sea",
    "Java Sea",
    "Banda Sea",
    "Arafura Sea",
    "Antarctic Ocean",
    "Caspian Sea",
]

PLOT_TYPE = {
    "Box Plot": "box",
    "Violin Plot": "violin",
    "Histogram": "hist",
}

METRICS_DOC = r"""
# Metrics information
We compare 2 time series:
 * `sim`: modelled surge time series
 * `mod`: observed surge time series

We need metrics to assess the quality of the model.
## A. Dimensional Statistics:
### Mean Error (or Bias)
$$\langle x_c - x_m \rangle = \langle x_c \rangle - \langle x_m \rangle$$
### RMSE (Root Mean Squared Error)
$$\sqrt{\langle(x_c - x_m)^2\rangle}$$
### Mean-Absolute Error (MAE):
$$\langle |x_c - x_m| \rangle$$
## B. Dimentionless Statistics (best closer to 1)

### Performance Scores (PS) or Nash-Sutcliffe Eff (NSE): $$1 - \frac{\langle (x_c - x_m)^2 \rangle}{\langle (x_m - x_R)^2 \rangle}$$
### Correlation Coefficient (R):
$$\frac {\langle x_{m}x_{c}\rangle -\langle x_{m}\rangle \langle x_{c}\rangle }{{\sqrt {\langle x_{m}^{2}\rangle -\langle x_{m}\rangle ^{2}}}{\sqrt {\langle x_{c}^{2}\rangle -\langle x_{c}\rangle ^{2}}}}$$
### Kling–Gupta Efficiency (KGE):
$$1 - \sqrt{(r-1)^2 + b^2 + (g-1)^2}$$
with :
 * `r` the correlation
 * `b` the modified bias term (see [ref](https://journals.ametsoc.org/view/journals/clim/34/16/JCLI-D-21-0067.1.xml)) $$\frac{\langle x_c \rangle - \langle x_m \rangle}{\sigma_m}$$
 * `g` the std dev term $$\frac{\sigma_c}{\sigma_m}$$

### Lambda index ($$\lambda$$), values closer to 1 indicate better agreement:
$$\lambda = 1 - \frac{\sum{(x_c - x_m)^2}}{\sum{(x_m - \overline{x}_m)^2} + \sum{(x_c - \overline{x}_c)^2} + n(\overline{x}_m - \overline{x}_c)^2 + \kappa}$$
 * with $$\kappa = 2 \cdot \left| \sum{((x_m - \overline{x}_m) \cdot (x_c - \overline{x}_c))} \right|$$

## C. Storm metrics:
we defined the following metrics for the storms events:

* `R1`/`R3`/`error_metric`: we select the biggest observated storms, and then calculate error (so the absolute value of differenc between the model and the observed peaks)
  * `R1` is the error for the biggest storm
  * `R3` is the mean error for the 3 biggest storms
  * `error_metric` is the mean error for all the storms above the threshold.

* `R1_norm`/`R3_norm`/`error`: Same methodology, but values are in normalised (in %) by the observed peaks.

More info in the dedicated [`seastats`](https://github.com/seareport/seastats) package


this happens when the function `storms/match_extremes.py` couldn't finc concomitent storms for the observed and modeled time series.

## D. Slope parameters
more info can be found [in this preprint](https://doi.org/10.5194/egusphere-2024-1415) from Campos-Caba et. al.
"""

TABULATOR_CSS = """
.tabulator-cell {
    font-size: 10px;
}
.tabulator-col-title {
    font-size: 11px;
}
.tabulator-row {
  vertical-align: middle;
  height: 6px;
  margin: -5px;
  padding: -5px;
}

"""

TABULATOR_FORMATTER = {
    "rmse": {"type": "progress", "min": 0, "max": 0.2, "color": cc.CET_R4},
    "rms": {"type": "progress", "min": 0, "max": 0.2, "color": cc.CET_R4},
    "rms_95": {"type": "progress", "min": 0, "max": 0.2, "color": cc.CET_R4},
    "bias": {"type": "progress", "min": -0.2, "max": 0.2, "color": cc.coolwarm},
    "kge": {"type": "progress", "min": 0, "max": 1, "color": cc.CET_R4[::-1]},
    "nse": {"type": "progress", "min": 0, "max": 1, "color": cc.CET_R4[::-1]},
    "lamba": {"type": "progress", "min": 0, "max": 1, "color": cc.CET_R4[::-1]},
    "slope": {"type": "progress", "min": 0.5, "max": 1.5, "color": cc.coolwarm},
    "slope_pp": {"type": "progress", "min": 0.5, "max": 1.5, "color": cc.coolwarm},
    "cr": {"type": "progress", "min": 0, "max": 1, "color": cc.CET_R4[::-1]},
    "cr_95": {"type": "progress", "min": 0, "max": 1, "color": cc.CET_R4[::-1]},
    "mad": {"type": "progress", "min": 0, "max": 0.2, "color": cc.CET_R4},
    "madp": {"type": "progress", "min": 0, "max": 0.1, "color": cc.CET_R4},
    "R1_norm": {"type": "progress", "min": 0, "max": 1, "color": cc.CET_R4},
    "R3_norm": {"type": "progress", "min": 0, "max": 1, "color": cc.CET_R4},
    "error95": {"type": "progress", "min": 0, "max": 1, "color": cc.CET_R4},
    "error99": {"type": "progress", "min": 0, "max": 1, "color": cc.CET_R4},
    "R1": {"type": "progress", "min": 0, "max": 0.5, "color": cc.CET_R4},
    "R3": {"type": "progress", "min": 0, "max": 0.5, "color": cc.CET_R4},
    "error95m": {"type": "progress", "min": 0, "max": 0.5, "color": cc.CET_R4},
    "error99m": {"type": "progress", "min": 0, "max": 0.5, "color": cc.CET_R4},
}

TABULATOR_CONFIG = {}
