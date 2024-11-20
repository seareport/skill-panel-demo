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
from seastats import get_stats
from seastats.storms import match_extremes

from seareport_skill import DashboardTS
from seareport_skill import load_parquet
from seareport_skill import settings
from utils.plots import scatter_plot
from utils.tools import folders_to_models
from utils.tools import models_to_folders
from utils.tools import value_to_key

# sea stats functions
# Thalassa

logging.basicConfig(level=10)
logger = logging.getLogger()

pn.extension("mathjax")
pn.extension("tabulator")

# GLOBAL VARIABLES
folders = sorted(list(glob.glob(settings.OBS_FOLDER + "/model/*")))
MODELS = folders_to_models(folders, settings.VERSIONS)

if len(MODELS) > 1:
    MODEL1 = MODELS[0]
    MODEL2 = MODELS[1]
    logger.info(f"Comparing {MODEL1} and {MODEL2}")
else:
    raise ValueError("need to have at least 2 models in the folder")

db = DashboardTS(MODEL1)
LIST2 = list(set(MODELS) - set([MODEL1]))

map_view = {
    "width": 900,
    "height": 600,
}
scatter_view = {
    "width": 450,
    "height": 450,
}
hist_hw = 125
sidebar_width = 350


model1 = pn.widgets.Select(
    name="Reference Model",
    # value = MODEL1,
    options={m: settings.VERSIONS[m] for m in MODELS},
    sizing_mode="stretch_width",
)

model2 = pn.widgets.Select(
    name="Second Model",
    # value = MODEL2,
    options={m: settings.VERSIONS[m] for m in LIST2},
    sizing_mode="stretch_width",
)

metrics = pn.widgets.Select(
    name="Metrics", options=settings.METRICS, sizing_mode="stretch_width"
)

station = pn.widgets.CrossSelector(
    name="Stations", options=list(db.STATS.index), width=sidebar_width - 40
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
    pn.state.location.sync(model1, {"value": model1.name})
    pn.state.location.sync(model2, {"value": model2.name})
    pn.state.location.sync(station, {"value": station.name})
    pn.state.location.sync(quantile, {"value": quantile.name})
    pn.state.location.sync(metrics, {"value": metrics.name})
    pn.state.location.sync(start_date, {"value": start_date.name})
    pn.state.location.sync(end_date, {"value": end_date.name})


def update_station_from_map(index):
    if index:
        selected_id = db.STATS.iloc[index].index.values.tolist()
        station.value = selected_id
    else:
        station.value = ""


# Tap Streams
select_stream_map = hv.streams.Selection1D(source=None)
select_stream_map.add_subscriber(update_station_from_map)


def extract_station_codes(file_paths):
    codes = [os.path.splitext(os.path.basename(path))[0] for path in file_paths]
    return codes


@pn.depends(model1, model2, metrics, quantile, start_date, end_date)
def map_plot(
    model1_val, model2_val, metrics_val, quantile_val, start_date_val, end_date_val
) -> pn.pane.HoloViews:
    updated_list = list(set(MODELS) - set([model1_val]))
    model2.options = {m: settings.VERSIONS[m] for m in updated_list}
    stations1 = extract_station_codes(
        glob.glob(settings.OBS_FOLDER + f"/model/{model1_val}/*.parquet")
    )
    stations2 = extract_station_codes(
        glob.glob(settings.OBS_FOLDER + f"/model/{model2_val}/*.parquet")
    )
    obs_set = extract_station_codes(glob.glob(settings.OBS_FOLDER + "/surge/*.parquet"))
    common_stations = (
        set(stations1).intersection(set(stations2)).intersection(set(obs_set))
    )
    stats_df = pd.DataFrame()
    for station in common_stations:
        sim1 = pd.read_parquet(
            settings.OBS_FOLDER + f"/model/{model1_val}/{station}.parquet"
        )
        sim2 = pd.read_parquet(
            settings.OBS_FOLDER + f"/model/{model2_val}/{station}.parquet"
        )
        obs = pd.read_parquet(settings.OBS_FOLDER + f"/surge/{station}.parquet")
        sim1 = sim1[sim1.columns[0]]
        sim2 = sim2[sim2.columns[0]]
        obs = obs[obs.columns[0]]
        obs = obs.loc[start_date_val:end_date_val]
        obs = obs.resample("1h").mean().shift(freq="30min")
        sim1 = sim1.resample("1h").mean().shift(freq="30min")
        sim2 = sim2.resample("1h").mean().shift(freq="30min")
        sim1 = sim1.loc[start_date_val:end_date_val]
        sim2 = sim2.loc[start_date_val:end_date_val]
        metric1 = get_stats(sim1, obs, metrics=[metrics_val], quantile=quantile_val)[
            metrics_val
        ]
        metric2 = get_stats(sim2, obs, metrics=[metrics_val], quantile=quantile_val)[
            metrics_val
        ]
        df = pd.DataFrame(
            {
                f"{model1_val}": metric1,
                f"{model2_val}": metric2,
                "obs_lon": db.STATS.loc[station, "obs_lon"],
                "obs_lat": db.STATS.loc[station, "obs_lat"],
            },
            index=[station],
        )
        stats_df = pd.concat([stats_df, df], axis=0)
    stats_df["compare"] = (
        f"worse than {model1_val}"  # inititalise comparison to "worse"
    )
    if metrics_val in ["rmse", "rms", "R1", "R3", "error"]:
        stats_df.loc[stats_df[model2_val] < stats_df[model1_val], "compare"] = (
            f"better than {model1_val}"
        )
    elif metrics_val in ["cr", "kge", "nse"]:
        stats_df.loc[stats_df[model2_val] > stats_df[model1_val], "compare"] = (
            f"better than {model1_val}"
        )
    elif metrics_val in ["bias"]:
        stats_df.loc[
            abs(stats_df[model2_val]) < abs(stats_df[model1_val]), "compare"
        ] = f"better than {model1_val}"
    stats_df = stats_df.sort_values(by=["compare"])
    stats_df["id"] = stats_df.index
    db.STATS = stats_df
    db.VERSION = model1_val
    stats_df["size"] = 8
    # stats_df.loc[stats_df.index.isin(station_val), "size"] = 13

    p = scatter_plot(
        stats_df,
        "obs_lon",
        "obs_lat",
        colorbar=True,
        geo=True,
    ).opts(
        color="compare",
        line_color="k",
        line_width=1,
        size="size",
        cmap="kbc_r",
        tools=["box_select, lasso_select", "hover"],
        show_legend=True,
    )
    select_stream_map.source = p

    map_ = db.COUNTRIES.hvplot(geo=True).opts(
        color="grey", line_alpha=0.9, default_tools=[]
    )
    map_ = (map_ * p).opts(
        **map_view, ylim=(-50, 60), toolbar="above", legend_position="bottom_right"
    )

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


def size_transform(x):
    return 12 if x >= 1 else 12 * x


@pn.depends(model1, model2, station.param.value, quantile, start_date, end_date)
def time_series_plots(
    model1_val, model2_val, station_val, quantile_val, start_date_val, end_date_val
):
    db.COUNT = 0
    if not station_val:
        xhist, yhist = (hv.Distribution(hv.Points((0, 0)), kdims=[dim]) for dim in "xy")
        compo_empty = (
            hv.Points((0, 0)).opts(**scatter_view)
            << yhist.opts(width=hist_hw)
            << xhist.opts(height=hist_hw)
        )
        return pn.pane.HoloViews(compo_empty)
    else:
        models = [
            value_to_key(model1_val, settings.VERSIONS),
            value_to_key(model2_val, settings.VERSIONS),
        ]
        folders = models_to_folders(models, settings.VERSIONS)
        for im, model_version_folder in enumerate(folders):
            model_ = [model1_val, model2_val][im]
            ext_df_all = pd.DataFrame()
            for station in station_val:
                obs = load_parquet(settings.OBS_FOLDER + "/surge", station).dropna()
                obs = obs[obs.columns[0]]
                obs = obs.resample("1h").mean().shift(freq="30min")
                obs = obs.loc[start_date_val:end_date_val]
                window = db.CLUSTER_H // 2  # Assuming cluster_duration is in hours
                sim = load_parquet(model_version_folder, station)
                if model_ == "Stofs 2D":
                    sim = sim - sim.mean()
                sim = sim[sim.columns[0]]
                sim = sim.loc[start_date_val:end_date_val]
                ext_df = match_extremes(sim, obs, quantile_val, cluster=db.CLUSTER_H)
                sizes = ext_df["observed"].apply(size_transform)
                ext_df = ext_df[["tdiff", "diff"]]
                ext_df.columns = db.KDIMS
                ext_df["id"] = station
                ext_df["sizes"] = sizes
                ext_df_all = pd.concat([ext_df_all, ext_df], axis=0)
                lag_range = (-window, window)
                error_range = (-1.2, 1.2)

            scat_ = hv.Points(ext_df_all, kdims=db.KDIMS, label=model_).opts(
                color=cc.glasbey[im],
                size="sizes",
                line_color="black",
                tools=["hover", "box_select", "tap"],
            )
            x_kde_ = hv.Distribution(ext_df_all[db.KDIMS[0]]).opts(
                color=cc.glasbey[im], axiswise=True
            )
            y_kde_ = hv.Distribution(ext_df_all[db.KDIMS[1]]).opts(
                color=cc.glasbey[im], axiswise=True
            )

            # assign or overlay the plots
            if im == 0:
                scatter_ext = scat_
                lag_dist = x_kde_
                error_dist = y_kde_
            else:
                scatter_ext *= scat_
                lag_dist *= x_kde_
                error_dist *= y_kde_

            lag_dist = lag_dist.redim.range(**{db.KDIMS[0]: lag_range}).opts(xlabel="")
            error_dist = error_dist.redim.range(**{db.KDIMS[1]: error_range}).opts(
                xlabel=""
            )

        # scatter + KDE plot
        composition = (
            (scatter_ext.opts(**scatter_view))
            << error_dist.opts(width=125)
            << lag_dist.opts(height=125)
        )
        composition.opts(
            opts.Distribution(alpha=0.5),
            opts.Points(xlim=lag_range, ylim=error_range, show_legend=True),
        )
        sc_pane = pn.pane.HoloViews(composition, width_policy="max")

        return sc_pane


# Create a Column to hold the dynamic output of time_series_plots
storms_plot = pn.Row()


# Define a function to update the contents of the Column based on time_series_plots
def update_time_series_column(event=None):
    sc_pane = time_series_plots(
        model1.value,
        model2.value,
        station.value,
        quantile.value,
        start_date.value,
        end_date.value,
    )
    # Clear the existing contents and update with new panes
    storms_plot.clear()
    storms_plot.extend([sc_pane])


# Initially populate the Column
update_time_series_column()


# Watch for changes in the widgets and update the Column accordingly
def add_widget_watchers(widgets: list, callback: callable) -> None:
    for widget in widgets:
        widget.param.watch(callback, "value")


add_widget_watchers(
    [model1, model2, station, quantile, start_date, end_date], update_time_series_column
)

template = pn.template.BootstrapTemplate(
    title="Model comparison",
    sidebar=[model1, model2, metrics, station, quantile, start_date, end_date],
    sidebar_width=sidebar_width,
    main=pn.Column(
        pn.Row(map_plot, storms_plot),
    ),
)

template.modal.append(settings.CONTENT)
modal_btn = pn.widgets.Button(name="More information about the metrics")


def about_callback(event):
    template.open_modal()


modal_btn.on_click(about_callback)
template.sidebar.append(modal_btn)

template.servable()
