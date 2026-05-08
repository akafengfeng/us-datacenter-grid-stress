# AI Agent-Aided Research System — Cycle Instructions

## Work Cycle

Each cycle follows this protocol:

### 1. Check Constraints (Immutable)
Read `memories/constraints.md`. These rules CANNOT be overridden by any agent.

### 2. Read Consensus
Read `memories/consensus.md` for:
- Current phase (Setup / Writing / Reviewing / Polishing)
- Next action
- Latest scores (Judge, Statistician, Illustrator, Editor)

### 3. Execute

**If Phase = Setup:**
1. Director frames the research question and novelty
2. Librarian searches literature, downloads papers, builds references
3. Together they create plan.md with an Experiment Contract
4. Update consensus.md: Phase → Writing

**If Phase = Writing/Reviewing/Polishing:**
The Watcher orchestrates the production loop automatically:

```
Worker → Judge → Worker → Statistician → Worker → Editor → Worker → Illustrator → repeat
```

### 4. Update Consensus
After each significant milestone, update `memories/consensus.md` with:
- What was accomplished
- Current scores (Judge X/10, Statistician X/10, Illustrator X/10, Editor X/10)
- Next action
- Any blockers

## Convergence Rules

| Phase | Action | Agents |
|-------|--------|--------|
| Setup | Frame question + search literature | Director, Librarian |
| Writing (cycles 1-5) | Write first draft, run experiments | Worker |
| Reviewing (cycles 6+) | Full review loop with all 4 reviewers | Judge, Statistician, Illustrator, Editor |
| Polishing | Targeted fixes from reviews | Worker + specific reviewer |

**Anti-bikeshedding:** No pure discussion cycles. Every cycle must produce:
- Code, figures, or LaTeX text (Worker)
- A scored review with actionable items (Reviewers)
- A git commit (Editor)

## Experiment Contract

plan.md MUST contain an "Experiment Contract" section listing every required
experiment/simulation with:
- Method/solver to be used
- Case description (setup, parameters, boundary conditions)
- Expected runtime estimate
- Required output (data files, figures, metrics)

The Worker MUST run every experiment in the contract. The Judge MUST verify
every experiment actually ran (check output files, logs, timestamps).

## User Intervention

The user can inject instructions at any time by writing to:
```
reviews/USER_REVIEW.md
```

When detected:
1. Current agent finishes its work
2. USER_REVIEW.md is archived with timestamp
3. Worker addresses user instructions as HIGHEST PRIORITY
4. All reviewers incorporate user concerns

## Automated Layout Analysis

Before each Editor review, the Watcher automatically runs:
```bash
python3 tools/layout_analyzer.py
```

This produces `paper/layout_report.md` with programmatic detection of:
- Per-page white space percentage
- Oversized figures
- Large gaps after floats
- Orphan headings

The Editor reads this report instead of trying to visually detect issues.

## Safety Guardrails

1. No fake data or fabricated results
2. No shortcut substitutions (analytical where experiment required)
3. No fabricated or incorrect references
4. No force push to any branch
5. No credential leaks in commits
6. No plagiarism — all text must be original
7. Journal template must be used exactly as provided
8. 35-page hard limit (excluding references)
9. Experiments listed in the Experiment Contract MUST actually run
