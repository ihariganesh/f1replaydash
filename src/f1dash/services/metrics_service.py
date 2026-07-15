import math

import pandas as pd


def calculate_best_lap_gaps(laps_df: pd.DataFrame) -> pd.DataFrame:
    """Compute each driver's best lap and gap to session leader."""
    if laps_df.empty or "Driver" not in laps_df.columns or "LapTime" not in laps_df.columns:
        return pd.DataFrame(columns=["Driver", "best_lap_seconds", "gap_to_leader_seconds"])

    working = laps_df[["Driver", "LapTime"]].copy()
    working = working.dropna(subset=["LapTime"])

    if working.empty:
        return pd.DataFrame(columns=["Driver", "best_lap_seconds", "gap_to_leader_seconds"])

    working["best_lap_seconds"] = working["LapTime"].dt.total_seconds()

    best = (
        working.groupby("Driver", as_index=False)["best_lap_seconds"]
        .min()
        .sort_values("best_lap_seconds")
    )

    leader = best["best_lap_seconds"].iloc[0]
    best["gap_to_leader_seconds"] = best["best_lap_seconds"] - leader

    best["best_lap_seconds"] = best["best_lap_seconds"].apply(
        lambda value: None if math.isnan(value) else round(float(value), 3)
    )
    best["gap_to_leader_seconds"] = best["gap_to_leader_seconds"].apply(
        lambda value: None if math.isnan(value) else round(float(value), 3)
    )

    return best
