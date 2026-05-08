#!/usr/bin/env python3
"""
AI Agent-Aided Research System — Serial Agent Orchestrator (Watcher)

The Watcher is the heart of the system. It runs agents in a fixed rotation,
monitors progress, handles credit errors, and maintains state across restarts.

Serial rotation:
    Worker -> Judge -> Worker -> Statistician -> Worker -> Editor -> Worker -> Illustrator
    (then repeats)

The Worker is the only agent that produces work (code, figures, LaTeX).
Reviewers (Judge, Statistician, Editor, Illustrator) evaluate and score.
The cycle continues until all four reviewer scores reach >= 8/10.

Usage:
    python watcher.py                   # start from scratch or resume
    python watcher.py --reset           # start fresh (clears state)
    python watcher.py --step 3          # resume from specific step
    python watcher.py --dry-run         # print rotation without running
"""

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import textwrap
import time
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Optional dependencies
# ---------------------------------------------------------------------------

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class Config:
    """Tunable parameters for the watcher."""

    # Timeouts (minutes)
    AGENT_TIMEOUT_MIN = 18       # reviewers: Judge, Statistician, Illustrator
    EDITOR_TIMEOUT_MIN = 60      # Editor gets more time (layout analysis + writing)
    WORKER_TIMEOUT_MIN = 240     # Worker: 4 hours for long experiments

    # Cooldown and polling
    COOLDOWN_SEC = 15            # pause between agents
    POLL_SEC = 5                 # subprocess poll interval
    DASHBOARD_SEC = 30           # dashboard print interval

    # Models
    WORKER_MODEL = "claude-opus-4-6"
    JUDGE_MODEL = "claude-opus-4-6"
    STATISTICIAN_MODEL = "claude-opus-4-6"
    EDITOR_MODEL = "claude-opus-4-6"
    ILLUSTRATOR_MODEL = "claude-sonnet-4-20250514"
    CLI_FALLBACK_MODEL = "sonnet"

    # Max turns
    WORKER_MAX_TURNS = 200
    REVIEWER_MAX_TURNS = 50

    # Score threshold for "paper is ready"
    SCORE_THRESHOLD = 8

    # Credit / rate limit error patterns
    CREDIT_ERROR_PATTERNS = [
        "rate_limit_error",
        "quota_exceeded",
        "overloaded_error",
        "insufficient_quota",
        "rate limit",
        "too many requests",
        "billing",
        "credit",
        "capacity",
        "529",
        "APIError",
    ]

    # Fast-exit heuristic: if agent exits in < this many seconds on run > 1,
    # it is likely a credit error even without explicit message
    FAST_EXIT_SEC = 30


# ---------------------------------------------------------------------------
# Paths (all relative to repo root)
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent

PAPER_DIR = ROOT / "paper"
REVIEW_DIR = ROOT / "reviews"
CODES_DIR = ROOT / "code"
PROGRESS_DIR = ROOT / "work-progress"
LOG_DIR = ROOT / "logs"
MEMORIES_DIR = ROOT / "memories"
TOOLS_DIR = ROOT / "tools"

STATE_FILE = ROOT / "watcher_state.json"

# Serial rotation
SERIAL_ORDER = [
    "worker",
    "judge",
    "worker",
    "statistician",
    "worker",
    "editor",
    "worker",
    "illustrator",
]


# ---------------------------------------------------------------------------
# Resource Monitor
# ---------------------------------------------------------------------------

class ResourceMonitor:
    """Check system resource availability."""

    @staticmethod
    def get_status() -> dict:
        """Return current resource usage."""
        status = {}
        if HAS_PSUTIL:
            status["cpu_percent"] = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()
            status["ram_total_gb"] = round(mem.total / (1024**3), 1)
            status["ram_used_gb"] = round(mem.used / (1024**3), 1)
            status["ram_percent"] = mem.percent
            disk = psutil.disk_usage(str(ROOT))
            status["disk_free_gb"] = round(disk.free / (1024**3), 1)
            status["disk_percent"] = disk.percent
        else:
            status["note"] = "psutil not installed — no resource monitoring"
        return status

    @staticmethod
    def is_healthy() -> tuple[bool, str]:
        """Check if resources are sufficient to run an agent."""
        if not HAS_PSUTIL:
            return True, "psutil not available — assuming healthy"
        mem = psutil.virtual_memory()
        if mem.percent > 95:
            return False, f"RAM critically high: {mem.percent}%"
        disk = psutil.disk_usage(str(ROOT))
        if disk.free < 500 * 1024 * 1024:  # < 500 MB free
            return False, f"Disk space low: {disk.free // (1024**2)} MB free"
        return True, "OK"


# ---------------------------------------------------------------------------
# Project Tracker
# ---------------------------------------------------------------------------

class ProjectTracker:
    """Track project file changes and review scores."""

    def __init__(self):
        self._mtimes: dict[str, float] = {}
        self.scores: dict[str, int | None] = {
            "judge": None,
            "statistician": None,
            "editor": None,
            "illustrator": None,
        }

    def snapshot_mtimes(self, directory: Path) -> dict[str, float]:
        """Record modification times for all files in a directory."""
        mtimes = {}
        if directory.exists():
            for f in directory.iterdir():
                if f.is_file():
                    mtimes[str(f)] = f.stat().st_mtime
        return mtimes

    def has_changed(self, directory: Path) -> bool:
        """Check if any file in directory has changed since last snapshot."""
        key = str(directory)
        current = self.snapshot_mtimes(directory)
        if key not in self._mtimes:
            self._mtimes[key] = current
            return True  # first check — treat as changed
        old = self._mtimes.get(key, {})
        changed = current != old
        self._mtimes[key] = current
        return changed

    def scan_reviews(self):
        """Parse all review files for Score: X/10 patterns."""
        if not REVIEW_DIR.exists():
            return

        for role in self.scores:
            prefix = role.upper()
            reviews = sorted(REVIEW_DIR.glob(f"{prefix}_*_REVIEW.md"))
            if reviews:
                latest = reviews[-1]
                score = self._extract_score(latest)
                if score is not None:
                    self.scores[role] = score

    @staticmethod
    def _extract_score(review_path: Path) -> int | None:
        """Extract Score: X/10 from a review file."""
        try:
            content = review_path.read_text(encoding="utf-8", errors="replace")
            # Look for "Score: X/10" pattern
            match = re.search(r"Score:\s*(\d+)\s*/\s*10", content)
            if match:
                return int(match.group(1))
        except Exception:
            pass
        return None

    def get_latest_review_number(self, role: str) -> int:
        """Get the highest review number for a role (e.g., JUDGE_003 -> 3)."""
        prefix = role.upper()
        reviews = sorted(REVIEW_DIR.glob(f"{prefix}_*_REVIEW.md"))
        if not reviews:
            return 0
        # Extract number from filename like JUDGE_003_REVIEW.md
        match = re.search(r"_(\d+)_REVIEW", reviews[-1].name)
        return int(match.group(1)) if match else 0

    def all_scores_above_threshold(self, threshold: int = Config.SCORE_THRESHOLD) -> bool:
        """Check if all reviewer scores are >= threshold."""
        for role, score in self.scores.items():
            if score is None or score < threshold:
                return False
        return True

    def has_user_review(self) -> bool:
        """Check if USER_REVIEW.md exists (not archived)."""
        return (REVIEW_DIR / "USER_REVIEW.md").exists()


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class Agent:
    """
    Wraps a Claude CLI subprocess with streaming JSON output parsing,
    session persistence, log writing, and credit error detection.
    """

    def __init__(
        self,
        role: str,
        prompt: str,
        model: str,
        max_turns: int,
        timeout_min: int,
        session_id: str | None = None,
    ):
        self.role = role
        self.prompt = prompt
        self.model = model
        self.max_turns = max_turns
        self.timeout_sec = timeout_min * 60
        self.session_id = session_id

        self.process: subprocess.Popen | None = None
        self.log_path = LOG_DIR / f"{role.upper()}.log"
        self.start_time: float = 0
        self.exit_code: int | None = None
        self.credit_error: bool = False
        self.timed_out: bool = False
        self._output_lines: list[str] = []

    def start(self):
        """Launch the Claude CLI subprocess."""
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        cmd = [
            "claude",
            "--dangerously-skip-permissions",
            "--output-format", "stream-json",
            "--verbose",
            "--max-turns", str(self.max_turns),
            "--model", self.model,
        ]

        if self.session_id:
            cmd.extend(["--resume", self.session_id])
            cmd.extend(["-p", self.prompt])
        else:
            cmd.extend(["-p", self.prompt])

        # Remove CLAUDECODE env var to avoid nested session errors
        env = os.environ.copy()
        env.pop("CLAUDECODE", None)

        self.start_time = time.time()

        self.process = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            bufsize=1,
        )

        _log(f"[{self.role}] Started PID={self.process.pid} model={self.model}")

    def poll(self) -> bool:
        """
        Check if the process is still running. Read available output.
        Returns True if still running, False if done.
        """
        if self.process is None:
            return False

        # Read any available output (non-blocking via poll + readline)
        retcode = self.process.poll()

        if retcode is not None:
            # Process has finished — drain remaining output
            if self.process.stdout:
                remaining = self.process.stdout.read()
                if remaining:
                    self._process_output(remaining)
            self.exit_code = retcode
            self._check_credit_error()
            return False

        return True

    def elapsed(self) -> float:
        """Seconds since agent started."""
        return time.time() - self.start_time if self.start_time else 0

    def has_exceeded_timeout(self) -> bool:
        """Check if agent has exceeded its timeout."""
        return self.elapsed() > self.timeout_sec

    def kill(self):
        """Terminate the agent subprocess."""
        if self.process and self.process.poll() is None:
            _log(f"[{self.role}] Killing PID={self.process.pid}")
            try:
                self.process.terminate()
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
            self.timed_out = True

    def extract_session_id(self) -> str | None:
        """
        Try to extract a session ID from the agent output.
        Claude CLI outputs session info in stream-json format.
        """
        for line in self._output_lines:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                # The session_id appears in the initial message
                if isinstance(data, dict):
                    sid = data.get("session_id")
                    if sid:
                        return sid
            except (json.JSONDecodeError, KeyError):
                continue
        return None

    def _process_output(self, text: str):
        """Process output text: store lines, write to log."""
        lines = text.splitlines()
        self._output_lines.extend(lines)

        # Append to log file
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                timestamp = datetime.now().strftime("%H:%M:%S")
                for line in lines:
                    f.write(f"[{timestamp}] {line}\n")
        except Exception:
            pass

    def _check_credit_error(self):
        """Check if exit was due to credit/rate limit errors."""
        if self.exit_code == 0:
            self.credit_error = False
            return

        # Check output for credit error patterns
        full_output = "\n".join(self._output_lines).lower()
        for pattern in Config.CREDIT_ERROR_PATTERNS:
            if pattern.lower() in full_output:
                self.credit_error = True
                _log(f"[{self.role}] Credit error detected: matched '{pattern}'")
                return

        # Fast-exit heuristic
        if self.elapsed() < Config.FAST_EXIT_SEC and self.start_time > 0:
            self.credit_error = True
            _log(f"[{self.role}] Fast exit ({self.elapsed():.0f}s) — likely credit error")


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def _build_worker_prompt(tracker: ProjectTracker) -> str:
    """Build the Worker agent prompt."""
    review_context = _gather_latest_reviews()
    user_review = ""
    user_review_path = REVIEW_DIR / "USER_REVIEW.md"
    if user_review_path.exists():
        user_review = user_review_path.read_text(encoding="utf-8", errors="replace")

    prompt = textwrap.dedent(f"""\
        You are the Worker — the primary researcher and author.

        Read CLAUDE.md for your full system instructions, team architecture,
        and safety red lines.

        YOUR PRIORITY SYSTEM (follow strictly):
        PRIORITY 0: USER REVIEW — read reviews/USER_REVIEW.md first. If it exists,
                     address ALL items in it before anything else.
        PRIORITY 1: Judge CRITICAL items (wrong equations, methodology errors)
        PRIORITY 2: Statistician CRITICAL items (statistical errors)
        PRIORITY 3: Editor CRITICAL items (LaTeX compilation, blocking issues)
        PRIORITY 4: Illustrator CRITICAL items (fundamentally misleading figures)
        PRIORITY 5-7: HIGH then MEDIUM items from all reviewers
        THEN: Continue writing unfinished sections from work-progress/plan.md

        CURRENT REVIEW CONTEXT:
        {review_context if review_context else "(No reviews yet — start from plan.md)"}

        {f"USER REVIEW (PRIORITY 0):{chr(10)}{user_review}" if user_review else ""}

        WORKFLOW:
        1. Read work-progress/plan.md for the research plan and experiment contract
        2. Read work-progress/progress.md for current status
        3. Address review items by priority
        4. Write code in code/ — use code/utils/plotting_utils.py for all figures
        5. Generate figures: save to paper/figures/ as PDF + PNG
        6. Write LaTeX in paper/main.tex
        7. Update work-progress/progress.md when you complete significant work
        8. If blocked, write reviews/WORKER_BLOCKED.md explaining what you need

        RULES:
        - Every figure from REAL computation — no fake data
        - Import and use plotting_utils.py for consistent styling
        - Run your code and verify outputs before moving on
        - Commit meaningful changes to git with descriptive messages
    """)
    return prompt


def _build_reviewer_prompt(role: str, tracker: ProjectTracker) -> str:
    """Build a reviewer agent prompt (Judge, Statistician, Illustrator)."""
    review_num = tracker.get_latest_review_number(role) + 1
    review_file = f"{role.upper()}_{review_num:03d}_REVIEW.md"

    personas = {
        "judge": (
            "the Judge — the devil's advocate and technical reviewer",
            "Charlie Munger",
            textwrap.dedent("""\
                Your job: find reasons this paper will be REJECTED.
                Evaluate on four axes:
                1. NOVELTY — Is the contribution genuinely new?
                2. TECHNICAL DEPTH — Are the methods rigorous?
                3. CONTRIBUTION — Does this advance the field?
                4. RELEVANCY — Is this appropriate for the target journal?

                Anti-shortcut detection:
                - Does the code ACTUALLY run the experiments described in the paper?
                - Are figures generated from real data or fabricated?
                - Did the Worker take shortcuts the plan forbids?

                Your default starting score is 4/10. The Worker must EARN higher scores.
                Find NEW issues every review — do not repeat old critiques.
            """),
        ),
        "statistician": (
            "the Statistician — guardian of statistical rigor",
            "Ronald Fisher",
            textwrap.dedent("""\
                Your job: ensure every claim is statistically defensible.
                Check:
                1. EXPERIMENTAL DESIGN — proper controls, sample sizes
                2. UNCERTAINTY — error bars, confidence intervals, propagation
                3. CONVERGENCE — grid/mesh independence, iterative convergence
                4. COMPARISONS — proper statistical tests, not just eyeballing

                No claim without proper evidence. "The results show improvement"
                is not acceptable without quantified confidence.
            """),
        ),
        "illustrator": (
            "the Illustrator — master of visual communication",
            "Edward Tufte",
            textwrap.dedent("""\
                Your job: ensure every figure earns its place in the paper.
                Apply Tufte's principles:
                1. DATA-INK RATIO — minimize non-data ink
                2. CHARTJUNK — remove decorative elements
                3. SMALL MULTIPLES — use panels effectively
                4. VISUAL CLARITY — can a reader extract the key message in 5 seconds?

                Check each figure script in code/figures/ and each rendered
                figure in paper/figures/. Use tools/figure_inspector.py for
                automated analysis. Your review should cite specific figures
                and provide actionable improvement instructions.
            """),
        ),
    }

    title, persona, specific = personas[role]

    prompt = textwrap.dedent(f"""\
        You are {title}.
        Persona: {persona}.

        Read CLAUDE.md for your full system instructions.

        {specific}

        INSTRUCTIONS:
        1. Read work-progress/plan.md for the research plan
        2. Read work-progress/progress.md for current status
        3. Read ALL previous reviews in reviews/ (including other reviewers')
        4. Review the current state of paper/main.tex
        5. Review code in code/ for correctness
        6. Write your review to reviews/{review_file}

        REVIEW FORMAT:
        ```
        # {role.upper()} Review #{review_num:03d}

        Date: [today's date]

        ## Overall Assessment
        [2-3 sentence summary]

        ## Score: X/10

        ## Critical Issues
        - [issues that MUST be fixed]

        ## High Priority
        - [important improvements]

        ## Medium Priority
        - [nice-to-have improvements]

        ## Acknowledged Progress
        - [what improved since last review]
        ```

        RULES:
        - Do NOT modify code or LaTeX — only write your review file
        - Be specific and actionable — "improve figure" is useless, "in fig 3, add error bars to the baseline comparison" is useful
        - Find NEW issues — do not repeat items already addressed
        - Score honestly: 1-3 = major problems, 4-6 = significant work needed, 7-8 = good with minor issues, 9-10 = publication ready
    """)
    return prompt


def _build_editor_prompt(tracker: ProjectTracker) -> str:
    """Build the Editor agent prompt."""
    review_num = tracker.get_latest_review_number("editor") + 1
    review_file = f"EDITOR_{review_num:03d}_REVIEW.md"

    prompt = textwrap.dedent(f"""\
        You are the Editor — guardian of writing quality and LaTeX integrity.
        Persona: William Strunk Jr. — "Omit needless words."

        Read CLAUDE.md for your full system instructions.

        YOUR WORKFLOW:
        1. Run layout analysis: python tools/layout_analyzer.py
           Read the resulting paper/layout_report.md
        2. Read work-progress/plan.md for research direction
        3. Read work-progress/progress.md for current status
        4. Read ALL previous reviews in reviews/
        5. Carefully review paper/main.tex for:
           - Writing clarity and conciseness
           - LaTeX compilation correctness
           - Reference integrity (all \\cite match references.bib)
           - Figure/table placement and referencing
           - Section flow and logical structure
           - Adherence to target journal style
        6. Write your review to reviews/{review_file}
        7. Commit all changes to git with a descriptive message

        EDITOR-SPECIFIC RULES:
        - You MAY fix minor LaTeX errors directly (typos, broken references)
        - You MAY restructure sections for better flow
        - You MUST NOT change scientific content (that is the Worker's job)
        - You MUST NOT change figure content (Illustrator's domain)
        - You MUST verify the paper compiles: cd paper && pdflatex main.tex
        - Keep the paper under 35 pages (hard limit)
        - Use active voice, present tense for established facts
        - Every paragraph should have a clear topic sentence

        REVIEW FORMAT:
        ```
        # EDITOR Review #{review_num:03d}

        Date: [today's date]

        ## Overall Assessment
        [2-3 sentences on writing quality]

        ## Score: X/10

        ## LaTeX Issues
        - [compilation errors, missing references]

        ## Layout Issues
        - [from layout_report.md]

        ## Writing Issues
        - [clarity, conciseness, structure]

        ## Changes Made
        - [list of direct fixes applied]
        ```
    """)
    return prompt


def _gather_latest_reviews() -> str:
    """Collect the most recent review from each reviewer role."""
    sections = []
    for role in ["judge", "statistician", "editor", "illustrator"]:
        prefix = role.upper()
        reviews = sorted(REVIEW_DIR.glob(f"{prefix}_*_REVIEW.md"))
        if reviews:
            latest = reviews[-1]
            try:
                content = latest.read_text(encoding="utf-8", errors="replace")
                # Truncate if very long
                if len(content) > 3000:
                    content = content[:3000] + "\n\n[... truncated ...]"
                sections.append(f"--- Latest {role.upper()} review ({latest.name}) ---\n{content}")
            except Exception:
                pass
    return "\n\n".join(sections) if sections else ""


# ---------------------------------------------------------------------------
# Maintenance tasks (run during credit pauses)
# ---------------------------------------------------------------------------

def run_maintenance():
    """Run maintenance tasks during credit error pauses."""
    _log("[maintenance] Running maintenance tasks...")

    # 1. Layout analysis
    layout_script = TOOLS_DIR / "layout_analyzer.py"
    if layout_script.exists():
        _log("[maintenance] Running layout analyzer...")
        try:
            subprocess.run(
                [sys.executable, str(layout_script)],
                cwd=str(ROOT),
                timeout=120,
                capture_output=True,
            )
        except Exception as e:
            _log(f"[maintenance] Layout analyzer error: {e}")

    # 2. Figure inspector
    fig_script = TOOLS_DIR / "figure_inspector.py"
    if fig_script.exists():
        _log("[maintenance] Running figure inspector...")
        try:
            subprocess.run(
                [sys.executable, str(fig_script), "--all"],
                cwd=str(ROOT),
                timeout=120,
                capture_output=True,
            )
        except Exception as e:
            _log(f"[maintenance] Figure inspector error: {e}")

    # 3. LaTeX compilation check
    tex_file = PAPER_DIR / "main.tex"
    if tex_file.exists():
        _log("[maintenance] Compiling LaTeX...")
        try:
            subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
                cwd=str(PAPER_DIR),
                timeout=60,
                capture_output=True,
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

def save_state(step: int, cycle: int, session_ids: dict, extra: dict | None = None):
    """Save watcher state to JSON."""
    state = {
        "step": step,
        "cycle": cycle,
        "session_ids": session_ids,
        "timestamp": datetime.now().isoformat(),
        "serial_order": SERIAL_ORDER,
    }
    if extra:
        state.update(extra)
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def load_state() -> dict | None:
    """Load watcher state from JSON. Returns None if no state file."""
    if not STATE_FILE.exists():
        return None
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, Exception) as e:
        _log(f"[state] Error loading state: {e}")
        return None


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

def print_dashboard(
    step: int,
    cycle: int,
    current_role: str,
    agent: Agent | None,
    tracker: ProjectTracker,
    resources: dict,
):
    """Print a status dashboard to stdout."""
    now = datetime.now().strftime("%H:%M:%S")
    elapsed = f"{agent.elapsed():.0f}s" if agent else "N/A"
    timeout = f"{agent.timeout_sec}s" if agent else "N/A"

    lines = [
        "",
        f"{'='*60}",
        f"  WATCHER DASHBOARD  |  {now}  |  Cycle {cycle}  Step {step}",
        f"{'='*60}",
        f"  Current: {current_role.upper():<15} Elapsed: {elapsed:<10} Timeout: {timeout}",
        f"  Rotation: {' -> '.join(r.upper() if r != current_role else f'[{r.upper()}]' for r in SERIAL_ORDER)}",
        f"",
        f"  SCORES:",
    ]

    for role, score in tracker.scores.items():
        score_str = f"{score}/10" if score is not None else "---"
        bar = ""
        if score is not None:
            filled = score
            empty = 10 - score
            bar = f"  [{'#' * filled}{'.' * empty}]"
        lines.append(f"    {role:<15} {score_str:<8}{bar}")

    if tracker.all_scores_above_threshold():
        lines.append(f"")
        lines.append(f"  *** ALL SCORES >= {Config.SCORE_THRESHOLD} — PAPER MAY BE READY ***")

    if resources:
        lines.append(f"")
        lines.append(f"  RESOURCES:")
        if "cpu_percent" in resources:
            lines.append(f"    CPU: {resources['cpu_percent']}%")
        if "ram_percent" in resources:
            lines.append(
                f"    RAM: {resources['ram_used_gb']:.1f}/{resources['ram_total_gb']:.1f} GB "
                f"({resources['ram_percent']}%)"
            )
        if "disk_free_gb" in resources:
            lines.append(f"    Disk free: {resources['disk_free_gb']:.1f} GB")

    if tracker.has_user_review():
        lines.append(f"")
        lines.append(f"  ** USER_REVIEW.md detected — Worker will address it next **")

    lines.append(f"{'='*60}")
    lines.append("")

    print("\n".join(lines), flush=True)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _log(msg: str):
    """Log a message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)

    # Also write to watcher log
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_DIR / "WATCHER.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# WatcherSerial — Main Orchestrator
# ---------------------------------------------------------------------------

class WatcherSerial:
    """
    Serial agent orchestrator. Runs agents one at a time in the fixed
    SERIAL_ORDER rotation, handling state persistence, credit errors,
    user reviews, and progress tracking.
    """

    def __init__(self, start_step: int = 0, start_cycle: int = 0):
        self.step = start_step
        self.cycle = start_cycle
        self.session_ids: dict[str, str] = {}
        self.tracker = ProjectTracker()
        self.running = True
        self.current_agent: Agent | None = None
        self._run_count: dict[str, int] = {}  # track runs per role for fast-exit heuristic

        # Ensure directories exist
        for d in [REVIEW_DIR, LOG_DIR, PROGRESS_DIR, PAPER_DIR / "figures", MEMORIES_DIR]:
            d.mkdir(parents=True, exist_ok=True)

    def _get_role(self) -> str:
        """Get the current role from the serial order."""
        return SERIAL_ORDER[self.step % len(SERIAL_ORDER)]

    def _get_model(self, role: str) -> str:
        """Get the model for a given role."""
        models = {
            "worker": Config.WORKER_MODEL,
            "judge": Config.JUDGE_MODEL,
            "statistician": Config.STATISTICIAN_MODEL,
            "editor": Config.EDITOR_MODEL,
            "illustrator": Config.ILLUSTRATOR_MODEL,
        }
        return models.get(role, Config.WORKER_MODEL)

    def _get_timeout(self, role: str) -> int:
        """Get the timeout (minutes) for a given role."""
        if role == "worker":
            return Config.WORKER_TIMEOUT_MIN
        elif role == "editor":
            return Config.EDITOR_TIMEOUT_MIN
        else:
            return Config.AGENT_TIMEOUT_MIN

    def _get_max_turns(self, role: str) -> int:
        """Get max turns for a given role."""
        return Config.WORKER_MAX_TURNS if role == "worker" else Config.REVIEWER_MAX_TURNS

    def _build_prompt(self, role: str) -> str:
        """Build the prompt for the given role."""
        if role == "worker":
            return _build_worker_prompt(self.tracker)
        elif role == "editor":
            return _build_editor_prompt(self.tracker)
        else:
            return _build_reviewer_prompt(role, self.tracker)

    def _should_force_worker(self, next_role: str) -> bool:
        """
        Check if we should force a Worker run instead of the scheduled role.
        This happens when USER_REVIEW.md exists and next agent is not Worker.
        """
        if next_role == "worker":
            return False
        return self.tracker.has_user_review()

    def _run_layout_analyzer(self):
        """Run the layout analyzer before Editor turns."""
        layout_script = TOOLS_DIR / "layout_analyzer.py"
        if not layout_script.exists():
            return
        _log("[pre-editor] Running layout analyzer...")
        try:
            subprocess.run(
                [sys.executable, str(layout_script)],
                cwd=str(ROOT),
                timeout=120,
                capture_output=True,
            )
            _log("[pre-editor] Layout analysis complete.")
        except Exception as e:
            _log(f"[pre-editor] Layout analyzer error: {e}")

    def _wait_for_credit_recovery(self):
        """
        Wait during a credit/rate limit error. Run maintenance tasks,
        then wait with exponential backoff.
        """
        _log("[credit] Rate limit or credit error detected. Running maintenance...")
        run_maintenance()

        # Wait with backoff: 2, 4, 8, 16 minutes (max)
        wait_minutes = 2
        max_wait = 16
        while self.running:
            _log(f"[credit] Waiting {wait_minutes} minutes before retry...")
            for _ in range(wait_minutes * 60 // 5):
                if not self.running:
                    return
                time.sleep(5)

            _log("[credit] Attempting to resume...")
            break  # Let the main loop retry

    def _advance_step(self):
        """Advance to the next step in the rotation."""
        self.step += 1
        if self.step % len(SERIAL_ORDER) == 0:
            self.cycle += 1
            _log(f"[cycle] Completed cycle {self.cycle - 1}, starting cycle {self.cycle}")

    def run(self):
        """Main orchestrator loop."""
        _log("=" * 60)
        _log("  AI Agent-Aided Research System — Watcher Started")
        _log(f"  Step: {self.step}  Cycle: {self.cycle}")
        _log(f"  Rotation: {' -> '.join(r.upper() for r in SERIAL_ORDER)}")
        _log("=" * 60)

        # Register signal handlers for graceful shutdown
        def handle_signal(signum, frame):
            _log(f"[signal] Received signal {signum}, shutting down...")
            self.running = False
            if self.current_agent:
                self.current_agent.kill()

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        # Initial scan
        self.tracker.scan_reviews()

        while self.running:
            # --- 1. Pick next agent ---
            role = self._get_role()

            # --- 2. Check for USER_REVIEW.md override ---
            if self._should_force_worker(role):
                _log(f"[override] USER_REVIEW.md detected — forcing Worker instead of {role}")
                role = "worker"

            # --- 3. Resource check ---
            healthy, reason = ResourceMonitor.is_healthy()
            if not healthy:
                _log(f"[resources] Unhealthy: {reason}. Waiting 60s...")
                time.sleep(60)
                continue

            # --- 4. Save state ---
            save_state(self.step, self.cycle, self.session_ids)

            # --- 5. Pre-Editor layout analysis ---
            if role == "editor":
                self._run_layout_analyzer()

            # --- 6. Build prompt and create agent ---
            prompt = self._build_prompt(role)
            model = self._get_model(role)
            timeout = self._get_timeout(role)
            max_turns = self._get_max_turns(role)
            session_id = self.session_ids.get(role)

            agent = Agent(
                role=role,
                prompt=prompt,
                model=model,
                max_turns=max_turns,
                timeout_min=timeout,
                session_id=session_id,
            )
            self.current_agent = agent

            # --- 7. Start agent ---
            _log(f"[{role}] Starting (model={model}, timeout={timeout}min, max_turns={max_turns})")
            agent.start()
            self._run_count[role] = self._run_count.get(role, 0) + 1

            # --- 8. Wait for completion ---
            last_dashboard = time.time()
            resources = ResourceMonitor.get_status()

            while agent.poll():
                if not self.running:
                    agent.kill()
                    break

                # Check timeout
                if agent.has_exceeded_timeout():
                    _log(f"[{role}] Timeout after {agent.elapsed():.0f}s")
                    agent.kill()
                    break

                # Dashboard
                now = time.time()
                if now - last_dashboard >= Config.DASHBOARD_SEC:
                    self.tracker.scan_reviews()
                    resources = ResourceMonitor.get_status()
                    print_dashboard(
                        self.step, self.cycle, role, agent, self.tracker, resources
                    )
                    last_dashboard = now

                time.sleep(Config.POLL_SEC)

            self.current_agent = None

            if not self.running:
                break

            # --- 9. Handle exit ---
            elapsed = agent.elapsed()
            _log(f"[{role}] Finished: exit_code={agent.exit_code} elapsed={elapsed:.0f}s "
                 f"credit_error={agent.credit_error} timed_out={agent.timed_out}")

            # Try to extract and save session ID
            new_session_id = agent.extract_session_id()
            if new_session_id:
                self.session_ids[role] = new_session_id

            # Credit error handling
            if agent.credit_error:
                self._wait_for_credit_recovery()
                continue  # retry same step

            # Scan reviews after agent completes
            self.tracker.scan_reviews()

            # Check if paper is ready
            if self.tracker.all_scores_above_threshold():
                _log("")
                _log("=" * 60)
                _log("  ALL REVIEWER SCORES >= {}/10".format(Config.SCORE_THRESHOLD))
                _log("  The paper may be ready for submission!")
                _log("  Review the paper and scores before submitting.")
                _log("=" * 60)
                _log("")
                # Continue running — human makes final call

            # --- 10. Cooldown ---
            _log(f"[cooldown] Waiting {Config.COOLDOWN_SEC}s before next agent...")
            for _ in range(Config.COOLDOWN_SEC):
                if not self.running:
                    break
                time.sleep(1)

            # --- 11. Advance ---
            self._advance_step()
            save_state(self.step, self.cycle, self.session_ids)

        _log("[watcher] Shutdown complete.")
        save_state(self.step, self.cycle, self.session_ids, {"status": "stopped"})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="AI Agent-Aided Research System — Serial Agent Orchestrator",
    )
    parser.add_argument("--reset", action="store_true",
                        help="Start fresh (ignore saved state)")
    parser.add_argument("--step", type=int, default=None,
                        help="Resume from a specific step number")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print rotation and exit without running agents")
    args = parser.parse_args()

    # --- Dry run ---
    if args.dry_run:
        print("\nSerial rotation (repeats every 8 steps):\n")
        for i, role in enumerate(SERIAL_ORDER):
            timeout = Config.WORKER_TIMEOUT_MIN if role == "worker" else (
                Config.EDITOR_TIMEOUT_MIN if role == "editor" else Config.AGENT_TIMEOUT_MIN
            )
            model_map = {
                "worker": Config.WORKER_MODEL,
                "judge": Config.JUDGE_MODEL,
                "statistician": Config.STATISTICIAN_MODEL,
                "editor": Config.EDITOR_MODEL,
                "illustrator": Config.ILLUSTRATOR_MODEL,
            }
            model = model_map.get(role, "")
            turns = Config.WORKER_MAX_TURNS if role == "worker" else Config.REVIEWER_MAX_TURNS
            print(f"  Step {i}: {role.upper():<15} model={model:<30} "
                  f"timeout={timeout}min  max_turns={turns}")
        print(f"\nTotal cycle length: {len(SERIAL_ORDER)} steps")
        print(f"Score threshold for completion: {Config.SCORE_THRESHOLD}/10")
        sys.exit(0)

    # --- Load or initialize state ---
    start_step = 0
    start_cycle = 0

    if args.reset:
        _log("[init] Reset requested — starting fresh.")
        if STATE_FILE.exists():
            STATE_FILE.unlink()
    elif args.step is not None:
        start_step = args.step
        _log(f"[init] Resuming from step {start_step}")
    else:
        state = load_state()
        if state:
            start_step = state.get("step", 0)
            start_cycle = state.get("cycle", 0)
            _log(f"[init] Resuming from saved state: step={start_step} cycle={start_cycle}")
        else:
            _log("[init] No saved state — starting fresh.")

    # --- Dependency check ---
    if not HAS_PSUTIL:
        _log("[init] WARNING: psutil not installed. Resource monitoring disabled.")
        _log("[init]   Install with: pip install psutil")

    # Check claude CLI
    from shutil import which
    if not which("claude"):
        _log("[init] ERROR: 'claude' CLI not found on PATH.")
        _log("[init]   Install Claude Code: https://docs.anthropic.com/en/docs/claude-code")
        sys.exit(1)

    # --- Start watcher ---
    watcher = WatcherSerial(start_step=start_step, start_cycle=start_cycle)

    # Restore session IDs from state
    state = load_state()
    if state and "session_ids" in state:
        watcher.session_ids = state["session_ids"]

    watcher.run()


if __name__ == "__main__":
    main()
