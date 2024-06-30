from __future__ import annotations

import logging
import typing as T

import holoviews as hv
import hvplot.pandas  # noqa: F401
import pandas as pd
import panel as pn

from seareport_skill import load_stats
from seareport_skill import settings

logging.basicConfig(level=10)
logger = logging.getLogger()

pn.extension()

versions = pn.widgets.MultiSelect(
    name="Version",
    options=settings.VERSIONS,
    sizing_mode="stretch_width",
    size=6,
)
metrics = pn.widgets.MultiSelect(
    name="Metrics",
    options=settings.METRICS,
    sizing_mode="stretch_width",
    size=15,
)

if pn.state.location:
    pn.state.location.sync(versions, {"value": versions.name})
    pn.state.location.sync(metrics, {"value": metrics.name})


def _get_stats(versions_val: list[str], metrics_val: list[str]) -> pd.DataFrame:
    stats = load_stats()
    stats = stats[stats.version.isin(versions_val)]
    stats = stats[metrics_val + ["version"]]
    stats = T.cast(pd.DataFrame, stats)
    return stats


def _plot_metric(stats: pd.DataFrame, metric: str) -> hv.BoxWhisker:
    plot = stats.hvplot.box(y=metric, by="version")
    plot = plot.opts(
        ylabel="",
        invert_axes=True,
        title=metric,
        show_grid=True,
        tools=["hover"],
        outlier_radius=0.002,
        height=100 + 20 * stats.version.nunique(),
    )
    return plot


def _plot_table(stats: pd.DataFrame, metric: str) -> hv.Table:
    df = (
        stats[[metric, "version"]]
        .groupby("version")
        .describe([0.05, 0.25, 0.5, 0.75, 0.95])
        .round(3)
    )
    df.columns = df.columns.get_level_values(1)
    df = df.reset_index()
    table = df.hvplot.table().opts(height=100 + 20 * stats.version.nunique())
    return table


@pn.depends(versions, metrics)
def show_metrics(versions_val: list[str], metrics_val: list[str]):
    if not versions_val:
        versions_val = list(settings.VERSIONS.values())
    if not metrics_val:
        metrics_val = list(settings.METRICS.values())
    stats = _get_stats(versions_val=versions_val, metrics_val=metrics_val)
    plots = []
    for metric in metrics_val:
        plots.extend(
            [
                _plot_metric(stats=stats, metric=metric),
                _plot_table(stats=stats, metric=metric),
            ]
        )
    return hv.Layout(plots).cols(2)  # .opts(sizing_mode="stretch_width")


template = pn.template.MaterialTemplate(
    title="Metrics Table",
    sidebar=[versions, metrics],
    sidebar_width=430,
    main=[
        show_metrics,
    ],
)
template.servable()
