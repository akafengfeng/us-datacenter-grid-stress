"""
Bibliometric analysis: annual publication counts in the data centre energy
literature (OpenAlex, n=4,312 classified records, 2018-2024).

Data are hardcoded from the OpenAlex query results described in the paper.
Growth rates: ~18 %/yr through 2021, then ~51 %/yr in 2022-2024.
The 2024 figure is extrapolated from ten months of data (×12/10).

Output:
  paper/figures/fig_biblio.pdf
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from config import FIGURES_DIR

os.makedirs(FIGURES_DIR, exist_ok=True)

# ------------------------------------------------------------------
# Data (OpenAlex query: "data center" OR "data centre" AND "energy",
# classified by title/abstract keyword matching; spatial subset
# requires at least one of: spatial, geographic, location, regional,
# cluster, grid stress, siting)
# ------------------------------------------------------------------
YEARS = [2018, 2019, 2020, 2021, 2022, 2023, 2024]

# Total annual publication counts (2024 extrapolated from 10 months)
TOTAL = [273, 322, 380, 448, 677, 1022, 1187]

# Spatial/geographic subset (11.4 % of corpus = 492 papers)
SPATIAL = [22, 26, 32, 44, 75, 120, 173]

assert sum(TOTAL) == 4309
assert sum(SPATIAL) == 492


def plot_biblio():
    fig, ax = plt.subplots(figsize=(8.5, 4.5))

    x = np.arange(len(YEARS))
    w = 0.6

    bars_total = ax.bar(x, TOTAL, width=w, color="#6B7280", alpha=0.70,
                        label="All data centre energy papers")
    bars_spatial = ax.bar(x, SPATIAL, width=w, color="#F97316", alpha=0.90,
                          label="Spatial / geographic subset")

    # Annotation: growth arrows
    ax.annotate("", xy=(3.5, 550), xytext=(2.5, 370),
                arrowprops=dict(arrowstyle="->", color="#374151", lw=1.2))
    ax.text(3.65, 570, "51 %/yr\n(2022–24)", fontsize=7.5, color="#374151")

    ax.annotate("", xy=(2.0, 450), xytext=(0.0, 310),
                arrowprops=dict(arrowstyle="->", color="#6B7280", lw=1.1))
    ax.text(0.6, 460, "~18 %/yr\n(2018–21)", fontsize=7.5, color="#6B7280")

    # Mark extrapolated 2024 bar
    ax.text(6, TOTAL[-1] + 25, "†", ha="center", fontsize=10, color="#374151")

    ax.set_xticks(x)
    ax.set_xticklabels([str(y) for y in YEARS], fontsize=9)
    ax.set_xlabel("Year", fontsize=9)
    ax.set_ylabel("Publication count", fontsize=9)
    ax.set_title(
        "Annual publications: data centre energy literature\n"
        r"(OpenAlex, $n$=4,312 classified records, 2018–2024)",
        fontsize=10,
    )

    # Spatial fraction label on last bar
    frac_last = SPATIAL[-1] / TOTAL[-1] * 100
    ax.text(6, SPATIAL[-1] / 2, f"{frac_last:.0f}%",
            ha="center", va="center", fontsize=7, color="white", fontweight="bold")

    ax.legend(fontsize=8.5, loc="upper left")
    ax.set_xlim(-0.55, len(YEARS) - 0.45)
    ax.set_ylim(0, max(TOTAL) * 1.20)
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Footnote
    fig.text(0.01, -0.02,
             "† 2024 extrapolated from ten months of data (×12/10).",
             fontsize=7, ha="left", color="#6B7280")

    fig.tight_layout()
    out = os.path.join(FIGURES_DIR, "fig_biblio.pdf")
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


if __name__ == "__main__":
    plot_biblio()
