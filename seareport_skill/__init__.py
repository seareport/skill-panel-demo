from __future__ import annotations

import geodatasets
import geopandas as gp
import pandas as pd
import shapely

__all__: list[str] = [
    "load_model_stats",
]


def load_countries() -> gp.GeoDataFrame:
    path = geodatasets.get_path("naturalearth_land")
    countries = gp.read_file(path)
    return countries


def load_model_stats(model_version) -> pd.DataFrame:
    df = pd.read_parquet(f"assets/{model_version}.parquet").astype(float).sort_index()
    return df


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
