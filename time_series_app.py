from __future__ import annotations

import glob
import logging

import colorcet as cc
import holoviews as hv
import hvplot.pandas  # noqa: F401
import pandas as pd
import panel as pn
from holoviews import opts
from holoviews.operation.datashader import rasterize
from holoviews.operation.datashader import spread
from pyextremes import get_extremes
from seastats.stats import align_ts
from seastats.stats import get_percentiles
from seastats.stats import get_slope_intercept
from seastats.stats import get_stats
from seastats.storms import get_extremes_ts
from seastats.storms import match_extremes

from seareport_skill import load_countries
from seareport_skill import load_model_stats
from seareport_skill import settings
from utils.hists import scatter_plot

# sea stats functions
#

logging.basicConfig(level=10)
logger = logging.getLogger()

pn.extension("mathjax")


OBS_FOLDER = "./01_obs"
MODELS = list(glob.glob(OBS_FOLDER + "/model/*"))
CMAP_ = cc.colorwheel

statsv0 = load_model_stats("v0.0")

version = pn.widgets.Select(
    name="Model Version for map", options=settings.VERSIONS, sizing_mode="stretch_width"
)

version_plot = pn.widgets.CheckBoxGroup(
    name="Models Versions for Time Series",
    value=[MODELS[0]],
    options=MODELS,
    sizing_mode="stretch_width",
)

metrics = pn.widgets.Select(
    name="Metrics", options=settings.METRICS, sizing_mode="stretch_width"
)

quantile = pn.widgets.FloatInput(
    name="Quantile", value=0.9, step=1e-3, start=0, end=1, sizing_mode="stretch_width"
)

station = pn.widgets.AutocompleteInput(
    name="Station", options=list(statsv0.index), sizing_mode="stretch_width"
)

map_view = {
    "width": 1300,
    "height": 500,
}
ts_view = {
    "width": 700,
    "height": 400,
}
scatter_view = {
    "width": 400,
    "height": 400,
}

if pn.state.location:
    pn.state.location.sync(version, {"value": version.name})
    pn.state.location.sync(metrics, {"value": metrics.name})
    pn.state.location.sync(station, {"value": station.name})
    pn.state.location.sync(quantile, {"value": quantile.name})


def load_parquet(folder, id):
    return pd.read_parquet(f"{folder}/{id}.parquet")


def update_station_from_map(index):
    if index:
        selected_id = statsv0.iloc[index].index[0]
        station.value = selected_id
    else:
        station.value = ""


# PLOTTING FUNCTIONS
def plot_extreme_raster(
    ts: pd.Series, quantile: float, duration_cluster: int = 72, color="black", label=""
):
    """
    this function might induce overhead if the time series is too long
    """
    if ts.empty:
        ts_ = rasterize(hv.Curve((0, 0), label=label))
        sc_ = hv.Scatter((0, 0), label=label)
        th_ = hv.HLine(0)
        th_text_ = hv.Text(0, 0, "")
    else:
        ext = get_extremes(
            ts, "POT", threshold=ts.quantile(quantile), r=f"{duration_cluster}h"
        )
        ts_ = rasterize(hv.Curve(ts, label=label), line_width=0.5).opts(
            cmap=[color], **ts_view, show_grid=True, alpha=0.7
        )
        sc_ = hv.Scatter(ext, label=label).opts(
            opts.Scatter(line_color="black", fill_color=color, size=8)
        )
        th_ = hv.HLine(ts.quantile(quantile)).opts(
            opts.HLine(color=color, line_dash="dashed")
        )
        th_text_ = hv.Text(
            ts.index[int(len(ts) / 2)],
            ts.quantile(quantile),
            f"{ts.quantile(quantile):.2f}",
        )
    return ts_ * sc_ * th_ * th_text_


def scatter_plot_raster(
    ts1: pd.Series,
    ts2: pd.Series,
    quantile: float,
    cluster_duration: int = 72,
    pp_plot: bool = False,
    color="black",
    label="",
):
    if ts1.empty or ts2.empty:
        sc_ = spread(rasterize(hv.Points((0, 0))))
        extremes_match = pd.DataFrame()
        slope, intercept = (0, 0)
    else:
        extremes = get_extremes_ts(ts1, ts2, quantile, cluster_duration)
        extremes_match = match_extremes(extremes)
        p = hv.Points((ts1.values, ts2.values))
        sc_ = spread(rasterize(p)).opts(
            cmap=[color], cnorm="linear", alpha=0.9, **scatter_view
        )
        slope, intercept = get_slope_intercept(ts1, ts2)
    if extremes_match.empty:
        ext_ = hv.Points((0, 0))
    else:
        ext_ = hv.Points(
            (extremes_match["modeled"].values, extremes_match["observed"]), label=label
        ).opts(size=8, fill_color=color, line_color="k")
    ax_plot = hv.Slope(1, 0).opts(color=color, show_grid=True)

    lr_plot = hv.Slope(
        slope, intercept, label=f"y = {slope:.2f}x + {intercept:.2f}"
    ).opts(color=color, line_dash="dashed")
    #
    if pp_plot:
        pc1, pc2 = get_percentiles(ts1, ts2, higher_tail=True)
        ppp = hv.Scatter((pc1, pc2), ("modeled", "observed"), label="percentiles").opts(
            fill_color="g", line_color="b", size=10
        )
        return ax_plot * lr_plot * sc_ * ext_ * ppp
    else:
        return ax_plot * lr_plot * sc_ * ext_


# Define a tap stream and link it to the scatter plot later
tap_stream = hv.streams.Selection1D(source=None)

# Watch for selection events on the scatter plot and update the station widget accordingly
tap_stream.add_subscriber(update_station_from_map)


@pn.depends(version, metrics)
def map_plot(version_val, metrics_val) -> pn.pane.HoloViews:
    countries = load_countries()
    stats = load_model_stats(version_val)
    p = scatter_plot(stats, "obs_lon", "obs_lat", colorbar=True).opts(
        size=10,
        color=metrics_val,
        line_color="k",
        line_width=1,
        cmap="rainbow4",
        tools=["tap"],  # Enable tap tool
    )
    tap_stream.source = p

    map_ = countries.hvplot().opts(color="white", line_alpha=0.9)
    map_plot = (map_ * p).opts(
        **map_view,
        xlim=(-180, 180),
        ylim=(-90, 90),
    )
    return pn.pane.HoloViews(
        map_plot,
        width_policy="max",
    )


@pn.depends(version_plot, station.param.value, quantile)
def time_series_plots(version_plot_val, station_val, quantile_val):
    if not station_val:
        emp_ = pd.DataFrame()
        empty_ts = plot_extreme_raster(emp_, 0).opts(**ts_view)
        empty_scatter = scatter_plot_raster(emp_, emp_, 0).opts(**scatter_view)
        ts_pane_empty = pn.pane.HoloViews(empty_ts + empty_scatter, width_policy="max")
        df_pane_empty = pn.pane.DataFrame(emp_, width_policy="max")
        return ts_pane_empty, df_pane_empty
    else:
        # 0 - store dict of dataframes for each model version
        df_dict = {}
        for im, model_version in enumerate(version_plot_val):
            df_dict[model_version] = load_parquet(model_version, station_val)
        obs = load_parquet(OBS_FOLDER + "/surge", station_val).dropna()

        # 1 - plot time series plots
        for im, model_ in enumerate(df_dict.keys()):
            df = df_dict[model_]
            temp = plot_extreme_raster(
                df[df.columns[0]], quantile_val, color=cc.glasbey[im], label=model_
            )
            if im == 0:
                mod_plot = temp
            else:
                mod_plot *= temp
        # add the obs TS
        obs_plot = plot_extreme_raster(
            obs[obs.columns[0]], quantile_val, color="grey", label="observed"
        )
        #
        ts = (mod_plot * obs_plot).opts(
            title=station_val,
            tools=["hover"],
        )

        # 2 - Scatter plot + LIVE STATS
        df_stats = pd.DataFrame()
        for im, model_ in enumerate(df_dict.keys()):
            df = df_dict[model_]
            sim_, obs_ = align_ts(df[df.columns[0]], obs[obs.columns[0]])
            temp = scatter_plot_raster(
                sim_,
                obs_,
                quantile=quantile_val,
                cluster_duration=72,
                color=cc.glasbey[im],
                label=model_,
            )
            if im == 0:
                scat = temp
            else:
                scat *= temp
            stats = pd.DataFrame(get_stats(sim_, obs_), index=[model_])
            df_stats = pd.concat([df_stats, stats], axis=0)

        ts_pane = pn.pane.HoloViews(ts + scat, width_policy="max")
        df_pane = pn.pane.DataFrame(df_stats, sizing_mode="stretch_width")
        return ts_pane, df_pane


# Create a Column to hold the dynamic output of time_series_plots
time_series_column = pn.Column()


# Define a function to update the contents of the Column based on time_series_plots
def update_time_series_column(event=None):
    ts_pane, df_pane = time_series_plots(
        version_plot.value, station.value, quantile.value
    )
    # Clear the existing contents and update with new panes
    time_series_column.clear()
    time_series_column.extend([ts_pane, df_pane])


# Initially populate the Column
update_time_series_column()
# Watch for changes in the widgets and update the Column accordingly
version_plot.param.watch(update_time_series_column, "value")
station.param.watch(update_time_series_column, "value")
quantile.param.watch(update_time_series_column, "value")

template = pn.template.MaterialTemplate(
    title="Time Series Analysis",
    sidebar=[
        version,
        version_plot,
        metrics,
        station,
        quantile,
        pn.pane.Markdown(settings.METRICS_DOC),
    ],
    sidebar_width=430,
    main=pn.Column(
        map_plot,
        time_series_column,
    ),
)

template.servable()
