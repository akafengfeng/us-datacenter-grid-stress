"""
Experiment 1: Weighted k-means spatial clustering of US data centre capacity.

Outputs
-------
results/cluster_stats.csv          — cluster centroids, shares, silhouette
results/figures/fig_clusters.pdf   — bubble map of clusters
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.utils import resample
from config import *
from load_data import load_facilities

os.makedirs(FIGURES_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

CLUSTER_LABELS = {
    0: "Northern Virginia",
    1: "Dallas–Fort Worth",
    2: "Chicago Metro",
    3: "Phoenix",
    4: "Atlanta",
    5: "Pacific Northwest",
    6: "SF Bay Area",
    7: "NYC Metro",
}

CLUSTER_COLORS = [
    "#2563EB",  # blue       – N. Virginia
    "#DC2626",  # red        – DFW
    "#D97706",  # amber      – Chicago
    "#059669",  # green      – Phoenix
    "#7C3AED",  # violet     – Atlanta
    "#0891B2",  # cyan       – Pacific NW
    "#B45309",  # brown      – SF Bay
    "#6B7280",  # gray       – NYC
]


def run_clustering(df: pd.DataFrame, k: int = K_CLUSTERS, seed: int = RANDOM_SEED):
    coords = df[["lat", "lon"]].values
    weights = df["it_load_mw_est"].values

    km = KMeans(n_clusters=k, init="k-means++", n_init=20,
                random_state=seed, max_iter=500)
    km.fit(coords, sample_weight=weights)

    df = df.copy()
    df["cluster"] = km.labels_

    sil = silhouette_score(coords, km.labels_,
                           sample_size=min(5000, len(df)),
                           random_state=seed)
    return df, km, sil


def cluster_summary(df: pd.DataFrame, km) -> pd.DataFrame:
    total_mw = df["it_load_mw_est"].sum()
    rows = []
    for c in range(km.n_clusters):
        mask = df["cluster"] == c
        sub = df[mask]
        cap = sub["it_load_mw_est"].sum()
        rows.append({
            "cluster_id":    c,
            "label":         CLUSTER_LABELS.get(c, f"Cluster {c}"),
            "lat":           km.cluster_centers_[c, 0],
            "lon":           km.cluster_centers_[c, 1],
            "capacity_gw":   cap / 1000,
            "share_pct":     cap / total_mw * 100,
            "n_facilities":  len(sub),
            "top_state":     sub.groupby("state")["it_load_mw_est"].sum().idxmax(),
            "top_egrid":     sub.groupby("egrid_subrgn")["it_load_mw_est"].sum().idxmax(),
        })
    return pd.DataFrame(rows).sort_values("share_pct", ascending=False)


def bootstrap_shares(df: pd.DataFrame, km, n: int = N_BOOTSTRAP,
                     seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Bootstrap 95% CIs on cluster capacity shares."""
    np.random.seed(seed)
    records = []
    for _ in range(n):
        boot = resample(df, replace=True, n_samples=len(df),
                        random_state=np.random.randint(0, 2**31))
        total = boot["it_load_mw_est"].sum()
        for c in range(km.n_clusters):
            share = boot.loc[boot["cluster"] == c, "it_load_mw_est"].sum() / total * 100
            records.append({"cluster": c, "share": share})
    bdf = pd.DataFrame(records)
    ci = (bdf.groupby("cluster")["share"]
            .quantile([0.025, 0.975])
            .unstack()
            .rename(columns={0.025: "ci_lo", 0.975: "ci_hi"}))
    return ci


def plot_clusters(df: pd.DataFrame, km, stats: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(11, 6))

    for _, row in stats.iterrows():
        c = int(row["cluster_id"])
        color = CLUSTER_COLORS[c % len(CLUSTER_COLORS)]
        size = row["share_pct"] * 30          # scale bubble
        ax.scatter(row["lon"], row["lat"], s=size, c=color,
                   alpha=0.75, zorder=5, edgecolors="white", linewidths=0.8)
        ax.annotate(f"{row['label']}\n({row['share_pct']:.1f}%)",
                    xy=(row["lon"], row["lat"]),
                    xytext=(8, 4), textcoords="offset points",
                    fontsize=7.5, color="#1F2937")

    # Background scatter of all facilities
    ax.scatter(df["lon"], df["lat"], s=1.5, c="#9CA3AF", alpha=0.35, zorder=3)

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
    df, km, sil = run_clustering(df)
    print(f"Silhouette score: {sil:.3f}")

    stats = cluster_summary(df, km)
    ci = bootstrap_shares(df, km)
    stats = stats.merge(ci.reset_index().rename(columns={"cluster": "cluster_id"}),
                        on="cluster_id", how="left")
    print(stats[["label", "capacity_gw", "share_pct", "ci_lo", "ci_hi",
                 "top_state", "top_egrid"]].to_string(index=False))
    stats.to_csv(os.path.join(RESULTS_DIR, "cluster_stats.csv"), index=False)
    plot_clusters(df, km, stats)
