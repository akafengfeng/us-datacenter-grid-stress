# Research Process Log

## Overview

This paper was produced by Feng Wei (CAICT) with assistance from Claude Code
(Anthropic's AI coding assistant). The research workflow followed the AIDER
AI-assisted research methodology.

## Tools Used

- **Claude Code (claude-sonnet-4-6)** — AI assistant for literature synthesis,
  methodology design, code generation, and LaTeX drafting
- **Python 3.11** — Data analysis, spatial clustering, regression, figure generation
- **LaTeX / pdflatex** — Manuscript preparation (Elsevier elsarticle class)
- **EPA eGRID 2022** — Grid emission rate data
- **EIA Electric Power Monthly** — Electricity demand data

## Workflow

1. **Problem formulation** — Author identified the gap: no facility-level
   spatial analysis of US data centre energy demand simultaneously addressing
   carbon intensity, grid stress, and renewable misalignment.
2. **Literature review** — Systematic PRISMA-ScR search across Web of Science,
   Scopus, Google Scholar (2018–2024), 312 records screened.
3. **Data acquisition** — Curated facility dataset (112 entries) from
   regulatory filings and operator disclosures; EPA eGRID 2022 (CO2 rates);
   EIA demand data.
4. **Methodology development** — Designed DCGSI composite index, spatial
   clustering approach, HC3-robust regression with Moran's I diagnostics.
5. **Implementation** — Python scripts (see `code/`) with fixed random seeds.
6. **Writing** — LaTeX manuscript drafted with AI assistance, revised by author.
7. **Verification** — All figures generated from Python code; no hardcoded data
   in LaTeX.

## AI Sessions

See [`ai-sessions/`](ai-sessions/) for session summaries.

Claude Code was used as a co-author assistant. All research decisions
(data sources, methodology choices, policy interpretations) were made
and verified by the human author.

## Human Decisions

See [`human-decisions/`](human-decisions/) for significant research decisions
made by the author during the project.
