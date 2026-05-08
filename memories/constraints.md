# Constraints — IMMUTABLE

These constraints CANNOT be overridden by any agent. They are absolute law.

## Scientific Integrity
1. **NO fake data** — Every result must come from real computation or real experiments
2. **NO shortcut substitutions** — If plan.md says experiment/simulation, RUN it
3. **NO fabricated references** — Every citation must be real and verifiable
4. **NO plagiarism** — All text must be original academic prose

## Paper Quality
5. **35-page hard limit** — Content pages excluding references must not exceed 35
6. **Journal template fidelity** — Use the exact documentclass and options from the journal's template
7. **Figure sophistication** — Match the target journal's quality standards; no simple bar charts for top journals

## Operational Safety
8. **No force push** — Ever, on any branch
9. **No credential leaks** — API keys, tokens, passwords never appear in commits
10. **No destructive git operations** — No reset --hard, no branch -D without user approval

## Experiment Requirements
11. **Experiments must actually run** — If plan.md specifies a simulation, ML training, or computational experiment, the Worker MUST actually run it, even if it takes hours
12. **No analytical substitutions** — Workers are FORBIDDEN from replacing required experiments with analytical/engineering approximations unless plan.md explicitly allows it
13. **Experiment outputs must exist** — Output files, logs, and results must be present as evidence

## Hardware Resources
14. **Auto-detect CPU cores** — Use `os.cpu_count()` and reserve 2 for OS/agents
15. **Parallel computation** — Use multiprocessing for batch tasks, set thread counts for numpy/MKL
16. **Never use ALL cores** — Always reserve at least 2 for the OS and agent processes

## Budget
17. **Model selection** — Use Opus for strategic/review agents, Sonnet for illustrator
18. **Token efficiency** — Reviewers only run when Worker signals progress (no idle token burn)
