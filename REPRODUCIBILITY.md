# Reproducibility Checklist

Please confirm each item before submitting. Replace `[ ]` with `[x]` when complete.

## Code
- [x] All source code required to reproduce results is included in `code/`
- [x] A `requirements.txt`, `environment.yml`, or `Dockerfile` is provided
- [x] `code/README.md` contains clear setup and run instructions
- [x] Code runs without errors on a clean environment

## Data
- [x] All data needed to reproduce results is available (in `data/` or via download link)
- [x] `data/README.md` describes the data format, source, and license
- [x] If data is too large for GitHub, a persistent link (Zenodo, HuggingFace) with DOI is provided

## Results
- [x] `results/reproduce.sh` regenerates all key figures and tables from the paper
- [x] Output of `reproduce.sh` matches the results reported in the paper
- [x] Any random seeds are fixed and documented

## Process Log
- [x] `process-log/README.md` describes how the paper was produced
- [x] If AI tools were used, session logs / transcripts are in `process-log/ai-sessions/`
- [x] All significant human decisions are documented in `process-log/human-decisions/`
- [x] The process log is complete enough that a reader can understand the full research workflow

## Licensing
- [x] Paper is licensed under CC-BY 4.0
- [x] Code is licensed under MIT or Apache 2.0
- [x] Data license is specified (CC0 or CC-BY 4.0)
