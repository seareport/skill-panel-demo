from __future__ import annotations

import logging

import colorcet as cc
import geopandas as gp
import holoviews as hv
import hvplot.pandas  # noqa: F401
import pandas as pd
import panel as pn

from seareport_skill import assign_oceans
from seareport_skill import load_countries
from seareport_skill import load_model_stats
from seareport_skill import settings
from utils.hists import hist_
from utils.hists import scatter_plot
from utils.taylor import taylor_diagram

logging.basicConfig(level=10)
logger = logging.getLogger()

pn.extension("mathjax")

version = pn.widgets.Select(
    name="Version", options=settings.VERSIONS, sizing_mode="stretch_width"
)
metrics = pn.widgets.Select(
    name="Metrics", options=settings.METRICS, sizing_mode="stretch_width"
)
type_select = pn.widgets.Select(
    name="Choose Type of Selection",
    options=settings.TYPE_SELECT,
    sizing_mode="stretch_width",
)
oceans = pn.widgets.CrossSelector(name="Oceans", options=settings.OCEANS, width=400)
sector = pn.widgets.CrossSelector(
    name="Maritime Sectors", options=settings.SECTORS, width=400, height=720
)

if pn.state.location:
    pn.state.location.sync(version, {"value": version.name})
    pn.state.location.sync(metrics, {"value": metrics.name})
    pn.state.location.sync(type_select, {"value": type_select.name})
    pn.state.location.sync(oceans, {"value": oceans.name})
    pn.state.location.sync(sector, {"value": sector.name})


GDF = gp.read_file("assets/world_oceans_final.json")
T_VOID = taylor_diagram(pd.DataFrame())
CMAP = cc.CET_C6


def update_color_map(df, filter_var):
    # Create a color mapping for oceans or maritime sectors
    unique_oceans = df[filter_var].unique()
    factor = int(len(CMAP) / len(unique_oceans))
    color_key = hv.Cycle(CMAP).values
    ocean_mapping = {
        ocean: color_key[i * factor % len(CMAP)]
        for i, ocean in enumerate(unique_oceans)
    }
    return ocean_mapping


@pn.depends(version, metrics, type_select, oceans, sector)
def update_plots(
    version_val, metrics_val, type_select_val, oceans_val, sector_val
) -> pn.pane.DataFrame:
    stats = load_model_stats(version_val)
    stats = assign_oceans(stats)
    cmap = update_color_map(GDF, type_select_val)
    if type_select_val == "ocean":
        if oceans_val:
            stats = stats[stats.ocean.isin(oceans_val)]
            height = len(oceans_val) * 30 + 90
        else:
            height = 300
    else:
        if sector_val:
            stats = stats[stats.name.isin(sector_val)]
            height = len(sector_val) * 30 + 90
        else:
            height = 500
    hist = hist_(
        stats,
        metrics_val,
        list(settings.METRICS.keys())[
            list(settings.METRICS.values()).index(metrics_val)
        ],
        g=type_select_val,
        map=cmap,
    ).opts(
        show_grid=True,
        height=height,
        width=800,
        default_tools=["pan"],
        tools=["box_zoom", "reset", "save"],
    )

    taylor = taylor_diagram(
        stats,
        norm=True,
        color=type_select_val,
        cmap=cmap,
    ).opts(
        show_grid=True,
        show_legend=False,
        default_tools=["pan"],
        tools=["hover", "box_zoom", "reset", "save"],
    )
    taylor_ = (T_VOID * taylor).opts(
        width=600,
        height=600,
        title="Taylor Diagram",
    )
    return pn.pane.HoloViews(
        (hist + taylor_).opts(shared_axes=False), sizing_mode="stretch_width"
    )


@pn.depends(type_select, version, oceans, sector)
def map_plot(type_select_val, version_val, oceans_val, sector_val) -> pn.pane.HoloViews:
    countries = load_countries()
    stats = load_model_stats(version_val)
    stats = assign_oceans(stats)
    if type_select_val == "ocean":
        if oceans_val:
            stats = stats[stats.ocean.isin(oceans_val)]
    else:
        if sector_val:
            stats = stats[stats.name.isin(sector_val)]
    points = scatter_plot(stats[["obs_lon", "obs_lat"]], "obs_lon", "obs_lat")
    cmap = update_color_map(GDF, type_select_val)
    map_ = countries.hvplot().opts(color="white", line_alpha=0.9)
    map_plot = (
        GDF.hvplot(color=type_select_val).opts(
            cmap=cmap,
            width=1400,
            height=600,
            xlim=(-180, 180),
            ylim=(-90, 90),
        )
        * map_
        * points
    )
    return pn.pane.HoloViews(
        map_plot,
        width_policy="max",
    )


@pn.depends(type_select)
def display_selector(type_select_val):
    if type_select_val == "ocean":
        return oceans
    else:
        return sector


template = pn.template.MaterialTemplate(
    title="Regional statistics",
    sidebar=[
        version,
        metrics,
        type_select,
        display_selector,
        pn.pane.Markdown(settings.METRICS_DOC),
    ],
    sidebar_width=430,
    main=pn.Column(
        update_plots,
        map_plot,
    ),
)
template.servable()
