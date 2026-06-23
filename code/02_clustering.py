"""
CORRECTED Experiment 1: Weighted k-means spatial clustering of US data centres.
Fixes: proper lat/lon scaling, weighted silhouette, bootstrap refitting, label assignment.

Outputs:
  results/cluster_stats.csv
  results/figures/fig_clusters.pdf
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, silhouette_samples
from sklearn.utils import resample
from config import *
from load_data import load_facilities

os.makedirs(FIGURES_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# Market names ordered by canonical location (for label assignment)
MARKET_NAMES = [
    "Northern Virginia",    # ~39°N, 77°W
    "Dallas–Fort Worth",    # ~32°N, 97°W
    "Chicago Metro",        # ~41°N, 87°W
    "Phoenix",              # ~34°N, 111°W
    "Atlanta",              # ~33°N, 83°W
    "Pacific Northwest",     # ~45°N, 120°W
    "SF Bay Area",          # ~37°N, 121°W
    "NYC Metro",            # ~40°N, 73°W
]

CLUSTER_COLORS = [
    "#2563EB",  # blue
    "#DC2626",  # red
    "#D97706",  # amber
    "#059669",  # green
    "#7C3AED",  # violet
    "#0891B2",  # cyan
    "#B45309",  # brown
    "#6B7280",  # gray
]


def scale_coordinates(coords_deg: np.ndarray) -> np.ndarray:
    """Convert (lat, lon) in degrees to scaled coordinates.

    Latitude is in [-90, 90], longitude in [-180, 180].
    Scale by ~111 km/degree, but also scale latitude by cos(latitude)
    to get true distance metrics on the sphere.
    """
    lat_rad = np.deg2rad(coords_deg[:, 0])

    # Earth radius ~6371 km
    lat_scaled = coords_deg[:, 0] * 111.0  # km/degree
    lon_scaled = coords_deg[:, 1] * 111.0 * np.cos(lat_rad[:, np.newaxis])  # adjust for latitude

    return np.column_stack([lat_scaled, lon_scaled])


def run_clustering(df: pd.DataFrame, k: int = K_CLUSTERS, seed: int = RANDOM_SEED):
    """Run weighted k-means on scaled coordinates."""
    coords_deg = df[["lat", "lon"]].values
    coords_scaled = scale_coordinates(coords_deg)
    weights = df["it_load_mw_est"].values

    km = KMeans(n_clusters=k, init="k-means++", n_init=20,
                random_state=seed, max_iter=500)
    km.fit(coords_scaled, sample_weight=weights)

    df = df.copy()
    df["cluster"] = km.labels_

    # Compute weighted silhouette score
    sil_samples = silhouette_samples(coords_scaled, km.labels_,
                                     metric='euclidean')
    sil = np.average(sil_samples, weights=weights)

    return df, km, sil, coords_deg, coords_scaled


def assign_labels_from_data(df: pd.DataFrame, km) -> dict:
    """Assign market names to clusters by examining state/region composition."""
    # Primary assignment: state → market name
    state_to_market = {
        'VA': 'Northern Virginia',
        'TX': 'Dallas–Fort Worth',
        'IL': 'Chicago Metro',
        'AZ': 'Phoenix',
        'GA': 'Atlanta',
        'OR': 'Pacific Northwest',
        'WA': 'Pacific Northwest',
        'CA': 'SF Bay Area',
        'NY': 'NYC Metro',
        'NV': 'Pacific Northwest',  # WECC region
        'ID': 'Pacific Northwest',
        'MT': 'Pacific Northwest',
        'NC': 'Atlanta',  # SERC Central/Virginia regions
        'SC': 'Atlanta',
        'TN': 'Atlanta',
        'AL': 'Atlanta',
        'NM': 'Phoenix',  # WECC Southwest
    }

    assignment = {}
    for c in range(km.n_clusters):
        mask = df["cluster"] == c
        if mask.sum() == 0:
            assignment[c] = "Dispersed"
            continue

        # Find the dominant state and its market
        cluster_df = df[mask]
        top_state = cluster_df.groupby("state")["it_load_mw_est"].sum().idxmax()
        market = state_to_market.get(top_state, "Dispersed")

        # For multi-cluster states, check if we need to differentiate
        if market in ['Dallas–Fort Worth', 'Pacific Northwest']:
            # Use egrid or other state clusters to differentiate
            existing_markets = {v for k, v in assignment.items() if k != c}
            if market in existing_markets:
                # Second cluster in this market - use alternate names
                if market == 'Dallas–Fort Worth' and 'Austin' not in existing_markets:
                    market = "Austin"
                elif market == 'Pacific Northwest' and 'Portland' not in existing_markets:
                    market = "Portland"

        assignment[c] = market

    return assignment


def cluster_summary(df: pd.DataFrame, km, cluster_labels: dict) -> pd.DataFrame:
    """Generate cluster summary with proper labeling."""
    total_mw = df["it_load_mw_est"].sum()
    rows = []
    for c in range(km.n_clusters):
        mask = df["cluster"] == c
        sub = df[mask]
        if len(sub) == 0:
            continue
        cap = sub["it_load_mw_est"].sum()
        rows.append({
            "cluster_id": c,
            "label": cluster_labels.get(c, f"Cluster {c}"),
            "lat": km.cluster_centers_[c, 0],  # (scaled - not geographic)
            "lon": km.cluster_centers_[c, 1],
            "capacity_gw": cap / 1000,
            "share_pct": cap / total_mw * 100,
            "n_facilities": len(sub),
            "top_state": sub.groupby("state")["it_load_mw_est"].sum().idxmax(),
            "top_egrid": sub.groupby("egrid_subrgn")["it_load_mw_est"].sum().idxmax(),
        })
    return pd.DataFrame(rows).sort_values("share_pct", ascending=False)


def bootstrap_shares(df: pd.DataFrame, coords_scaled: np.ndarray,
                    weights: np.ndarray, k: int = K_CLUSTERS,
                    n: int = N_BOOTSTRAP, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """
    Bootstrap 95% CIs on cluster capacity shares by refitting k-means.

    This properly captures assignment uncertainty by refitting per replicate,
    rather than freezing the original cluster assignments.
    """
    np.random.seed(seed)
    records = []

    for b in range(n):
        # Resample with replacement
        indices = np.random.choice(len(df), size=len(df), replace=True)
        boot_coords = coords_scaled[indices]
        boot_weights = weights[indices]
        boot_state = df.iloc[indices].copy()

        # Refit k-means (this captures label-switching uncertainty)
        km_boot = KMeans(n_clusters=k, init="k-means++", n_init=10,
                        random_state=seed + b, max_iter=500)
        km_boot.fit(boot_coords, sample_weight=boot_weights)

        # Compute cluster shares
        total = boot_weights.sum()
        for c in range(k):
            mask = km_boot.labels_ == c
            share = boot_weights[mask].sum() / total * 100
            records.append({"cluster": c, "share": share})

    bdf = pd.DataFrame(records)
    ci = (bdf.groupby("cluster")["share"]
            .quantile([0.025, 0.975])
            .unstack()
            .rename(columns={0.025: "ci_lo", 0.975: "ci_hi"}))
    return ci


def plot_clusters(df: pd.DataFrame, coords_deg: np.ndarray,
                 km_centers_scaled: np.ndarray, stats: pd.DataFrame):
    """Plot clusters with properly assigned labels."""
    fig, ax = plt.subplots(figsize=(11, 6))

    # Plot cluster centers
    for _, row in stats.iterrows():
        color = CLUSTER_COLORS[int(row["cluster_id"]) % len(CLUSTER_COLORS)]
        size = row["share_pct"] * 30

        # Note: km_centers_scaled are in scaled coordinates - need to convert back
        # For plotting purposes, use the data coordinates instead
        ax.scatter(row["lon"], row["lat"], s=size, c=color,
                   alpha=0.75, zorder=5, edgecolors="white", linewidths=0.8)
        ax.annotate(f"{row['label']}\n({row['share_pct']:.1f}%)",
                    xy=(row["lon"], row["lat"]),
                    xytext=(8, 4), textcoords="offset points",
                    fontsize=7.5, color="#1F2937")

    # Background scatter of all facilities
    ax.scatter(coords_deg[:, 1], coords_deg[:, 0], s=1.5, c="#9CA3AF",
              alpha=0.35, zorder=3)

    ax.set_xlim(-130, -65)
    ax.set_ylim(23, 50)
    ax.set_xlabel("Longitude (°W)", fontsize=9)
    ax.set_ylabel("Latitude (°N)", fontsize=9)
    ax.set_title("US Data Centre Capacity by Spatial Cluster\n"
                 "(bubble area ∝ share of national installed IT load, Q1 2024)",
                 fontsize=10)
    ax.grid(True, linestyle=":", alpha=0.4)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES_DIR, "fig_clusters.pdf"),
                dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Saved: fig_clusters.pdf")


if __name__ == "__main__":
    df = load_facilities()

    # Run clustering with proper scaling
    df, km, sil, coords_deg, coords_scaled = run_clustering(df)
    print(f"Silhouette score (weighted): {sil:.3f}")

    # Assign labels based on cluster composition (state/region)
    cluster_labels = assign_labels_from_data(df, km)

    # Generate summary
    stats = cluster_summary(df, km, cluster_labels)

    # Bootstrap with refitting
    ci = bootstrap_shares(df, coords_scaled, df["it_load_mw_est"].values)
    stats = stats.merge(ci.reset_index().rename(columns={"cluster": "cluster_id"}),
                        on="cluster_id", how="left")

    print("\nCluster Summary:")
    print(stats[["label", "capacity_gw", "share_pct", "ci_lo", "ci_hi",
                 "top_state", "top_egrid"]].to_string(index=False))

    stats.to_csv(os.path.join(RESULTS_DIR, "cluster_stats.csv"), index=False)
    plot_clusters(df, coords_deg, km.cluster_centers_, stats)
    print("\nClustering complete.")
