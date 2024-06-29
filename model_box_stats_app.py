from __future__ import annotations

import logging

import colorcet as cc
import geopandas as gp
import holoviews as hv
import hvplot.pandas  # noqa: F401
import panel as pn

from seareport_skill import assign_oceans
from seareport_skill import load_countries
from seareport_skill import load_model_stats
from seareport_skill import settings
from utils.hists import hist_

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
    name="Maritime Sectors", options=settings.SECTORS, width=400
)

if pn.state.location:
    pn.state.location.sync(version, {"value": version.name})
    pn.state.location.sync(metrics, {"value": metrics.name})
    pn.state.location.sync(type_select, {"value": type_select.name})
    pn.state.location.sync(oceans, {"value": oceans.name})
    pn.state.location.sync(sector, {"value": sector.name})


GDF = gp.read_file("assets/world_oceans_final.json")


def update_color_map(df, filter_var):
    # Create a color mapping for oceans or maritime sectors
    unique_oceans = df[filter_var].unique()
    factor = int(len(cc.rainbow) / len(unique_oceans))
    color_key = hv.Cycle(cc.colorwheel).values
    ocean_mapping = {
        ocean: color_key[i * factor % len(cc.rainbow)]
        for i, ocean in enumerate(unique_oceans)
    }
    return ocean_mapping


@pn.depends(version, metrics, type_select, oceans, sector)
def update_dataframe(
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
        g=type_select.value,
        map=cmap,
    ).opts(
        show_grid=True,
        height=height,
        default_tools=["pan"],
        tools=["box_zoom", "reset", "save"],
    )
    return pn.pane.HoloViews(hist, sizing_mode="stretch_width")


@pn.depends(type_select)
def map_plot(type_select_val):
    countries = load_countries()
    cmap = update_color_map(GDF, type_select_val)
    map_ = countries.hvplot().opts(color="white", line_alpha=0.9)
    map_plot = (
        GDF.hvplot(color=type_select_val).opts(
            cmap=cmap,
            width=1500,
            height=700,
            xlim=(-180, 180),
            ylim=(-90, 90),
            # legend_position="bottom_left",
        )
        * map_
    )
    return pn.pane.HoloViews(map_plot, width_policy="max", sizing_mode="stretch_width")


@pn.depends(type_select)
def display_selector(type_select_val):
    if type_select_val == "ocean":
        return oceans
    else:
        return sector


def metrics_doc():
    return pn.pane.Markdown(settings.METRICS_DOC)


template = pn.template.MaterialTemplate(
    title="Regional statistics",
    sidebar=[version, metrics, type_select, display_selector, metrics_doc],
    sidebar_width=430,
    main=pn.Column(
        update_dataframe,
        map_plot,
    ),
)
template.servable()
