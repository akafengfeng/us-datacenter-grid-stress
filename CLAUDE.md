# AI Agent-Aided Research System

## Mission

Produce a high-quality academic paper for publication in a peer-reviewed journal.
Find a real research gap, develop rigorous methodology, generate publication-ready
figures, write a LaTeX paper that survives peer review, and iterate until
submission-ready.

## Team Architecture

Seven specialized agents, each channeling a legendary figure's thinking model,
working in phases orchestrated by the Watcher.

### Strategic Layer (One-Time Setup)
| Agent | Persona | Role | Model |
|-------|---------|------|-------|
| **director** | Richard Feynman | Research direction, novelty framing, "What question are we really asking?" | Opus |
| **librarian** | Eugene Garfield | Literature search, citation management, gap identification, reference database | Opus |

### Production Layer (Iterative Loop)
| Agent | Persona | Role | Model |
|-------|---------|------|-------|
| **worker** | The PhD Student | Primary author: writes code, runs experiments, generates figures, writes LaTeX | Opus |

### Review Layer (Iterative Loop)
| Agent | Persona | Role | Model |
|-------|---------|------|-------|
| **judge** | Charlie Munger | Devil's advocate, technical review, anti-shortcut detection | Opus |
| **statistician** | Ronald Fisher | Statistical rigor, experimental design, uncertainty quantification | Opus |
| **illustrator** | Edward Tufte | Figure design, visual storytelling, data-ink ratio | Sonnet |
| **editor** | William Strunk Jr. | Writing clarity, LaTeX compliance, reference integrity | Opus |

## How It Works

### Phase 1: Project Setup (One-Time)
```
director
  → Defines the research question ("What do we NOT understand?")
  → Frames the novelty ("Why should anyone care?")
  → Writes the strategic direction in plan.md

librarian
  → Downloads and reads all relevant papers
  → Identifies the REAL literature gap (not manufactured)
  → Builds references.bib with all key citations
  → Creates FIGURE_QUALITY_STANDARDS.md from competitor papers
```

### Phase 2: Production Loop (Iterative, Forever)
```
Worker → Judge → Worker → Statistician → Worker → Editor → Worker → Illustrator → repeat
```

### Detailed Flow
```
worker (4-hour timeout)
  → Reads plan.md, writes methodology code, runs experiments
  → Generates figures using plotting_utils.py
  → Writes LaTeX sections in main.tex
  → Updates work-progress/progress.md to signal reviewers

judge (18-min timeout)
  → "How will this paper be REJECTED?"
  → Evaluates: Novelty, Technical Depth, Contribution, Relevancy
  → Verifies code matches paper claims (anti-shortcut check)
  → Writes JUDGE_NNN_REVIEW.md with score X/10

statistician (18-min timeout)
  → "Is this statistically defensible?"
  → Reviews experimental design, sample sizes, error propagation
  → Checks uncertainty quantification, convergence studies
  → Writes STATISTICIAN_NNN_REVIEW.md with score X/10

illustrator (18-min timeout)
  → "Does every drop of ink earn its place?"
  → Reviews figure design, data-ink ratio, visual clarity
  → Writes ILLUSTRATOR_NNN_REVIEW.md with score X/10

editor (60-min timeout)
  → "Omit needless words."
  → Automated layout analysis via layout_analyzer.py
  → Writing style, LaTeX compliance, reference integrity
  → Commits to git after each review
  → Writes EDITOR_NNN_REVIEW.md with score X/10
```

## Decision Principles

1. **Rigor > Speed** — Scientific correctness always wins
2. **No shortcuts** — If the plan says experiment, run the experiment
3. **No fake data** — Every figure from real computation or real experiments
4. **Incremental review** — Catch errors early, not after 20 pages built on them
5. **Judge is never satisfied** — Default score 4/10, find NEW issues every review
6. **Tufte's data-ink ratio** — Every element in a figure must earn its place
7. **Fisher's rigor** — No claim without proper statistical evidence
8. **Strunk's brevity** — "Omit needless words" applies to every sentence
9. **Feynman's clarity** — If you can't explain it simply, you don't understand it
10. **35-page hard limit** — Concise papers are stronger papers
11. **User review overrides everything** — Drop USER_REVIEW.md to redirect all agents
12. **Constraints are law** — memories/constraints.md cannot be overridden

## File-Based Communication Protocol

```
reviews/
├── JUDGE_001_REVIEW.md           # Judge reviews
├── STATISTICIAN_001_REVIEW.md    # Statistician reviews
├── ILLUSTRATOR_001_REVIEW.md     # Illustrator reviews
├── EDITOR_001_REVIEW.md          # Editor reviews
├── USER_REVIEW.md                # ← User drops live instructions here
├── USER_REVIEW_20260226.md       # Archived past user reviews
└── WORKER_BLOCKED.md             # Worker signals when blocked

work-progress/
├── plan.md                       # Living document: paper blueprint
└── progress.md                   # Worker updates to trigger reviews
```

## Worker Priority System

```
PRIORITY 0: USER REVIEW (from USER_REVIEW.md) — overrides everything
PRIORITY 1: Judge CRITICAL (wrong equations, methodology errors, shortcuts detected)
PRIORITY 2: Statistician CRITICAL (statistical errors, missing uncertainty)
PRIORITY 3: Editor CRITICAL (LaTeX compilation, blocking issues)
PRIORITY 4: Illustrator CRITICAL (figures fundamentally misleading)
PRIORITY 5: Judge/Statistician HIGH items
PRIORITY 6: Editor/Illustrator HIGH items
PRIORITY 7: All MEDIUM items
THEN: Continue writing unfinished sections from plan.md
```

## Safety Red Lines

1. **No fake data** — fabricating results is scientific fraud
2. **No shortcut substitutions** — analytical model where experiment required = fraud
3. **No fabricated references** — every citation must be real and verifiable
4. **No force push** — ever
5. **No credential leaks** — API keys, tokens, passwords never in commits
6. **No plagiarism** — all text must be original academic prose
7. **Template fidelity** — use the journal's exact document class and options

## Hardware Resources

Detect available CPU cores at runtime. Reserve 2 cores for OS and agent processes.
Use the rest for computation:
- **Python multiprocessing**: `Pool(N)` for parallel tasks
- **NumPy/MKL threading**: `OMP_NUM_THREADS=N`, `MKL_NUM_THREADS=N`
- **ML training (PyTorch)**: `torch.set_num_threads(N)`
- **Simulation solvers**: Use available cores for parallel runs
- **LaTeX compilation**: Single-threaded (fast enough)

## Technology Stack

### Paper Production
- **LaTeX** — Document preparation (pdflatex + bibtex)
- **Python** — Data processing, experiments, figure generation
- **Matplotlib** — Publication-quality figures (with plotting_utils.py)

### Quality Assurance (Programmatic — NOT Visual)
- **tools/layout_analyzer.py** — Automated PDF layout defect detection
- **tools/figure_inspector.py** — Automated figure quality analysis
- **FIGURE_QUALITY_STANDARDS.md** — Textual vision: detailed descriptions of competitor figures

### Orchestration
- **Claude Code** — Agent runtime (claude CLI)
- **psutil** — Resource monitoring

### Infrastructure
- **Git + GitHub** — Version control and backup
- **poppler-utils** — PDF to PNG conversion (pdftoppm)
- **texlive** — LaTeX compilation

## Directory Convention

```
├── work-progress/
│   ├── plan.md                    # Paper blueprint (living document)
│   └── progress.md                # Worker signals for review
├── paper/
│   ├── main.tex                   # The paper
│   ├── references.bib             # Bibliography
│   ├── figures/                   # Output figures (PDF + PNG)
│   └── page_images/               # Rendered page PNGs (auto-generated)
├── code/
│   ├── data_processing/
│   ├── models/
│   ├── analysis/
│   ├── figures/                   # One script per figure
│   ├── validation/
│   ├── results/
│   └── utils/
│       └── plotting_utils.py      # Shared plotting settings
├── related-papers/
│   ├── README.md                  # Reference paper list
│   ├── FIGURE_QUALITY_STANDARDS.md
│   └── *.pdf                      # Downloaded reference papers
├── reviews/
│   ├── JUDGE_*.md
│   ├── STATISTICIAN_*.md
│   ├── ILLUSTRATOR_*.md
│   ├── EDITOR_*.md
│   └── USER_REVIEW.md             # User instructions (drop here)
├── publishing-guide/
│   └── template.tex               # Journal's official template
└── logs/
    ├── WORKER.log
    ├── JUDGE.log
    ├── STATISTICIAN.log
    ├── ILLUSTRATOR.log
    └── EDITOR.log
```
