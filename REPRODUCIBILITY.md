# Reproducibility Checklist

Please confirm each item before submitting. Replace `[ ]` with `[x]` when complete.

## Code
- [ ] All source code required to reproduce results is included in `code/`
- [ ] A `requirements.txt`, `environment.yml`, or `Dockerfile` is provided
- [ ] `code/README.md` contains clear setup and run instructions
- [ ] Code runs without errors on a clean environment

## Data
- [ ] All data needed to reproduce results is available (in `data/` or via download link)
- [ ] `data/README.md` describes the data format, source, and license
- [ ] If data is too large for GitHub, a persistent link (Zenodo, HuggingFace) with DOI is provided

## Results
- [ ] `results/reproduce.sh` regenerates all key figures and tables from the paper
- [ ] Output of `reproduce.sh` matches the results reported in the paper
- [ ] Any random seeds are fixed and documented

## Process Log
- [ ] `process-log/README.md` describes how the paper was produced
- [ ] If AI tools were used, session logs / transcripts are in `process-log/ai-sessions/`
- [ ] All significant human decisions are documented in `process-log/human-decisions/`
- [ ] The process log is complete enough that a reader can understand the full research workflow

## Licensing
- [ ] Paper is licensed under CC-BY 4.0
- [ ] Code is licensed under MIT or Apache 2.0
- [ ] Data license is specified (CC0 or CC-BY 4.0)
