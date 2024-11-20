from __future__ import annotations

import glob
import logging
import os

import colorcet as cc
import holoviews as hv
import hvplot.pandas  # noqa: F401
import numpy as np
import pandas as pd
import panel as pn
from holoviews import opts
from pyextremes import get_extremes
from seastats import get_stats
from seastats.stats import align_ts
from seastats.storms import match_extremes

from seareport_skill import DashboardTS
from seareport_skill import load_model_stats
from seareport_skill import load_parquet
from seareport_skill import settings
from utils.plots import plot_extreme_raster
from utils.plots import scatter_plot
from utils.tools import folders_to_models
from utils.tools import models_to_folders

# sea stats functions
# Thalassa

logging.basicConfig(level=10)
logger = logging.getLogger()

pn.extension("mathjax")
pn.extension("tabulator")

# GLOBAL VARIABLES
folders = sorted(list(glob.glob(settings.OBS_FOLDER + "/model/*")))
MODELS = folders_to_models(folders, settings.VERSIONS)

if len(MODELS) > 0:
    DEFAULT_VAL = MODELS[0]
else:
    DEFAULT_VAL = []

db = DashboardTS(DEFAULT_VAL)

map_view = {
    "width": 900,
    "height": 500,
}
ts_view = {
    "width": 1050,
    "height": 500,
}
scatter_view = {
    "width": 350,
    "height": 350,
}

hist_hw = 125

table_view = {
    "width": 600,
    "height": 300,
}

desc_view = {
    "width": 600,
    "height": 200,
}

sidebar_width = 350


version = pn.widgets.Select(
    name="Model",
    options={m: settings.VERSIONS[m] for m in MODELS},
    sizing_mode="stretch_width",
)

v_plot = pn.widgets.CrossSelector(
    name="Models",
    value=[DEFAULT_VAL],
    options=MODELS,
    width=sidebar_width,
)

station = pn.widgets.AutocompleteInput(
    name="Station", options=list(db.STATS.index), sizing_mode="stretch_width"
)

show_colors = pn.widgets.Checkbox(
    name="Show_colors", value=False, sizing_mode="stretch_width"
)

quantile = pn.widgets.FloatInput(
    name="Quantile", value=0.95, step=1e-3, start=0, end=1, sizing_mode="stretch_width"
)

start_date = pn.widgets.DatePicker(
    name="Start Date",
    value=pd.Timestamp(2022, 1, 1),  # Default to today, adjust as needed
    sizing_mode="stretch_width",
)

end_date = pn.widgets.DatePicker(
    name="End Date", value=pd.Timestamp(2024, 1, 1), sizing_mode="stretch_width"
)

# UPDATE URL
if pn.state.location:
    pn.state.location.sync(version, {"value": version.name})
    pn.state.location.sync(v_plot, {"value": v_plot.name})
    pn.state.location.sync(station, {"value": station.name})
    pn.state.location.sync(quantile, {"value": quantile.name})
    pn.state.location.sync(show_colors, {"value": show_colors.name})
    pn.state.location.sync(start_date, {"value": start_date.name})
    pn.state.location.sync(end_date, {"value": end_date.name})


def update_station_from_map(index):
    if index:
        selected_id = db.STATS.iloc[index].index[0]
        station.value = selected_id
    else:
        station.value = ""


def event_TS_from_event(index):
    if index:
        if db.EVENT != db.EXTREMES.index[index[0]]:
            db.EVENT = db.EXTREMES.index[index[0]]
            update_time_series_column(event_time=db.EVENT)
        else:
            db.EVENT = None
            update_time_series_column()
    else:
        db.EVENT = None  # Deselect the event
        update_time_series_column()


def event_table_callback(event=None):
    if db.EXTREMES is not None:
        if db.EVENT != db.EXTREMES.index[event.row]:
            db.EVENT = db.EXTREMES.index[event.row]
            update_time_series_column(event_time=db.EVENT)
        else:
            db.EVENT = None
            update_time_series_column()
    else:
        db.EVENT = None  # Deselect the event
        update_time_series_column()


# Tap Streams
tap_stream_map = hv.streams.Selection1D(source=None)
tap_stream_map.add_subscriber(update_station_from_map)
tap_stream_event = hv.streams.Selection1D(source=None)
tap_stream_event.add_subscriber(event_TS_from_event)


@pn.depends(version)
def map_plot(version_val) -> pn.pane.HoloViews:
    if version_val != db.VERSION:
        db.VERSION = version_val
        if isinstance(version_val, list):
            version = os.path.basename(version_val[0])
        else:
            version = version_val
        db.update_stats(version)

    p = scatter_plot(
        db.STATS[["obs_lon", "obs_lat", "id"]],
        "obs_lon",
        "obs_lat",
        colorbar=True,
        geo=True,
    ).opts(
        size=15,
        color="lightgrey",
        line_color="k",
        line_width=1,
        cmap="rainbow4",
        tools=["tap", "hover"],  # Enable tap tool
    )
    tap_stream_map.source = p

    map_ = db.COUNTRIES.hvplot(geo=True).opts(
        color="grey", line_alpha=0.9, default_tools=[]
    )
    map_ = (map_ * p).opts(**map_view, ylim=(-50, 60), toolbar="above")

    return pn.pane.HoloViews(
        map_,
        width_policy="max",
    )


def apply_glasbey_colors(s):
    """
    apply glasbey colors to the rows of the df table
    """
    is_max = np.zeros(len(s), dtype=bool)
    if s.name == "observed":
        color = "grey"
    else:
        color = cc.glasbey[db.COUNT]
        db.COUNT += 1
    return [f"background-color: {color}" if not v else "" for v in is_max]


def subset_signal(df, itime=None):
    half_win = pd.Timedelta(hours=db.CLUSTER_H)
    if itime:
        return df.loc[itime - half_win : itime + half_win]
    else:
        return df


@pn.depends(quantile, station.param.value)
def threshold_value(quantile_val, station_val):
    if quantile_val and station_val:
        obs = load_parquet(settings.OBS_FOLDER + "/surge", station_val).dropna()
        obs = obs[obs.columns[0]]
        threshold = np.round(obs.quantile(quantile_val), 3)
        return pn.pane.Markdown(f"Corresponding physical threshold: {threshold}m MSL")
    else:
        return pn.pane.Markdown("Corresponding physical threshold: N/A")


@pn.depends(v_plot, station.param.value, quantile, show_colors, start_date, end_date)
def time_series_plots(
    version_plot_val,
    station_val,
    quantile_val,
    show_colors_val,
    start_date_val,
    end_date_val,
    event_time=None,
):
    db.COUNT = 0
    if not station_val:
        emp_ = pd.DataFrame()
        empty_ts = plot_extreme_raster(emp_, emp_).opts(**ts_view)
        ts_pane_empty = pn.pane.HoloViews(empty_ts, width_policy="max")
        df_pane_empty = pn.widgets.Tabulator(emp_)
        xhist, yhist = (hv.Distribution(hv.Points((0, 0)), kdims=[dim]) for dim in "xy")
        compo_empty = (
            hv.Points((0, 0)).opts(**scatter_view)
            << yhist.opts(width=hist_hw)
            << xhist.opts(height=hist_hw)
        )
        stats_pane_empty = pn.pane.DataFrame(emp_, width_policy="max")
        return (
            ts_pane_empty,
            df_pane_empty,
            df_pane_empty,
            pn.pane.HoloViews(compo_empty),
            stats_pane_empty,
        )
    else:
        ## get observations
        obs = load_parquet(settings.OBS_FOLDER + "/surge", station_val).dropna()
        obs = obs[obs.columns[0]]
        obs = obs.loc[start_date_val:end_date_val]
        # get observed extremes
        ext = get_extremes(
            obs, "POT", threshold=obs.quantile(quantile_val), r=f"{db.CLUSTER_H}h"
        )
        # subset if event selected
        snippet_obs = subset_signal(obs, event_time)
        obs_plot = plot_extreme_raster(snippet_obs, ext, color="lightgray")
        snippet_obs = snippet_obs.resample("1h").mean().shift(freq="30min")
        # resample to 1h time series
        obs = obs.resample("1h").mean().shift(freq="30min")
        ext = get_extremes(
            obs, "POT", threshold=obs.quantile(quantile_val), r=f"{db.CLUSTER_H}h"
        )
        obs_plot *= plot_extreme_raster(
            snippet_obs, ext, color="grey", label="observed"
        )

        folders = models_to_folders(version_plot_val, settings.VERSIONS)
        df_stats = pd.DataFrame()
        ext_df_all = pd.DataFrame()
        window = db.CLUSTER_H // 2  # Assuming cluster_duration is in hours
        for im, model_version_folder in enumerate(folders):
            model_ = version_plot_val[im]
            sim = load_parquet(model_version_folder, station_val)
            if model_ == "Stofs 2D":
                sim = sim - sim.mean()
            sim = sim[sim.columns[0]]
            sim = sim.loc[start_date_val:end_date_val]
            ext_df = match_extremes(sim, obs, quantile_val, cluster=72)
            # subset if event selected
            sim = subset_signal(sim, event_time)
            sim_, obs_ = align_ts(sim, obs)
            stats = get_stats(sim_, obs_)
            stats["R1"] = ext_df["error"].iloc[0]
            stats["R3"] = ext_df["error"].iloc[0:3].mean()
            stats["error"] = ext_df["error"].mean()
            stats_ = pd.DataFrame(stats, index=[model_])
            df_stats = pd.concat([df_stats, stats_], axis=0)

            # prepare time series plots
            ext_temp = pd.DataFrame(
                {model_: ext_df["model"].values}, index=ext_df["time model"]
            )
            temp_plot = plot_extreme_raster(
                sim, ext_temp, color=cc.glasbey[im], label=model_
            )

            # prepare scatter + KDE plot
            df_ext = ext_df[["tdiff", "diff"]]
            df_ext.columns = db.KDIMS
            lag_range = (-window, window)
            error_range = (-1.2, 1.2)
            df_ext.loc[:, "sizes"] = 7
            if db.EVENT is not None and db.EVENT in ext.index:
                ind = np.where(db.EVENT == ext_df.index)[0]
                df_ext["sizes"][ind] = 12
            scat_ = hv.Points(df_ext, kdims=db.KDIMS).opts(
                color=cc.glasbey[im],
                line_color="black",
                size="sizes",
                tools=["hover", "box_select", "tap"],
            )
            x_kde_ = hv.Distribution(df_ext[db.KDIMS[0]]).opts(
                color=cc.glasbey[im], axiswise=True
            )
            y_kde_ = hv.Distribution(df_ext[db.KDIMS[1]]).opts(
                color=cc.glasbey[im], axiswise=True
            )

            # assign or overlay the plots
            if im == 0:
                scatter_ext = scat_
                lag_dist = x_kde_
                error_dist = y_kde_
                mod_plot = temp_plot
            else:
                scatter_ext *= scat_
                lag_dist *= x_kde_
                error_dist *= y_kde_
                mod_plot *= temp_plot

            lag_dist = lag_dist.redim.range(**{db.KDIMS[0]: lag_range}).opts(xlabel="")
            error_dist = error_dist.redim.range(**{db.KDIMS[1]: error_range}).opts(
                xlabel=""
            )
            tap_stream_event.source = scatter_ext

            # concatenate model extremes into one DataFrame
            ext_df = ext_df.rename(
                columns={"model": model_, "time model": f"time {model_}"}
            )
            ext_df = ext_df.drop(columns=["error", "error_norm", "diff", "tdiff"])
            if im > 0:
                ext_df = ext_df.drop(
                    columns=["observed", "time observed"]
                )  # drop duplicates
            ext_df_all = pd.concat([ext_df_all, ext_df], axis=1)

        # scatter + KDE plot
        composition = (
            (scatter_ext.opts(**scatter_view))
            << error_dist.opts(width=125)
            << lag_dist.opts(height=125)
        )
        composition.opts(
            opts.Distribution(alpha=0.5), opts.Points(xlim=lag_range, ylim=error_range)
        )
        sc_pane = pn.pane.HoloViews(composition, width_policy="max")

        # TS plot
        plot_ = (mod_plot * obs_plot).opts(
            title=station_val,
            tools=["hover"],
            toolbar="above",
            **ts_view,
        )
        if event_time is not None:
            plot_ = plot_.opts(
                xlim=(
                    event_time - pd.Timedelta(days=3),
                    event_time + pd.Timedelta(days=3),
                ),
            )
        ts_pane = pn.pane.HoloViews(plot_)

        # extreme events table
        discard_columns = []
        for c in ext_df_all.columns:
            if "time" in c:
                discard_columns.append(c)

        extremes_df_colored = ext_df_all.drop(columns=discard_columns)
        df_pane = pn.widgets.Tabulator(
            extremes_df_colored,
            **table_view,
            sizing_mode="stretch_width",
            stylesheets=[settings.TABULATOR_CSS],
        )
        if db.EVENT is not None and db.EVENT in ext.index:
            ind = np.where(db.EVENT == ext_df_all.index)[0]
            df_pane = pn.widgets.Tabulator(
                df_pane,
                selection=ind.tolist(),
                **table_view,
                sizing_mode="stretch_width",
                stylesheets=[settings.TABULATOR_CSS],
            )
        df_pane.on_click(event_table_callback)
        df_pane.style.apply(apply_glasbey_colors)

        # extreme events table description
        desc_pane = pn.widgets.Tabulator(
            ext_df_all.drop(columns=discard_columns).describe(),
            **desc_view,
            stylesheets=[settings.TABULATOR_CSS],
        )

        # stats tables
        if show_colors_val:
            stats_pane = pn.widgets.Tabulator(
                df_stats,
                sizing_mode="stretch_width",
                stylesheets=[settings.TABULATOR_CSS],
                formatters=settings.TABULATOR_FORMATTER,
                configuration=settings.TABULATOR_CONFIG,
                layout="fit_data_table",
            )
        else:
            stats_pane = pn.widgets.Tabulator(
                df_stats,
                sizing_mode="stretch_width",
                stylesheets=[settings.TABULATOR_CSS],
            )

        return ts_pane, df_pane, desc_pane, sc_pane, stats_pane


# Create a Column to hold the dynamic output of time_series_plots
time_series = pn.Row()
storms_plot = pn.Row()
storms_table = pn.Column()
stats_table = pn.Row()


# Define a function to update the contents of the Column based on time_series_plots
def update_time_series_column(event=None, event_time=None):
    ts_pane, df_pane, desc_pane, sc_pane, stats_pane = time_series_plots(
        v_plot.value,
        station.value,
        quantile.value,
        show_colors.value,
        start_date.value,
        end_date.value,
        event_time=event_time,
    )
    # Clear the existing contents and update with new panes
    time_series.clear()
    time_series.extend([ts_pane])
    storms_table.clear()
    storms_table.extend([df_pane, desc_pane])
    db.EXTREMES = df_pane.value
    storms_plot.clear()
    storms_plot.extend([sc_pane])
    stats_table.clear()
    stats_table.extend([stats_pane])


def update_stats(event=None):
    db.STATS = load_model_stats(version.value)


# Initially populate the Column
update_time_series_column()


# Watch for changes in the widgets and update the Column accordingly
def add_widget_watchers(widgets: list, callback: callable) -> None:
    for widget in widgets:
        widget.param.watch(callback, "value")


add_widget_watchers(
    [v_plot, station, quantile, show_colors, start_date, end_date],
    update_time_series_column,
)
version.param.watch(update_stats, "value")

template = pn.template.BootstrapTemplate(
    title="Extreme event analysis",
    sidebar=[
        version,
        pn.pane.Markdown("Models to compare"),
        v_plot,
        station,
        quantile,
        threshold_value,
        show_colors,
        start_date,
        end_date,
    ],
    sidebar_width=sidebar_width,
    main=pn.Column(
        stats_table,
        pn.Row(map_plot, storms_table),
        pn.Row(time_series, storms_plot),
    ),
)

template.modal.append(settings.CONTENT)
modal_btn = pn.widgets.Button(name="More information about the metrics")


def about_callback(event):
    template.open_modal()


modal_btn.on_click(about_callback)
template.sidebar.append(modal_btn)

template.servable()
