# Streamlit Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Streamlit web UI that wraps the existing `python -m src.cli` pipeline, with per-project step tracking that survives restarts.

**Architecture:** Streamlit app in a new top-level `ui/` package. It calls the existing CLI via `subprocess`, streams stdout into a live log, and persists step status + produced artifacts to `projects/<name>/state.json`. No changes to `src/` — the UI is a pure wrapper. Pure-logic modules (`state.py`, `runner.py`, `cli_map.py`) are unit-tested with pytest; the Streamlit view layer is smoke-tested manually.

**Tech Stack:** Python 3.10+, Streamlit, existing `src.cli` (argparse), pytest.

---

## File Structure

```
ui/
├── __init__.py
├── app.py              # Streamlit entrypoint — wires components together
├── state.py            # read/write projects/<name>/state.json + filesystem fallback
├── cli_map.py          # maps (step, options) -> exact CLI argv list
├── runner.py           # subprocess wrapper, yields output lines
└── components/
    ├── __init__.py
    ├── sidebar.py      # project list, new project, nav links
    ├── pipeline.py     # pill row + active step card
    ├── output.py       # per-step artifact viewer
    └── log.py          # live log strip
tests/ui/
├── __init__.py
├── test_state.py
├── test_cli_map.py
└── test_runner.py
```

**Responsibilities:**
- `state.py` — single source of truth for step status. Knows nothing about Streamlit or subprocess.
- `cli_map.py` — pure function: given a step name + options dict, returns the argv list to run. No I/O.
- `runner.py` — runs an argv list, yields output lines, returns exit code. No Streamlit, no state writes.
- `app.py` + `components/` — Streamlit view. Calls the three modules above.

**Pipeline steps (canonical order):** `script, narration, scenes, voiceover, storyboard, render`

**CLI command mapping (verified against `src/cli/main.py`):**

| Step | argv | Options |
|---|---|---|
| script | `python -m src.cli script <p>` | `--url <u>` or `-i <file>`, `--mock` |
| narration | `python -m src.cli narration <p>` | `--force`, `--mock` |
| scenes | `python -m src.cli scenes <p>` | `--force` |
| voiceover | `python -m src.cli voiceover <p> --provider <prov>` | `--provider edge\|mock\|elevenlabs\|manual`, `--voice <v>` |
| storyboard | `python -m src.cli storyboard <p>` | — |
| render | `python -m src.cli render <p> --resolution <r>` | `--resolution 4k\|1440p\|1080p\|720p\|480p`, `--short` (vertical), `--fast`, `--concurrency <n>` |

**Resolution presets (UI label → render flags):**

| UI label | Flags |
|---|---|
| 4K | `--resolution 4k` |
| 1080p | `--resolution 1080p` |
| 720p | `--resolution 720p` |
| Vertical 1080 | `--resolution 1080p --short` |
| Vertical 720 | `--resolution 720p --short` |

**Artifact directories per step (for state.py scanning):**

| Step | Glob |
|---|---|
| script | `projects/<p>/script/*.json` |
| narration | `projects/<p>/narration/*.json` |
| scenes | `projects/<p>/scenes/*.tsx` |
| voiceover | `projects/<p>/voiceover/*.mp3` |
| storyboard | `projects/<p>/storyboard/*.json` |
| render | `projects/<p>/output/*.mp4` |

---

### Task 1: Project scaffolding + Streamlit dependency

**Files:**
- Create: `ui/__init__.py` (empty)
- Create: `ui/components/__init__.py` (empty)
- Create: `tests/ui/__init__.py` (empty)
- Modify: `pyproject.toml` — add `ui` optional dependency group

- [ ] **Step 1: Add the ui extra to pyproject.toml**

In `pyproject.toml`, under `[project.optional-dependencies]`, add after the `whisper` group:

```toml
ui = [
    "streamlit>=1.40",
]
```

- [ ] **Step 2: Create empty package files**

Create `ui/__init__.py`, `ui/components/__init__.py`, `tests/ui/__init__.py`, each containing a single line:

```python
"""Streamlit dashboard package."""
```

- [ ] **Step 3: Install the extra**

Run: `.venv\Scripts\python.exe -m pip install -e ".[ui]"`
Expected: `Successfully installed streamlit-...`

- [ ] **Step 4: Verify streamlit imports**

Run: `.venv\Scripts\python.exe -c "import streamlit; print(streamlit.__version__)"`
Expected: prints a version >= 1.40

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml ui tests/ui
git commit -m "feat(ui): scaffold ui package and add streamlit dependency"
```

---

### Task 2: cli_map — pure step→argv mapping

**Files:**
- Create: `ui/cli_map.py`
- Test: `tests/ui/test_cli_map.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/ui/test_cli_map.py
import sys
from ui.cli_map import build_argv, STEPS, RESOLUTION_PRESETS


def test_steps_in_canonical_order():
    assert STEPS == ["script", "narration", "scenes", "voiceover", "storyboard", "render"]


def test_script_default():
    argv = build_argv("script", "demo", {})
    assert argv == [sys.executable, "-m", "src.cli", "script", "demo"]


def test_script_with_url():
    argv = build_argv("script", "demo", {"url": "https://x.com/post"})
    assert argv == [sys.executable, "-m", "src.cli", "script", "demo", "--url", "https://x.com/post"]


def test_scenes_force():
    argv = build_argv("scenes", "demo", {"force": True})
    assert argv == [sys.executable, "-m", "src.cli", "scenes", "demo", "--force"]


def test_voiceover_provider_and_voice():
    argv = build_argv("voiceover", "demo", {"provider": "edge", "voice": "en-US-AriaNeural"})
    assert argv == [sys.executable, "-m", "src.cli", "voiceover", "demo",
                    "--provider", "edge", "--voice", "en-US-AriaNeural"]


def test_render_horizontal_1080():
    argv = build_argv("render", "demo", {"resolution": "1080p"})
    assert argv == [sys.executable, "-m", "src.cli", "render", "demo", "--resolution", "1080p"]


def test_render_vertical_1080_adds_short():
    argv = build_argv("render", "demo", {"resolution": "Vertical 1080"})
    assert argv == [sys.executable, "-m", "src.cli", "render", "demo",
                    "--resolution", "1080p", "--short"]


def test_resolution_presets_labels():
    assert set(RESOLUTION_PRESETS) == {"4K", "1080p", "720p", "Vertical 1080", "Vertical 720"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/ui/test_cli_map.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ui.cli_map'`

- [ ] **Step 3: Write minimal implementation**

```python
# ui/cli_map.py
"""Pure mapping from (step, options) to a CLI argv list. No I/O."""
import sys

STEPS = ["script", "narration", "scenes", "voiceover", "storyboard", "render"]

# UI label -> (render --resolution value, add --short)
RESOLUTION_PRESETS = {
    "4K": ("4k", False),
    "1080p": ("1080p", False),
    "720p": ("720p", False),
    "Vertical 1080": ("1080p", True),
    "Vertical 720": ("720p", True),
}


def build_argv(step: str, project: str, options: dict) -> list[str]:
    """Return the argv list to run a pipeline step for a project."""
    if step not in STEPS:
        raise ValueError(f"Unknown step: {step}")
    argv = [sys.executable, "-m", "src.cli", step, project]

    if step == "script":
        if options.get("url"):
            argv += ["--url", options["url"]]
        elif options.get("input"):
            argv += ["-i", options["input"]]
        if options.get("mock"):
            argv += ["--mock"]
    elif step in ("narration", "scenes"):
        if options.get("force"):
            argv += ["--force"]
        if step == "narration" and options.get("mock"):
            argv += ["--mock"]
    elif step == "voiceover":
        if options.get("provider"):
            argv += ["--provider", options["provider"]]
        if options.get("voice"):
            argv += ["--voice", options["voice"]]
    elif step == "render":
        label = options.get("resolution", "1080p")
        value, is_short = RESOLUTION_PRESETS.get(label, ("1080p", False))
        argv += ["--resolution", value]
        if is_short:
            argv += ["--short"]
        if options.get("fast"):
            argv += ["--fast"]
        if options.get("concurrency"):
            argv += ["--concurrency", str(options["concurrency"])]

    return argv
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/ui/test_cli_map.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add ui/cli_map.py tests/ui/test_cli_map.py
git commit -m "feat(ui): add cli_map step-to-argv builder"
```

---

### Task 3: state.py — load, mutate, persist step status

**Files:**
- Create: `ui/state.py`
- Test: `tests/ui/test_state.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/ui/test_state.py
import json
from pathlib import Path
from ui import state


def _make_project(tmp_path: Path, name: str = "demo") -> Path:
    proj = tmp_path / "projects" / name
    proj.mkdir(parents=True)
    return proj


def test_fresh_state_all_pending(tmp_path):
    _make_project(tmp_path)
    s = state.load("demo", projects_dir=tmp_path / "projects")
    assert set(s) == {"script", "narration", "scenes", "voiceover", "storyboard", "render"}
    assert all(v["status"] == "pending" for v in s.values())


def test_set_running_then_done_persists(tmp_path):
    proj = _make_project(tmp_path)
    (proj / "script").mkdir()
    (proj / "script" / "script.json").write_text("{}", encoding="utf-8")

    pdir = tmp_path / "projects"
    state.set_running("demo", "script", projects_dir=pdir)
    s = state.load("demo", projects_dir=pdir)
    assert s["script"]["status"] == "running"

    state.set_done("demo", "script", projects_dir=pdir)
    s = state.load("demo", projects_dir=pdir)
    assert s["script"]["status"] == "done"
    assert s["script"]["artifacts"] == ["script/script.json"]
    assert s["script"]["completed_at"] is not None


def test_set_failed_records_error(tmp_path):
    _make_project(tmp_path)
    pdir = tmp_path / "projects"
    state.set_failed("demo", "scenes", "Undefined variable: 'floodOpacity'", projects_dir=pdir)
    s = state.load("demo", projects_dir=pdir)
    assert s["scenes"]["status"] == "failed"
    assert "floodOpacity" in s["scenes"]["error"]


def test_filesystem_fallback_when_no_state_file(tmp_path):
    proj = _make_project(tmp_path)
    (proj / "narration").mkdir()
    (proj / "narration" / "narrations.json").write_text("{}", encoding="utf-8")
    pdir = tmp_path / "projects"

    s = state.load("demo", projects_dir=pdir)
    assert s["narration"]["status"] == "done"
    assert s["script"]["status"] == "pending"
    # load() must have written a state.json so subsequent loads are stable
    assert (proj / "state.json").exists()


def test_stale_running_reset_to_failed(tmp_path):
    proj = _make_project(tmp_path)
    pdir = tmp_path / "projects"
    # write a state.json with a 'running' step but no live process
    raw = state._empty_state()
    raw["scenes"]["status"] = "running"
    (proj / "state.json").write_text(json.dumps(raw), encoding="utf-8")

    s = state.load("demo", projects_dir=pdir)
    assert s["scenes"]["status"] == "failed"
    assert "interrupted" in s["scenes"]["error"].lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/ui/test_state.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ui.state'`

- [ ] **Step 3: Write minimal implementation**

```python
# ui/state.py
"""Per-project pipeline state persisted to projects/<name>/state.json."""
import json
from datetime import datetime, timezone
from pathlib import Path

from ui.cli_map import STEPS

# step -> (output subdir, glob) used for artifact scanning + filesystem fallback
_ARTIFACT_GLOB = {
    "script": ("script", "*.json"),
    "narration": ("narration", "*.json"),
    "scenes": ("scenes", "*.tsx"),
    "voiceover": ("voiceover", "*.mp3"),
    "storyboard": ("storyboard", "*.json"),
    "render": ("output", "*.mp4"),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_state() -> dict:
    return {
        step: {"status": "pending", "completed_at": None, "artifacts": [], "error": None}
        for step in STEPS
    }


def _state_path(project: str, projects_dir: Path) -> Path:
    return Path(projects_dir) / project / "state.json"


def _scan_artifacts(project: str, step: str, projects_dir: Path) -> list[str]:
    subdir, glob = _ARTIFACT_GLOB[step]
    base = Path(projects_dir) / project / subdir
    if not base.exists():
        return []
    return sorted(f"{subdir}/{p.name}" for p in base.glob(glob))


def _derive_from_filesystem(project: str, projects_dir: Path) -> dict:
    s = _empty_state()
    for step in STEPS:
        artifacts = _scan_artifacts(project, step, projects_dir)
        if artifacts:
            s[step] = {"status": "done", "completed_at": _now(),
                       "artifacts": artifacts, "error": None}
    return s


def load(project: str, projects_dir: Path = Path("projects")) -> dict:
    """Load state; derive from filesystem if missing; reset stale 'running'."""
    path = _state_path(project, projects_dir)
    if not path.exists():
        s = _derive_from_filesystem(project, projects_dir)
        _write(project, s, projects_dir)
        return s

    s = json.loads(path.read_text(encoding="utf-8"))
    # reset any stale 'running' (no process survives a UI restart)
    changed = False
    for step in STEPS:
        if s.get(step, {}).get("status") == "running":
            s[step] = {"status": "failed", "completed_at": _now(),
                       "artifacts": [], "error": "Process interrupted — re-run."}
            changed = True
    if changed:
        _write(project, s, projects_dir)
    return s


def _write(project: str, s: dict, projects_dir: Path) -> None:
    path = _state_path(project, projects_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(s, indent=2), encoding="utf-8")


def _update(project: str, step: str, projects_dir: Path, **fields) -> None:
    s = load(project, projects_dir)
    s[step].update(fields)
    _write(project, s, projects_dir)


def set_running(project: str, step: str, projects_dir: Path = Path("projects")) -> None:
    _update(project, step, projects_dir, status="running", error=None)


def set_done(project: str, step: str, projects_dir: Path = Path("projects")) -> None:
    artifacts = _scan_artifacts(project, step, projects_dir)
    _update(project, step, projects_dir, status="done", completed_at=_now(),
            artifacts=artifacts, error=None)


def set_failed(project: str, step: str, error: str,
               projects_dir: Path = Path("projects")) -> None:
    _update(project, step, projects_dir, status="failed", completed_at=_now(), error=error)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/ui/test_state.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add ui/state.py tests/ui/test_state.py
git commit -m "feat(ui): add per-project state persistence with filesystem fallback"
```

---

### Task 4: runner.py — subprocess wrapper that yields output

**Files:**
- Create: `ui/runner.py`
- Test: `tests/ui/test_runner.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/ui/test_runner.py
import sys
from ui.runner import run


def test_run_yields_lines_and_returns_zero():
    argv = [sys.executable, "-c", "print('hello'); print('world')"]
    lines = []
    code = yield_collect(argv, lines)
    assert code == 0
    assert "hello" in lines
    assert "world" in lines


def test_run_nonzero_exit():
    argv = [sys.executable, "-c", "import sys; sys.stderr.write('boom\\n'); sys.exit(3)"]
    lines = []
    code = yield_collect(argv, lines)
    assert code == 3
    assert any("boom" in ln for ln in lines)


def yield_collect(argv, lines):
    """Drive the run() generator, collecting lines, returning the exit code."""
    gen = run(argv)
    try:
        while True:
            lines.append(next(gen))
    except StopIteration as stop:
        return stop.value
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/ui/test_runner.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ui.runner'`

- [ ] **Step 3: Write minimal implementation**

```python
# ui/runner.py
"""Run a pipeline subprocess, yielding combined stdout/stderr lines.

Usage:
    gen = run(argv)
    for line in gen:        # each output line as it arrives
        ...
    exit_code = gen.value   # available after StopIteration

Run from the repo root so `python -m src.cli` resolves.
"""
import subprocess
from pathlib import Path


def run(argv: list[str], cwd: Path = Path(".")):
    """Generator: yields output lines; return value is the exit code."""
    proc = subprocess.Popen(
        argv,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        yield line.rstrip("\n")
    proc.wait()
    return proc.returncode
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/ui/test_runner.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add ui/runner.py tests/ui/test_runner.py
git commit -m "feat(ui): add subprocess runner that streams output lines"
```

---

### Task 5: Pipeline view component (pills + active card)

**Files:**
- Create: `ui/components/pipeline.py`

This is Streamlit view code — no unit test (covered by manual smoke test in Task 8). Keep logic minimal; all decisions come from `state` dict.

- [ ] **Step 1: Implement the pill row + active card**

```python
# ui/components/pipeline.py
"""Pipeline step pills + active-step control card."""
import streamlit as st

from ui.cli_map import STEPS, RESOLUTION_PRESETS

# pastel palette
_LAVENDER = "#c9b8ff"
_MINT = "#b8f0c8"
_PEACH = "#f9c784"
_RED = "#ffb3b3"
_DIM = "#333333"

_STATUS_COLOR = {"done": _MINT, "running": _PEACH, "failed": _RED, "pending": _DIM}


def _first_incomplete(state: dict) -> str:
    for step in STEPS:
        if state[step]["status"] != "done":
            return step
    return STEPS[-1]


def render_pills(state: dict) -> None:
    """Render the colored step pills in canonical order."""
    cols = st.columns(len(STEPS))
    for col, step in zip(cols, STEPS):
        status = state[step]["status"]
        color = _STATUS_COLOR[status]
        tick = " ✓" if status == "done" else ""
        col.markdown(
            f"<div style='text-align:center;padding:4px 6px;border:1px solid {color}55;"
            f"border-radius:16px;color:{color};font-size:12px'>{step}{tick}</div>",
            unsafe_allow_html=True,
        )


def render_active_card(state: dict, project: str):
    """Render the option form for the first incomplete step.

    Returns (step, options_dict, run_clicked).
    """
    step = _first_incomplete(state)
    st.markdown(f"#### {step.upper()}")
    options: dict = {}

    if step == "script":
        src = st.text_input("Source URL (optional)", key="script_url")
        if src:
            options["url"] = src
        options["mock"] = st.toggle("Mock LLM", key="script_mock")
    elif step in ("narration", "scenes"):
        options["force"] = st.toggle("Force regenerate", key=f"{step}_force")
    elif step == "voiceover":
        options["provider"] = st.selectbox("TTS provider", ["edge", "mock", "elevenlabs"],
                                            key="vo_provider")
    elif step == "render":
        options["resolution"] = st.selectbox("Resolution", list(RESOLUTION_PRESETS),
                                              key="render_res")
        options["fast"] = st.toggle("Fast encode", key="render_fast")

    run_clicked = st.button("Run", type="primary", key=f"run_{step}")
    return step, options, run_clicked
```

- [ ] **Step 2: Verify it imports**

Run: `.venv\Scripts\python.exe -c "import ui.components.pipeline"`
Expected: no output, exit 0

- [ ] **Step 3: Commit**

```bash
git add ui/components/pipeline.py
git commit -m "feat(ui): add pipeline pills and active step card"
```

---

### Task 6: Sidebar, output, and log components

**Files:**
- Create: `ui/components/sidebar.py`
- Create: `ui/components/output.py`
- Create: `ui/components/log.py`

- [ ] **Step 1: Implement sidebar**

```python
# ui/components/sidebar.py
"""Sidebar: project picker, new project, nav links."""
from pathlib import Path

import streamlit as st


def render_sidebar(projects_dir: Path = Path("projects")) -> str | None:
    """Render sidebar; return the selected project name (or None)."""
    st.sidebar.markdown("**video explainer** · local")
    projects = sorted(p.name for p in Path(projects_dir).iterdir() if p.is_dir()) \
        if Path(projects_dir).exists() else []

    selected = st.sidebar.radio("Projects", projects, key="project_pick") if projects else None

    with st.sidebar.expander("+ new project"):
        new_name = st.text_input("Project id", key="new_project_name")
        if st.button("Create", key="create_project") and new_name:
            st.session_state["_create_project"] = new_name

    st.sidebar.markdown("---")
    st.sidebar.markdown("[Remotion Studio ↗](http://localhost:3000)")
    return selected
```

- [ ] **Step 2: Implement output viewer**

```python
# ui/components/output.py
"""Per-step output / error display."""
import streamlit as st

from ui.cli_map import STEPS


def render_outputs(state: dict) -> None:
    """Show artifacts for done steps and errors for failed steps."""
    for step in STEPS:
        info = state[step]
        if info["status"] == "done" and info["artifacts"]:
            with st.expander(f"{step} output ✓ ({len(info['artifacts'])} files)"):
                for a in info["artifacts"]:
                    st.text(a)
        elif info["status"] == "failed" and info["error"]:
            st.error(f"{step}: {info['error']}")
```

- [ ] **Step 3: Implement log strip**

```python
# ui/components/log.py
"""Live log strip backed by a Streamlit placeholder."""
import streamlit as st


def make_log_area():
    """Return a Streamlit empty placeholder to stream log lines into."""
    return st.empty()


def update_log(placeholder, lines: list[str], max_lines: int = 200) -> None:
    """Render the last max_lines lines in a monospace code block."""
    tail = "\n".join(lines[-max_lines:])
    placeholder.code(tail or "waiting...", language="text")
```

- [ ] **Step 4: Verify imports**

Run: `.venv\Scripts\python.exe -c "import ui.components.sidebar, ui.components.output, ui.components.log"`
Expected: no output, exit 0

- [ ] **Step 5: Commit**

```bash
git add ui/components/sidebar.py ui/components/output.py ui/components/log.py
git commit -m "feat(ui): add sidebar, output viewer, and log components"
```

---

### Task 7: app.py — wire everything together

**Files:**
- Create: `ui/app.py`

- [ ] **Step 1: Implement the Streamlit entrypoint**

```python
# ui/app.py
"""Streamlit dashboard for the video_explainer pipeline.

Run from the repo root:
    streamlit run ui/app.py
"""
import subprocess
import sys
from pathlib import Path

import streamlit as st

from ui import state
from ui.cli_map import build_argv
from ui.components.log import make_log_area, update_log
from ui.components.output import render_outputs
from ui.components.pipeline import render_active_card, render_pills
from ui.components.sidebar import render_sidebar
from ui.runner import run

PROJECTS_DIR = Path("projects")

st.set_page_config(page_title="video explainer", layout="wide")

# Handle pending "create project" request from the sidebar
if st.session_state.get("_create_project"):
    name = st.session_state.pop("_create_project")
    subprocess.run([sys.executable, "-m", "src.cli", "create", name], check=False)
    state.load(name, PROJECTS_DIR)  # seeds state.json
    st.rerun()

project = render_sidebar(PROJECTS_DIR)

if not project:
    st.info("Create or select a project in the sidebar to begin.")
    st.stop()

current = state.load(project, PROJECTS_DIR)
render_pills(current)
st.markdown("---")
step, options, run_clicked = render_active_card(current, project)
render_outputs(current)

log_area = make_log_area()

if run_clicked:
    state.set_running(project, step, PROJECTS_DIR)
    lines: list[str] = []
    gen = run(build_argv(step, project, options))
    exit_code = 0
    try:
        while True:
            lines.append(next(gen))
            update_log(log_area, lines)
    except StopIteration as stop:
        exit_code = stop.value or 0

    if exit_code == 0:
        state.set_done(project, step, PROJECTS_DIR)
        st.success(f"{step} complete.")
    else:
        err = lines[-1] if lines else f"exit code {exit_code}"
        state.set_failed(project, step, err, PROJECTS_DIR)
        st.error(f"{step} failed (exit {exit_code}).")
    st.rerun()
```

- [ ] **Step 2: Verify it imports without running the server**

Run: `.venv\Scripts\python.exe -c "import ui.app"`
Expected: may print Streamlit warnings about bare mode, but no ImportError / exit 0. (If it raises `ModuleNotFoundError`, fix the import; Streamlit runtime warnings are fine.)

- [ ] **Step 3: Commit**

```bash
git add ui/app.py
git commit -m "feat(ui): add streamlit app entrypoint wiring all components"
```

---

### Task 8: Full test run + manual smoke test + docs

**Files:**
- Modify: `README.md` — add a "Web UI" section

- [ ] **Step 1: Run the full ui test suite**

Run: `.venv\Scripts\python.exe -m pytest tests/ui/ -v`
Expected: all pass (15 tests across cli_map, state, runner)

- [ ] **Step 2: Launch the app and smoke test**

Run: `.venv\Scripts\python.exe -m streamlit run ui/app.py`
Expected: opens `http://localhost:8501`. Manually verify:
- sidebar lists `demo` project
- pills show script/narration done (mint), scenes failed (red) — matching state
- selecting render step shows the resolution dropdown including "Vertical 1080" and "Vertical 720"
- clicking Run on a step streams log lines and updates the pill on completion

- [ ] **Step 3: Add README section**

In `README.md`, after the `### Remotion Studio` subsection under `## Development`, add:

```markdown
### Web UI (Dashboard)

A local Streamlit dashboard wraps the CLI for point-and-click pipeline runs.

\`\`\`bash
pip install -e ".[ui]"
streamlit run ui/app.py   # opens http://localhost:8501
\`\`\`

Pick a project in the sidebar, run pipeline steps from the pill row, and watch
live logs. Progress is saved to \`projects/<name>/state.json\` and survives restarts.
Resolution presets include vertical (Shorts/Reels/TikTok) variants.
```

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: document the streamlit web UI"
```

---

### Task 9: Settings panel — edit config.yaml

**Files:**
- Create: `ui/components/settings.py`
- Create: `ui/config_io.py`
- Test: `tests/ui/test_config_io.py`
- Modify: `ui/components/sidebar.py` — make "Settings" a real toggle
- Modify: `ui/app.py` — route to settings view when toggled

- [ ] **Step 1: Write the failing test for config read/write**

```python
# tests/ui/test_config_io.py
from pathlib import Path
from ui.config_io import load_config, save_config


def test_round_trip_preserves_values(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "llm:\n  provider: claude-code\n  model: claude-sonnet-4-20250514\n"
        "tts:\n  provider: mock\n  voice_id: null\n"
        "video:\n  width: 1920\n  height: 1080\n  fps: 30\n",
        encoding="utf-8",
    )
    data = load_config(cfg)
    assert data["llm"]["provider"] == "claude-code"

    data["tts"]["provider"] = "edge"
    save_config(cfg, data)

    reloaded = load_config(cfg)
    assert reloaded["tts"]["provider"] == "edge"
    assert reloaded["video"]["fps"] == 30
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/ui/test_config_io.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ui.config_io'`

- [ ] **Step 3: Implement config_io**

```python
# ui/config_io.py
"""Load and save config.yaml for the settings panel."""
from pathlib import Path

import yaml


def load_config(path: Path = Path("config.yaml")) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def save_config(path: Path, data: dict) -> None:
    Path(path).write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/ui/test_config_io.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Implement the settings view**

```python
# ui/components/settings.py
"""Settings panel — edits config.yaml in place."""
from pathlib import Path

import streamlit as st

from ui.config_io import load_config, save_config


def render_settings(config_path: Path = Path("config.yaml")) -> None:
    st.markdown("#### Settings")
    cfg = load_config(config_path)
    llm = cfg.setdefault("llm", {})
    tts = cfg.setdefault("tts", {})
    video = cfg.setdefault("video", {})

    llm["provider"] = st.selectbox(
        "LLM provider", ["claude-code", "mock"],
        index=["claude-code", "mock"].index(llm.get("provider", "claude-code")),
    )
    llm["model"] = st.text_input("LLM model", value=llm.get("model", ""))
    tts["provider"] = st.selectbox(
        "TTS provider", ["mock", "edge", "elevenlabs"],
        index=["mock", "edge", "elevenlabs"].index(tts.get("provider", "mock")),
    )
    video["fps"] = st.number_input("FPS", value=int(video.get("fps", 30)), min_value=1)

    if st.button("Apply", type="primary"):
        save_config(config_path, cfg)
        st.success("config.yaml updated.")
```

- [ ] **Step 6: Wire the toggle in sidebar.py**

In `ui/components/sidebar.py`, replace the Remotion line block at the end with:

```python
    st.sidebar.markdown("---")
    show_settings = st.sidebar.toggle("Settings", key="show_settings")
    st.sidebar.markdown("[Remotion Studio ↗](http://localhost:3000)")
    st.session_state["_show_settings"] = show_settings
    return selected
```

- [ ] **Step 7: Route to settings in app.py**

In `ui/app.py`, immediately after the `project = render_sidebar(PROJECTS_DIR)` line, add:

```python
if st.session_state.get("_show_settings"):
    from ui.components.settings import render_settings
    render_settings()
    st.stop()
```

- [ ] **Step 8: Run full suite + verify**

Run: `.venv\Scripts\python.exe -m pytest tests/ui/ -v`
Expected: all pass (16 tests)

- [ ] **Step 9: Commit**

```bash
git add ui/config_io.py ui/components/settings.py ui/components/sidebar.py ui/app.py tests/ui/test_config_io.py
git commit -m "feat(ui): add settings panel to edit config.yaml"
```

---

## Self-Review Notes

- **Spec coverage:** 2-column layout (Task 5/6), pill row colors (Task 5), per-step option cards (Task 5), state.json with artifacts (Task 3), filesystem fallback (Task 3), stale-running reset (Task 3), vertical resolution presets (Task 2), new project flow (Task 7), Remotion Studio link (Task 6), settings panel (Task 9). All spec sections covered.
- **CLI correction:** Spec placed "Resolution" on the Scenes step; the real CLI only accepts `--resolution` on `render`. Plan maps resolution to the Render step (correct behavior) — confirm this matches your intent.
- **Placeholder scan:** none found — every code step has full code.
- **Type consistency:** `build_argv`, `STEPS`, `RESOLUTION_PRESETS`, `state.load/set_running/set_done/set_failed`, `run` generator contract consistent across tasks.
