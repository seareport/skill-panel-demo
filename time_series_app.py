from __future__ import annotations

import glob
import logging
import os

import colorcet as cc
import holoviews as hv
import hvplot.pandas  # noqa: F401
import pandas as pd
import panel as pn
import thalassa
from pyextremes import get_extremes
from seastats import get_stats
from seastats.stats import align_ts
from seastats.storms import match_extremes

from seareport_skill import DashboardTS
from seareport_skill import load_mesh
from seareport_skill import settings
from utils.plots import plot_extreme_raster
from utils.plots import scatter_plot
from utils.plots import scatter_plot_raster
from utils.tools import folders_to_models
from utils.tools import models_to_folders

logging.basicConfig(level=10)
logger = logging.getLogger()

pn.extension("mathjax")
pn.extension("tabulator")


folders = sorted(list(glob.glob(settings.OBS_FOLDER + "/model/*")))
MODELS = folders_to_models(folders, settings.VERSIONS)

if len(MODELS) > 0:
    DEFAULT_VAL = MODELS[0]
else:
    DEFAULT_VAL = []

db = DashboardTS(DEFAULT_VAL)

version = pn.widgets.Select(
    name="Model",
    options={m: settings.VERSIONS[m] for m in MODELS},
    sizing_mode="stretch_width",
)

v_plot = pn.widgets.CheckBoxGroup(
    name="Models",
    value=[DEFAULT_VAL],
    options=MODELS,
    sizing_mode="stretch_width",
)

metrics = pn.widgets.Select(
    name="Metrics", options=settings.METRICS, sizing_mode="stretch_width"
)

quantile = pn.widgets.FloatInput(
    name="Quantile", value=0.95, step=1e-3, start=0, end=1, sizing_mode="stretch_width"
)

station = pn.widgets.AutocompleteInput(
    name="Station", options=list(db.STATS.index), sizing_mode="stretch_width"
)

show_colors = pn.widgets.Checkbox(
    name="Show_colors", value=False, sizing_mode="stretch_width"
)
show_bathy = pn.widgets.Checkbox(
    name="Show Bathymetry", value=False, sizing_mode="stretch_width"
)

start_date = pn.widgets.DatePicker(
    name="Start Date",
    value=pd.Timestamp(2022, 1, 1),  # Default to today, adjust as needed
    sizing_mode="stretch_width",
)

end_date = pn.widgets.DatePicker(
    name="End Date", value=pd.Timestamp(2024, 1, 1), sizing_mode="stretch_width"
)

map_view = {
    "width": 700,
    "height": 500,
}
ts_view = {
    "width": 1300,
    "height": 400,
}
scatter_view = {
    "width": 500,
    "height": 500,
}

sidebar_width = 300

# UPDATE URL
if pn.state.location:
    pn.state.location.sync(version, {"value": version.name})
    pn.state.location.sync(v_plot, {"value": v_plot.name})
    pn.state.location.sync(metrics, {"value": metrics.name})
    pn.state.location.sync(station, {"value": station.name})
    pn.state.location.sync(quantile, {"value": quantile.name})
    pn.state.location.sync(show_colors, {"value": show_colors.name})
    pn.state.location.sync(start_date, {"value": start_date.name})
    pn.state.location.sync(end_date, {"value": end_date.name})


def load_parquet(folder, id):
    return pd.read_parquet(f"{folder}/{id}.parquet")


def update_station_from_map(index):
    if index:
        selected_id = db.STATS.iloc[index].index[0]
        station.value = selected_id
    else:
        station.value = ""


# Define a tap stream and link it to the scatter plot
tap_stream = hv.streams.Selection1D(source=None)
tap_stream.add_subscriber(update_station_from_map)


@pn.depends(version, metrics, show_bathy)
def map_plot(version_val, metrics_val, show_bathy_val) -> pn.pane.HoloViews:
    if version_val != db.VERSION:
        db.VERSION = version_val
        mesh = load_mesh(version_val)
        if isinstance(version_val, list):
            version = os.path.basename(version_val[0])
        else:
            version = version_val
        db.update_stats(version)
        # plot mesh
        if show_bathy_val:
            mesh_ = thalassa.plot(
                mesh.isel(time=-1),
                "B",
                show_mesh=True,
                cmap="kbc",
            )
        else:
            mesh_ = thalassa.plot_mesh(
                mesh,
            )
        db.MESH_ = mesh_

    p = scatter_plot(
        db.STATS[["obs_lon", "obs_lat", metrics_val, "id"]],
        "obs_lon",
        "obs_lat",
        colorbar=True,
        geo=True,
    ).opts(
        size=20,
        color=metrics_val,
        line_color="k",
        line_width=1,
        cmap="rainbow4",
        tools=["tap", "hover"],  # Enable tap tool
    )
    tap_stream.source = p

    map_plot = (db.MESH_ * p).opts(
        **map_view,
    )
    return pn.pane.HoloViews(
        map_plot,
        width_policy="max",
    )


@pn.depends(version)
def specs_mesh(version_val):
    mesh = load_mesh(version_val)
    return pn.pane.Markdown(
        f"""
### MESH SPECS
 * nodes: {len(mesh.lon)}
 * elements: {len(mesh.triface_nodes)}
---"""
    )


@pn.depends(v_plot, station.param.value, quantile, show_colors, start_date, end_date)
def update_panels(
    version_plot_val,
    station_val,
    quantile_val,
    show_colors_val,
    start_date_val,
    end_date_val,
):
    if not station_val:
        emp_ = pd.DataFrame()
        empty_ts = plot_extreme_raster(emp_, emp_).opts(**ts_view)
        empty_scatter = scatter_plot_raster(emp_, emp_, 0).opts(**scatter_view)
        ts_pane_empty = pn.pane.HoloViews(empty_ts, width_policy="max")
        sc_pane_empty = pn.pane.HoloViews(empty_scatter)
        df_pane_empty = pn.pane.DataFrame(emp_, width_policy="max")
        return ts_pane_empty, sc_pane_empty, df_pane_empty
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
        obs_plot = plot_extreme_raster(obs, ext, color="lightgray")
        obs1h = obs.resample("1h").mean().shift(freq="30min")
        # resample to 1h time series
        ext1h = get_extremes(
            obs1h, "POT", threshold=obs.quantile(quantile_val), r=f"{db.CLUSTER_H}h"
        )
        obs_plot *= plot_extreme_raster(obs1h, ext1h, color="grey", label="observed")

        folders = models_to_folders(version_plot_val, settings.VERSIONS)
        df_stats = pd.DataFrame()
        for im, model_version_folder in enumerate(folders):
            model_ = version_plot_val[im]
            sim = load_parquet(model_version_folder, station_val)
            if model_ == "Stofs 2D":
                sim = sim - sim.mean()
            sim = sim[sim.columns[0]]
            sim = sim.loc[start_date_val:end_date_val]
            ext_df = match_extremes(sim, obs, quantile_val, cluster=72)
            # subset if event selected
            sim_, obs_ = align_ts(sim, obs)
            stats = get_stats(sim_, obs_)
            stats["R1"] = ext_df["error"].iloc[0]
            stats["R3"] = ext_df["error"].iloc[0:3].mean()
            stats["error"] = ext_df["error"].mean()
            stats_ = pd.DataFrame(stats, index=[model_])
            df_stats = pd.concat([df_stats, stats_], axis=0)

            ext_temp = pd.DataFrame(
                {model_: ext_df["model"].values}, index=ext_df["time model"]
            )
            temp_plot = plot_extreme_raster(
                sim, ext_temp, color=cc.glasbey[im], label=model_
            )

            # 2 - Scatter plot + LIVE STATS
            temp = scatter_plot_raster(
                obs_,
                sim_,
                quantile=quantile_val,
                cluster_duration=72,
                color=cc.glasbey[im],
                label=model_,
            )

            if im == 0:
                mod_plot = temp_plot
                scat_plot = temp
            else:
                mod_plot *= temp_plot
                scat_plot *= temp
        # options for plots
        ts_plot = (mod_plot * obs_plot).opts(
            title=station_val,
            tools=["hover"],
            toolbar="above",
            legend_position="bottom_right",
            **ts_view,
        )
        scat_plot = scat_plot.opts(
            toolbar="above",
            tools=["hover"],
            legend_position="bottom_right",
            **scatter_view,
        )

        ts_pane = pn.pane.HoloViews(ts_plot, width_policy="max")
        sc_pane = pn.pane.HoloViews(scat_plot, width_policy="max")
        if show_colors_val:
            df_pane = pn.widgets.Tabulator(
                df_stats,
                sizing_mode="stretch_width",
                stylesheets=[settings.TABULATOR_CSS],
                formatters=settings.TABULATOR_FORMATTER,
                configuration=settings.TABULATOR_CONFIG,
                layout="fit_data_table",
            )
        else:
            df_pane = pn.widgets.Tabulator(
                df_stats,
                sizing_mode="stretch_width",
                stylesheets=[settings.TABULATOR_CSS],
            )
        return ts_pane, sc_pane, df_pane


# Create a Column to hold the dynamic output of update_panels
time_series_column = pn.Column()
scat_column = pn.Column()
df_column = pn.Column()


def update_all(event=None):
    ts_pane, sc_pane, df_pane = update_panels(
        v_plot.value,
        station.value,
        quantile.value,
        show_colors.value,
        start_date.value,
        end_date.value,
    )
    # Clear the existing contents and update with new panes
    time_series_column.clear()
    time_series_column.extend([ts_pane])
    scat_column.clear()
    scat_column.extend([sc_pane])
    df_column.clear()
    df_column.extend([df_pane])


# Watch for changes in the widgets and update the Column accordingly
update_all()
# version.param.watch(update_stats, "value")
v_plot.param.watch(update_all, "value")
station.param.watch(update_all, "value")
quantile.param.watch(update_all, "value")
show_colors.param.watch(update_all, "value")

template = pn.template.BootstrapTemplate(
    title="Time Series Analysis",
    sidebar=[
        version,
        show_bathy,
        specs_mesh,
        v_plot,
        metrics,
        station,
        quantile,
        show_colors,
        start_date,
        end_date,
    ],
    sidebar_width=sidebar_width,
    main=pn.Column(
        df_column,
        pn.Row(map_plot, scat_column),
        time_series_column,
    ),
)

template.modal.append(settings.CONTENT)
modal_btn = pn.widgets.Button(name="More information about the metrics")


def about_callback(event):
    template.open_modal()


modal_btn.on_click(about_callback)
template.sidebar.append(modal_btn)

template.servable()
