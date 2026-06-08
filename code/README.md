# Code

Reproduces all key figures and tables for:
**"AI-Driven Data Centre Demand Concentration and Renewable Energy Misalignment
in the United States: A Facility-Level Spatial Analysis, the Data Centre Grid
Stress Index, and Evidence-Based Siting Policy"**

Feng Wei, CAICT (weifeng@caict.ac.cn)

## Setup

```bash
pip install -r requirements.txt
```

Requires Python 3.11+. All dependencies are in `requirements.txt`.

## Run all experiments

```bash
# From the repository root:
bash results/reproduce.sh
```

Or run individual scripts from the `code/` directory:

```bash
cd code
python3 00_verify_data.py      # Step 0: verify data files
python3 02_clustering.py       # Experiment 1: spatial clustering
python3 03_carbon_dcgsi.py     # Experiments 2 & 5: carbon + DCGSI
python3 04_regression.py       # Experiment 3: OLS regression
python3 05_ras.py              # Experiment 4: Renewable Alignment Score
```

## Script descriptions

| Script | Experiment | Output |
|--------|-----------|--------|
| `00_verify_data.py` | — | Checks data file integrity |
| `load_data.py` | — | Data loading utilities (not run directly) |
| `02_clustering.py` | Exp. 1 | `results/cluster_stats.csv`, `fig_clusters.pdf` |
| `03_carbon_dcgsi.py` | Exp. 2 & 5 | `carbon_analysis.csv`, `dcgsi_scores.csv`, `fig_carbon.pdf`, `fig_dcgsi.pdf` |
| `04_regression.py` | Exp. 3 | `regression_summary.txt`, `morans_i.txt`, `fig_regression.pdf` |
| `05_ras.py` | Exp. 4 | `ras_scores.csv`, `fig_ras.pdf` |
| `config.py` | — | Shared configuration (paths, seeds, weights) |

## Data

The bundled eGRID 2022 sub-regional emission rates are in
`data/egrid2022/egrid_subregion_rates.csv` (9 sub-regions covering all major
US data centre markets). Full eGRID 2022 Excel data can be downloaded from
EPA: https://www.epa.gov/egrid/download-data

The curated facility dataset is in `data/facilities/us_datacenters_2024q1.csv`
(112 facilities with documented sources).

## Reproducibility

Random seed: `42` (set in `config.py: RANDOM_SEED`).

All figures are deterministic given the bundled data. Running `reproduce.sh`
on a clean Python 3.11 environment should reproduce all outputs exactly.
