import geoviews as gv
import holoviews as hv
import numpy as np
import pandas as pd
from holoviews import opts
from holoviews.operation.datashader import rasterize
from holoviews.operation.datashader import spread
from seastats.stats import get_percentiles
from seastats.stats import get_slope_intercept
from seastats.storms import match_extremes


def scatter_plot(
    df,
    x,
    y,
    z=None,
    color="r",
    line_coror="k",
    line_width=2,
    cmap=None,
    show_legend=False,
    colorbar=False,
    geo=False,
) -> hv.Points:
    if z is None:
        color = color
    else:
        color = z
    if geo:
        p = gv.Points(df, kdims=[x, y]).opts(
            opts.Points(
                show_title=False,
                tools=["hover", "box_select", "tap"],
                size=7,
                color=color,
                line_color=line_coror,
                line_width=line_width,
                cmap=cmap,
                show_legend=show_legend,
                colorbar=colorbar,
            ),
        )
    else:
        p = hv.Points(df, kdims=[x, y]).opts(
            opts.Points(
                show_title=False,
                tools=["hover", "box_select", "tap"],
                size=7,
                color=color,
                line_color=line_coror,
                line_width=line_width,
                cmap=cmap,
                show_legend=show_legend,
                colorbar=colorbar,
            ),
        )
    return p


def stacked_hist(plot, element):
    """found here https://discourse.holoviz.org/t/stacked-histogram/6205/2"""
    offset = 0
    for r in plot.handles["plot"].renderers:
        r.glyph.bottom = "bottom"

        data = r.data_source.data
        new_offset = data["top"] + offset
        data["top"] = new_offset
        data["bottom"] = offset * np.ones_like(data["top"])
        offset = new_offset

    plot.handles["plot"].y_range.end = max(offset) * 1.1
    plot.handles["plot"].y_range.reset_end = max(offset) * 1.1


def hist_(src, z, z_name, g="ocean", map=None, type="box"):
    if z in ["rmse", "rms", "rms_95", "mad", "madp"]:
        range_ = (0, 0.5)
    elif z in ["bias"]:
        range_ = (-0.2, 0.2)
    elif z in ["slope"]:
        range_ = (0, 2)
    else:
        range_ = (0, 1)

    df = src[[z, g]].reset_index()
    #
    unique_oceans = df[g].unique()
    # Create a new DataFrame with one-hot encoded structure
    rows = []
    for index, row in df.iterrows():
        new_row = {group: np.nan for group in unique_oceans}
        new_row[row[g]] = row[z]
        rows.append(new_row)
    #
    mean = src[z].mean()
    color_key = hv.Cycle("Category20").values
    # only way to get the colors to match the ocean mapping
    if map is None:
        map = {
            ocean: color_key[i % len(color_key)]
            for i, ocean in enumerate(unique_oceans)
        }
    colors = [map[ocean] for ocean in unique_oceans]
    if type == "violin":
        return hv.Violin(
            df,
            g,
            z,
        ).opts(
            violin_fill_color=g,
            cmap=map,
            invert_axes=True,
            ylim=range_,
            title=f"{z_name}, mean value: {mean:.2f}",
            ylabel=z_name,
        )
    elif type == "box":
        return hv.BoxWhisker(
            df,
            g,
            z,
        ).opts(
            box_color=g,
            cmap=map,
            invert_axes=True,
            outlier_radius=0.0005,
            ylim=range_,
            title=f"{z_name}, mean value: {mean:.2f}",
            ylabel=z_name,
        )
    else:
        one_hot_df = pd.DataFrame(rows, columns=unique_oceans)

        return one_hot_df.hvplot.hist(
            bins=20,
            bin_range=range_,
            # cmap = ocean_mapping,
            color=colors,
        ).opts(
            hooks=[stacked_hist],
            title=f"{z_name}, mean value: {mean:.2f}",
            ylabel=z_name,
        )


def radar_plot(
    src: pd.DataFrame,
    params_dict: dict,
    oceans_list: list[str],
    g: str = "ocean",
    color_map: dict = None,
) -> hv.Overlay:
    """
    Create a radar plot for different oceans and global ocean from a source DataFrame.

    :param src: DataFrame containing the data.
    :param g: Grouping column name in the DataFrame.
    :param color_map: Dictionary mapping oceans to colors.
    :return: Holoviews Overlay object with the radar plot.
    """

    params = params_dict.values()
    # params = ["rms", "cr", "rms_95", "cr_95", "slope", "R1", "R3", "error99m", "error95m"]
    keys = params_dict.keys()
    theta = np.linspace(0, 2 * np.pi, len(params) + 1)

    def get_score(data: pd.DataFrame, ocean: str = None) -> pd.DataFrame:
        """
        Calculate scores for the given ocean or global ocean if ocean is None.
        """
        ocean_data = data if ocean is None else data[data[g] == ocean]
        results = {
            z: (
                (1 - np.round(ocean_data[z].mean(), 3))
                if z != "slope"
                else np.round(ocean_data[z].mean(), 3)
            )
            for z in params
        }
        index_name = "Global Ocean" if ocean is None else ocean
        return pd.DataFrame(results, index=[index_name])

    def create_radar_patch(scores: pd.Series, label: str) -> hv.Curve:
        """
        Create radar plot patch for the given scores.
        """
        theta = np.linspace(0, 2 * np.pi, len(scores) + 1)
        r = np.append(scores.values, scores.values[0])
        x = np.append(r * np.cos(theta), r[0] * np.cos(theta[0]))
        y = np.append(r * np.sin(theta), r[0] * np.sin(theta[0]))
        return hv.Curve((x, y), label=label)

    def create_ticks_and_labels(theta, params, num_ticks: int = 5) -> hv.Overlay:
        """Create ticks and parameter labels for the radar plot."""
        ticks = hv.Overlay()
        labels = hv.Overlay()
        markers = hv.Overlay()
        tick_values = np.linspace(0, 1, num_ticks)
        for angle, param in zip(theta, params):
            x, y = np.cos(angle), np.sin(angle)
            ticks *= hv.Curve([(0, 0), (x, y)]).opts(
                line_dash="dotted", line_color="grey"
            )
            labels *= hv.Text(x * 1.1, y * 1.1, param, halign="center", valign="center")
            for tv in tick_values[1:]:
                if param not in [
                    "Slope",
                    "Correlation Coefficient",
                    "Correlation Coefficient >95th percentile",
                ]:
                    text = str(1 - tv)
                else:
                    text = str(tv)
                markers *= hv.Text(
                    x * tv, y * tv, text, halign="center", valign="center"
                ).opts(text_font_size="9pt", text_color="black")

        return ticks, labels, markers

    # Create DataFrame to hold scores for each ocean and global ocean
    df_res = pd.concat(
        [get_score(src, ocean) for ocean in oceans_list] + [get_score(src)]
    )

    patches = hv.Overlay(
        [
            create_radar_patch(df_res.loc[ocean], ocean).opts(
                line_color=(color_map[ocean] if ocean != "Global Ocean" else "black"),
                line_width=3,
                alpha=0.7,
                show_legend=True,
            )
            for ocean in df_res.index
        ]
    )

    # Calculate score for Global Ocean
    global_scores = df_res.loc["Global Ocean"]
    score_total = global_scores.sum() / len(global_scores)

    # Create ticks for the radar plot
    ticks, labels, markers = create_ticks_and_labels(theta, keys)

    # Create polar grid lines
    grid = hv.Overlay(
        [
            hv.Curve([(r * np.cos(angle), r * np.sin(angle)) for angle in theta]).opts(
                line_dash="dotted", line_color="grey"
            )
            for r in np.linspace(0, 1, 5)
        ]
    )

    # Combine everything into the final plot
    radar_plot = (grid * ticks * patches * labels * markers).opts(
        title=f"Score: {score_total:.3f}", show_legend=True, xaxis=None, yaxis=None
    )

    return radar_plot.redim(x={"range": (-1.2, 1.2)}, y={"range": (-1.2, 1.2)})


def plot_extreme_raster(
    ts: pd.Series, ext: pd.DataFrame, color="black", label="", **kwargs
):
    """
    this function might induce overhead if the time series is too long
    """
    if ts.empty:
        ts_ = rasterize(hv.Curve(([0, 0], [1, 0]), label=label), line_width=0.5).opts(
            cmap=[color], show_grid=True, alpha=0.7, **kwargs
        )
    else:
        ts_ = rasterize(hv.Curve(ts, label=label), line_width=0.5).opts(
            cmap=[color], show_grid=True, alpha=0.7, **kwargs
        )
    if ext.empty:
        sc_ = hv.Scatter((0, 0), label=label).opts(
            opts.Scatter(line_color="black", line_alpha=0.3, fill_color=color, size=8)
        )
    else:
        sc_ = hv.Scatter(ext, label=label).opts(
            opts.Scatter(line_color="black", line_alpha=0.3, fill_color=color, size=8)
        )
    return ts_ * sc_


def scatter_plot_raster(
    ts1: pd.Series,
    ts2: pd.Series,
    quantile: float,
    cluster_duration: int = 72,
    pp_plot: bool = True,
    color: str = "black",
    label: str = "",
    kdims: list[str] = ["observed", "model"],
    **kwargs,
):
    if ts1.empty or ts2.empty:
        sc_ = spread(rasterize(hv.Points((0, 0))))
        extremes_match = pd.DataFrame()
        slope, intercept = (0, 0)
    else:
        extremes_match = match_extremes(ts2, ts1, quantile, cluster_duration)
        p = hv.Points((ts1.values, ts2.values))
        sc_ = spread(rasterize(p)).opts(
            cmap=[color], cnorm="linear", alpha=0.8, **kwargs
        )
        slope, intercept = get_slope_intercept(ts2, ts1)
    if extremes_match.empty:
        ext_ = hv.Points((0, 0))
    else:
        ext_ = hv.Points(extremes_match, kdims=kdims, label=f"extremes {label}").opts(
            size=8, fill_color=color, line_color="k", legend_position="bottom_right"
        )
    ax_plot = hv.Slope(1, 0).opts(color="grey", show_grid=True)

    lr_plot = hv.Slope(
        slope, intercept, label=f"y = {slope:.2f}x + {intercept:.2f}"
    ).opts(color=color, line_dash="dashed")
    #
    if pp_plot and not ts1.empty:
        pc1, pc2 = get_percentiles(ts1, ts2, higher_tail=True)
        ppp = hv.Scatter((pc1, pc2), label=f"perc. {label}").opts(
            fill_color=color, line_color="k", line_width=3, size=7
        )
        return ext_ * sc_ * ppp * ax_plot * lr_plot
    else:
        return ext_ * sc_ * ax_plot * lr_plot
