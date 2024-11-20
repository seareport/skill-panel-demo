from __future__ import annotations

import functools
import pathlib
import typing as T

import colorcet as cc
import geopandas as gp
import pandas as pd
import seareport_data as D
import shapely.geometry
import thalassa
from thalassa import api

import seareport_skill.settings as settings
from seareport_skill.settings import MESHES
from utils.tools import key_to_value

__all__: list[str] = [
    "load_countries",
    "load_model_stats",
    "load_stats",
    "load_parquet",
]


@functools.cache
def load_countries(res="l") -> gp.GeoDataFrame:
    path = D.gshhg(res, 5)
    countries = gp.read_file(path)
    polygons = countries[countries.geom_type == "Polygon"]
    return polygons


@functools.cache
def load_model_stats(model_version) -> pd.DataFrame:
    df = pd.read_parquet(f"assets/{model_version}.parquet").astype(float).sort_index()
    return df


@functools.cache
def load_mesh(model_version) -> pd.DataFrame:
    mesh_file = f"assets/meshes/{MESHES[model_version]}.slf"
    df = api.open_dataset(mesh_file)
    df = thalassa.utils.drop_elements_crossing_idl(df)
    return df


@functools.cache
def load_parquet(folder: str, id: str) -> pd.DataFrame:
    try:
        return pd.read_parquet(f"{folder}/{id}.parquet")
    except FileNotFoundError as e:
        raise ValueError(f"Parquet file not found for {id} in folder {folder}: {e}")


@functools.cache
def load_stats() -> pd.DataFrame:
    dataframes = []
    for pqfile in sorted(pathlib.Path("assets").glob("*.parquet")):
        version = pqfile.stem
        df = load_model_stats(version)
        # XXX Normalize values: This should be done directly in the skill calculations
        # df = df[(df > -2) & (df < 2)]
        df = df.assign(version=version)
        df["version"] = df.version.astype("category")
        dataframes.append(df)
    stats = pd.concat(dataframes).sort_values(["version"], ascending=False)
    return T.cast(pd.DataFrame, stats)


def find_ocean_for_station(station, oceans_df, xstr="longitude", ystr="latitude"):
    point = shapely.geometry.Point(station[xstr], station[ystr])
    for _, ocean in oceans_df.iterrows():
        if point.within(ocean["geometry"]):
            # Return a tuple with the two desired column values
            return ocean["name"], ocean["ocean"]
    # Return a tuple with None for both values if no match is found
    return None, None


def assign_oceans(df):
    oceans_ = gp.read_file("assets/world_oceans_final.json")
    # Use the result_type='expand' to expand list-like results to columns
    df[["name", "ocean"]] = df.apply(
        lambda station: find_ocean_for_station(station, oceans_, "obs_lon", "obs_lat"),
        axis=1,
        result_type="expand",
    )
    return df


class DashboardTS:
    """
    Initializes the global variables for the dashboard
    """

    def __init__(self, default_model=None):
        if default_model is None:
            self.VERSION = ""
        else:
            self.VERSION = key_to_value(default_model, settings.VERSIONS)
        self.STATS = load_model_stats(self.VERSION)
        self.STATS["id"] = self.STATS.index
        self.MESH_ = thalassa.plot_mesh(load_mesh(self.VERSION))
        self.COUNTRIES = load_countries("c")
        # extremes
        self.EXTREMES = None
        self.EVENT = None
        self.CLUSTER_H = 72
        self.COUNT = 0
        self.CM_CAT = cc.glasbey
        self.CM = cc.colorwheel
        self.KDIMS = ["time lag [hours]", "error [m]"]

    def update_stats(self, version):
        self.STATS = load_model_stats(version)
        self.STATS["id"] = self.STATS.index
