# Reproducibility Checklist

## Code Requirements
- [x] All source code is in `code/` with dependency specifications
- [x] `code/README.md` documents setup and execution
- [x] Code verified to run in a clean Python 3.11 environment

## Data Management
- [x] All required datasets are publicly available (EIA, EPA eGRID, LBNL)
- [x] `data/README.md` documents data sources, formats, and licenses
- [x] Persistent DOI or URL provided for each dataset

## Results Validation
- [x] `results/reproduce.sh` regenerates all key figures and tables
- [x] Random seeds are fixed in `code/config.py` (seed = 42 for k-means)
- [x] All numerical results in the paper match script output

## Process Documentation
- [x] `process-log/README.md` describes research methodology
- [x] AI session logs are in `process-log/ai-sessions/`
- [x] Human editorial decisions are documented in `process-log/human-decisions/`

## Licensing
- [x] Paper manuscript: CC-BY 4.0
- [x] Code: MIT License
- [x] Data: Source datasets are public domain (US government data)
