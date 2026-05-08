# Code

## Setup

```bash
pip install -r requirements.txt
```

## Usage

[Describe how to run your code here.]

## Structure

```
code/
├── README.md               # This file
├── requirements.txt        # Python dependencies
├── data_processing/        # Data loading, cleaning, preprocessing
├── models/                 # Model definitions and training
├── analysis/               # Post-processing and analysis scripts
├── figures/                # One Python script per paper figure
├── validation/             # Convergence studies, benchmarks
├── results/                # Output data files
└── utils/
    └── plotting_utils.py   # Shared figure styling (COLORS, setup_style, save_figure)
```

## Figure Generation

Each figure in the paper has a corresponding script in `code/figures/`. To regenerate
all figures:

```bash
cd code/figures
for script in plot_*.py; do python3 "$script"; done
```

All figure scripts import shared styling from `utils/plotting_utils.py` to ensure
consistent appearance across the paper.
