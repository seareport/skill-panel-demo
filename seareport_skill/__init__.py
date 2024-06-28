from __future__ import annotations

import pandas as pd

__all__: list[str] = [
    "load_stats",
]


def load_stats(model_version) -> pd.DataFrame:
    df = pd.read_parquet(f"assets/{model_version}.parquet").astype(float).sort_index()
    return df
