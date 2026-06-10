"""Per-project pipeline state persisted to projects/<name>/state.json."""
import json
from datetime import datetime, timezone
from pathlib import Path

from ui.cli_map import STEPS

# Steps actively set to "running" in this process — exempt from stale reset.
_active_running: set[tuple[str, str]] = set()

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


def _read_or_derive(project: str, projects_dir: Path) -> dict:
    """Read state.json as-is, or derive from filesystem — no stale-reset."""
    path = _state_path(project, projects_dir)
    if not path.exists():
        s = _derive_from_filesystem(project, projects_dir)
        _write(project, s, projects_dir)
        return s
    return json.loads(path.read_text(encoding="utf-8"))


def load(project: str, projects_dir: Path = Path("projects")) -> dict:
    """Load state; derive from filesystem if missing; reset stale 'running'."""
    s = _read_or_derive(project, projects_dir)
    changed = False
    for step in STEPS:
        if (s.get(step, {}).get("status") == "running"
                and (project, step) not in _active_running):
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
    """Mutate one step's fields and persist — no stale-reset side-effect."""
    s = _read_or_derive(project, projects_dir)
    s[step].update(fields)
    _write(project, s, projects_dir)


def set_running(project: str, step: str, projects_dir: Path = Path("projects")) -> None:
    _active_running.add((project, step))
    _update(project, step, projects_dir, status="running", error=None)


def set_done(project: str, step: str, projects_dir: Path = Path("projects")) -> None:
    _active_running.discard((project, step))
    artifacts = _scan_artifacts(project, step, projects_dir)
    _update(project, step, projects_dir, status="done", completed_at=_now(),
            artifacts=artifacts, error=None)


def set_failed(project: str, step: str, error: str,
               projects_dir: Path = Path("projects")) -> None:
    _active_running.discard((project, step))
    _update(project, step, projects_dir, status="failed", completed_at=_now(), error=error)
