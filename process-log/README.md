# Research Process Log

## Overview

This paper was produced using the **AI Agent-Aided Research System** — an autonomous
pipeline of 7 specialized AI agents (Director, Librarian, Worker, Judge, Statistician,
Illustrator, Editor) orchestrated by a watcher script.

> The full agent session logs are in `../logs/`. Relevant excerpts are copied here
> for the AIDER submission requirement.

## Tools Used

- AI Agent-Aided Research System (Claude Code CLI + agent orchestration)
- Python for experiments and figure generation
- LaTeX for manuscript preparation

## Workflow

1. **Problem formulation** — AI (Director agent, Feynman persona) + human input
2. **Literature review** — AI (Librarian agent, Garfield persona) + human verification
3. **Methodology development** — AI (Worker agent) + human oversight via USER_REVIEW.md
4. **Implementation** — AI (Worker agent) with Judge anti-shortcut verification
5. **Experiments** — AI (Worker agent) runs actual computations, Judge verifies
6. **Writing** — AI (Worker agent) writes LaTeX, Editor reviews style/compliance
7. **Revision** — Iterative loop: Worker addresses Judge, Statistician, Illustrator, Editor reviews

## AI Sessions

See [`ai-sessions/`](ai-sessions/) for full transcripts and logs.

Agent runtime logs are also available in the repository's `logs/` directory:
- `WORKER.log`, `JUDGE.log`, `STATISTICIAN.log`, `ILLUSTRATOR.log`, `EDITOR.log`
- `DIRECTOR.log`, `LIBRARIAN.log`

## Human Decisions

See [`human-decisions/`](human-decisions/) for a timestamped record of all significant
human interventions, including USER_REVIEW.md instructions dropped during the
production loop.
