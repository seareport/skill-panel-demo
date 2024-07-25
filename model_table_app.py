from __future__ import annotations

import logging

import panel as pn

from seareport_skill import load_model_stats
from seareport_skill import settings

logging.basicConfig(level=10)
logger = logging.getLogger()

pn.extension()
pn.extension("tabulator")

version = pn.widgets.Select(
    name="Version", options=settings.VERSIONS, sizing_mode="stretch_width"
)
metrics = pn.widgets.MultiSelect(
    name="Metrics", options=settings.METRICS, size=8, sizing_mode="stretch_width"
)
stations = pn.widgets.CrossSelector(
    name="Stations",
    options=load_model_stats("v0.0").index.tolist(),
)

show_colors = pn.widgets.Checkbox(
    name="Show colors", value=False, sizing_mode="stretch_width"
)

if pn.state.location:
    pn.state.location.sync(version, {"value": version.name})
    pn.state.location.sync(metrics, {"value": metrics.name})
    pn.state.location.sync(stations, {"value": stations.name})


@pn.depends(version, metrics, stations, show_colors)
def update_dataframe(
    version_val, metrics_val, stations_val, show_colors_val
) -> pn.pane.DataFrame:
    stats = load_model_stats(version_val)
    if metrics_val:
        stats = stats[metrics_val]
    else:
        stats = stats[settings.METRICS.values()]
    if stations_val:
        stats = stats.loc[stations_val]
    if show_colors_val:
        df_pane = pn.widgets.Tabulator(
            stats,
            sizing_mode="stretch_width",
            stylesheets=[settings.TABULATOR_CSS],
            formatters=settings.TABULATOR_FORMATTER,
            configuration=settings.TABULATOR_CONFIG,
            layout="fit_data_table",
        )
    else:
        df_pane = pn.widgets.Tabulator(
            stats, sizing_mode="stretch_width", stylesheets=[settings.TABULATOR_CSS]
        )
    return df_pane


template = pn.template.MaterialTemplate(
    title="Metrics Table",
    sidebar=[version, metrics, stations, show_colors],
    sidebar_width=430,
    main=[update_dataframe],
)
template.servable()
