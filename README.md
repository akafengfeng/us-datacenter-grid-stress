# AI Agent-Aided Research System

An autonomous research pipeline that uses 7 specialized AI agents to produce
publication-ready academic papers. Fork this template to start a new paper.

Part of [AIDER — AI-Driven Energy Research](https://ai-driven-energy-research.github.io/).

## The Team

| Agent | Persona | Role | Phase |
|-------|---------|------|-------|
| **Director** | Richard Feynman | Research direction, novelty framing | Setup (once) |
| **Librarian** | Eugene Garfield | Literature search, gap verification, reference building | Setup (once) |
| **Worker** | The PhD Student | Primary author: code, experiments, figures, LaTeX | Production (loop) |
| **Judge** | Charlie Munger | Technical review, anti-shortcut detection | Production (loop) |
| **Statistician** | Ronald Fisher | Statistical rigor, uncertainty quantification | Production (loop) |
| **Illustrator** | Edward Tufte | Figure design, data-ink ratio, visual quality | Production (loop) |
| **Editor** | William Strunk Jr. | Writing clarity, LaTeX compliance, reference integrity | Production (loop) |

## How It Works

### Phase 1: Setup (One-Time)

The **Director** frames the research question and novelty. The **Librarian** searches
literature, verifies the gap, builds references, and creates figure quality benchmarks
from competitor papers.

### Phase 2: Production (Iterative Loop)

```
Worker → Judge → Worker → Statistician → Worker → Editor → Worker → Illustrator → repeat
```

The Worker does the research. Four specialized reviewers take turns critiquing it.
The loop runs until all reviewer scores reach 8+/10, at which point you decide
whether to submit.

## Quick Start

### Prerequisites

- [Claude Code CLI](https://github.com/anthropics/claude-code) installed
- Python 3.10+
- LaTeX distribution (texlive recommended)
- `poppler-utils` (for PDF analysis: `apt install poppler-utils`)

### 1. Fork This Template

Click **"Use this template"** on GitHub to create your own repository.

### 2. Set Up Your Paper

```bash
# Interactive mode (recommended):
python3 setup.py

# Or quick mode:
python3 setup.py \
    --name "my_paper" \
    --journal "Applied Energy" \
    --topic "Neural network surrogate for heat exchanger design" \
    --gap "No existing surrogate captures turbulent regime transitions" \
    --methods "Physics-informed neural network with boundary layer constraints"
```

This creates the project structure, seeds `plan.md` with your input, then runs
the Director and Librarian to complete the research plan.

### 3. Start the Production Loop

```bash
python3 watcher.py
```

The watcher orchestrates the agent rotation automatically. It runs forever until
you press Ctrl+C. Drop instructions into `reviews/USER_REVIEW.md` at any time
to redirect all agents.

## Repository Structure

```
├── CLAUDE.md                     # Master system prompt (all agents read this)
├── PROMPT.md                     # Cycle instructions
├── setup.py                      # Project setup script
├── watcher.py                    # Agent orchestrator
├── tools/                        # Quality analysis tools
│   ├── layout_analyzer.py        # PDF layout defect detection
│   ├── figure_inspector.py       # Figure quality scoring
│   └── pdf_to_pages.py           # PDF → PNG conversion
├── .claude/agents/               # Agent definitions
│   ├── director.md               # Research strategist
│   ├── librarian.md              # Literature expert
│   ├── worker.md                 # Primary author
│   ├── judge.md                  # Technical reviewer
│   ├── statistician.md           # Statistics reviewer
│   ├── illustrator.md            # Figure reviewer
│   └── editor.md                 # Writing reviewer
├── memories/                     # Cross-session state
│   ├── constraints.md            # Immutable rules
│   └── consensus.md              # Current phase and scores
├── work-progress/                # Planning and coordination
│   ├── plan.md                   # Paper blueprint (living document)
│   └── progress.md               # Worker signals for review
├── paper/                        # Manuscript
│   ├── main.tex
│   ├── references.bib
│   └── figures/
├── code/                         # All source code
│   ├── README.md
│   ├── requirements.txt
│   ├── figures/                  # One Python script per figure
│   └── utils/
│       └── plotting_utils.py     # Shared figure styling
├── data/                         # Datasets
│   └── README.md
├── related-papers/               # Literature and competitor analysis
│   └── README.md
├── reviews/                      # Agent and user reviews
│   └── USER_REVIEW.md            # Drop instructions here any time
├── publishing-guide/             # Journal template files
├── process-log/                  # AIDER submission requirement
│   ├── README.md
│   ├── ai-sessions/
│   └── human-decisions/
├── results/
│   └── reproduce.sh
├── logs/                         # Agent runtime logs
├── REPRODUCIBILITY.md
└── LICENSE
```

## User Intervention

Drop a file called `USER_REVIEW.md` into `reviews/` at any time. The watcher
detects it, archives it with a timestamp, and forces the Worker to address your
instructions as the highest priority.

## Key Features

- **Anti-shortcut enforcement**: The Judge verifies that computational experiments
  actually ran — checks output file sizes, solver logs, and timestamps
- **Textual vision**: The Librarian creates detailed textual descriptions of
  competitor paper figures (`FIGURE_QUALITY_STANDARDS.md`), giving the Worker and
  Illustrator a benchmark for journal quality
- **Programmatic quality tools**: `layout_analyzer.py` and `figure_inspector.py`
  detect layout defects and figure quality issues without relying on visual inspection
- **Rate-limit resilience**: The watcher detects API rate limits and runs local
  tasks while waiting for recovery
- **Session persistence**: Agent sessions are saved and resumed across restarts

## Submitting to AIDER

When all reviewer scores reach 8+/10:

1. Ensure `results/reproduce.sh` regenerates all figures and tables
2. Complete `REPRODUCIBILITY.md`
3. Copy agent logs from `logs/` to `process-log/ai-sessions/`
4. Document human decisions in `process-log/human-decisions/`
5. Open a [submission issue](https://github.com/ai-driven-energy-research/submissions/issues/new/choose)

## License

- **Paper** (`paper/`): CC-BY 4.0
- **Code** (`code/`): MIT License
- **Data** (`data/`): See `data/README.md`
