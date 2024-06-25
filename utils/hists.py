import holoviews as hv
import numpy as np
import pandas as pd
from holoviews import opts


def scatter_hist(src, x, y, z):
    p = hv.Points(src, kdims=[x, y]).opts(
        opts.Points(
            show_title=False,
            tools=["hover", "box_select", "tap"],
            size=10,
            color=z,
            cmap="rainbow4",
            line_color="k",
            # line_='Category20',
            # line_width=2,
            # show_legend = False,
            colorbar=True,
        ),
        opts.Histogram(tools=["hover", "box_select"]),
        # opts.Layout(shared_axes=True, shared_datasource=True, merge_tools=True,),
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


def hist_(src, z, g="ocean", map=None, type="violin"):
    if z in ["rmse", "rms", "mad", "madp"]:
        range_ = (0, 0.5)
    elif z in ["bias"]:
        range_ = (-0.2, 0.2)
    elif z in ["R1", "R3"]:
        range_ = (-1, 1)
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
            title=f"{z} mean: {mean:.2f}",
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
            outlier_radius=0.001,
            ylim=range_,
            title=f"{z} mean: {mean:.2f}",
        )
    else:
        one_hot_df = pd.DataFrame(rows, columns=unique_oceans)

        return one_hot_df.hvplot.hist(
            bins=20,
            bin_range=range_,
            # cmap = ocean_mapping,
            color=colors,
        ).opts(hooks=[stacked_hist], title=f"{z} mean: {mean:.2f}")
