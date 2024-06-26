import glob
import json
from typing import Any
from typing import Dict
from typing import Optional

import geopandas as gp
import holoviews as hv
import hvplot.pandas  # noqa: F401
import pandas as pd
import panel as pn
import param
import shapely

from utils.hists import hist_
from utils.hists import radar_plot
from utils.hists import scatter_hist
from utils.taylor import taylor_diagram

hv.extension("bokeh")

# Constants and configuration
SURGE_FOLDER = "./obs/surge/"
STATS_JSON = "assets/stats_all.json"
TMIN = "2023-01-01"
TMAX = "2023-12-31"
VERSIONS = {
    "Global 50km": "v0",
    "Global 20km": "v0.2",
    "Global 7km": "v1.2",
    "Global 3km, L5 GSSHS": "v2.1",
    "Global 3km, L6 GSSHS": "v2.2",
    # Add other versions here
}

PLOT_OPTS = {
    "ts_view": dict(width=1000, height=600),
    "taylor_view": dict(width=700, height=700),
    "radar_view": dict(width=700, height=700),
    "hist_view": dict(width=1000, height=400),
    "mod_opts_raster": dict(cmap=["blue"]),
    "mod_opts": dict(color="blue"),
    "obs_opts_raster": dict(cmap=["red"]),
    "obs_opts": dict(color="red"),
}

PARAMS = {
    "Root Mean Square Error": "rmse",
    "Root Mean Square [m]": "rms",
    "Root Mean Square >95th percentile": "rms_95",
    "Bias [m]": "bias",
    "Kling-Guplta efficiency": "kge",
    "Nash-Sutcliffe model efficiency": "nse2",
    "Lamba index": "lamba",
    "Slope": "slope",
    "Slope of percentiles": "slopepp",
    "Correation Coefficient": "cr",
    "Correlation Coefficient >95th percentile": "cr_95",
    "Mean Absolute deviation": "mad",
    "Mean Absolute deviation of percentiles": "madp",
    "Normalized error on highest peak": "R1_norm",
    "Normalized error on 3 highest peaks": "R3_norm",
    "Normalized error on peaks >95th percentile": "error99",
    "Normalized error on peaks >99th percentile": "error95",
    "Error on highest peak [m]": "R1",
    "Error on 3 highest peaks [m]": "R3",
    "Error on peaks >95th percentile [m]": "error95m",
    "Error on peaks >99th percentile [m]": "error99m",
}

PARAMS_SPIDER = {
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

PLOT_TYPE = {
    "Box Plot": "box",
    "Violin Plot": "violin",
    "Histogram": "hist",
}


def load_data() -> pd.DataFrame:
    seaset = pd.read_csv(
        "https://raw.githubusercontent.com/tomsail/seaset/main/Notebooks/catalog_full.csv",
        index_col=0,
    )
    list_clean = glob.glob("*.parquet", root_dir=SURGE_FOLDER)
    ioc_cleanup_list = [item.split(".")[0] for item in list_clean]
    stations_df = seaset[seaset.ioc_code.isin(ioc_cleanup_list)]
    return stations_df


def load_stats() -> Dict[str, Any]:
    with open(STATS_JSON) as f:
        stats = json.load(f)
    return stats


def find_ocean_for_station(
    station, oceans_df, xstr="longitude", ystr="latitude"
) -> Optional[str]:
    point = shapely.geometry.Point(station[xstr], station[ystr])
    for _, ocean in oceans_df.iterrows():
        if point.within(ocean["geometry"]):
            return ocean["name"]
    return None


class Dashboard(param.Parameterized):
    version = param.Selector(objects=VERSIONS)
    parameter = param.Selector(objects=PARAMS)
    plot_type = param.Selector(objects=PLOT_TYPE)
    selected_station = param.Integer(default=0)

    def __init__(self, **params):
        super().__init__(**params)
        self.oceans_ = gp.read_file("assets/world_oceans_final.json")
        self.df = pd.DataFrame()
        self.ocean_mapping = {}
        self.countries = gp.read_file(
            "assets/ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp"
        )
        self.stats = load_stats()
        self.update_data()

    @param.depends("version", watch=True)
    def update_data(self):
        self.df = pd.DataFrame(self.stats[self.version]).T
        self.df = self.df.astype(float)
        self.df["ocean"] = self.df.apply(
            lambda station: find_ocean_for_station(
                station, self.oceans_, "obs_lon", "obs_lat"
            ),
            axis=1,
        )
        # Create a color mapping for oceans
        unique_oceans = self.df["ocean"].unique()
        color_key = hv.Cycle("Category20").values
        self.ocean_mapping = {
            ocean: color_key[i % len(color_key)]
            for i, ocean in enumerate(unique_oceans)
        }
        # Apply the color mapping to the oceans map
        self.map_ = self.oceans_[self.oceans_["name"].isin(unique_oceans)].hvplot(
            color="name",
            alpha=0.9,
            **PLOT_OPTS["ts_view"],
            cmap=self.ocean_mapping,  # Use the color mapping dictionary
            tools=[],
            xlim=(-180, 180),
            ylim=(-90, 90),
            legend=False,
        ) * self.countries.hvplot().opts(color="grey", line_alpha=0.9, tools=[])

        self.df = self.df.dropna()
        self.df["ioc_code"] = self.df.index
        self.df.loc[self.df["nse"] > 0, "nse2"] = self.df["nse"]
        self.df.loc[self.df["nse"] < 0, "nse2"] = 0

    def get_parameter_name(self, dict_):
        key_list = list(dict_.keys())
        val_list = list(dict_.values())
        param_name = key_list[val_list.index(self.parameter)]
        return param_name

    @param.depends("version", "parameter")
    def view(self):
        # Update the DataFrame based on the selected version
        self.update_data()
        scatter_ = scatter_hist(self.df, "obs_lon", "obs_lat", self.parameter)

        # Update the layout with new plots
        layout = pn.Column(self.map_ * scatter_)
        return layout

    @param.depends("version")
    def taylor(self):
        self.update_data()
        diagram = taylor_diagram(pd.DataFrame())
        for ocean in self.ocean_mapping.keys():
            df = self.df[self.df["ocean"] == ocean]
            diagram *= taylor_diagram(
                df, norm=True, color=self.ocean_mapping[ocean], label=ocean
            )
        return diagram.opts(
            **PLOT_OPTS["taylor_view"],
            shared_axes=False,
            legend_opts={"background_fill_alpha": 0.6},
        )

    @param.depends("version")
    def radar(self):
        self.update_data()
        return radar_plot(
            self.df, PARAMS_SPIDER, g="ocean", color_map=self.ocean_mapping
        ).opts(
            **PLOT_OPTS["radar_view"],
            shared_axes=False,
            legend_opts={"background_fill_alpha": 0.5},
        )

    @param.depends("version", "parameter", "plot_type")
    def hist(self):
        # Update the DataFrame based on the selected version
        self.update_data()
        hist = hist_(
            self.df,
            self.parameter,
            self.get_parameter_name(PARAMS),
            g="ocean",
            map=self.ocean_mapping,
            type=self.plot_type,
        )
        return hist.opts(
            shared_axes=False,
            **PLOT_OPTS["hist_view"],
        )


# Instantiate the dashboard and create the layout
dashboard = Dashboard()
layout = pn.Row(
    pn.Column(
        pn.Row(
            dashboard.param.version,
            dashboard.param.parameter,
            dashboard.param.plot_type,
        ),
        dashboard.view,
        dashboard.hist,
    ),
    pn.Column(dashboard.taylor, dashboard.radar),
)
# Serve the Panel app
layout.servable()
