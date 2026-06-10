import json
import pytest
from pathlib import Path
from ui import state


@pytest.fixture(autouse=True)
def _isolate_active_running():
    """Ensure _active_running is empty before every test to prevent inter-test leakage."""
    state._reset_active_running()
    yield
    state._reset_active_running()


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
    assert (proj / "state.json").exists()


def test_stale_running_reset_to_failed(tmp_path):
    proj = _make_project(tmp_path)
    pdir = tmp_path / "projects"
    raw = state._empty_state()
    raw["scenes"]["status"] = "running"
    (proj / "state.json").write_text(json.dumps(raw), encoding="utf-8")

    s = state.load("demo", projects_dir=pdir)
    assert s["scenes"]["status"] == "failed"
    assert "interrupted" in s["scenes"]["error"].lower()


def test_partial_state_file_backfills_missing_steps(tmp_path):
    """A state.json that only contains some steps is backfilled with 'pending' entries."""
    proj = _make_project(tmp_path)
    pdir = tmp_path / "projects"
    partial = {"script": {"status": "done", "completed_at": "2024-01-01T00:00:00+00:00",
                          "artifacts": ["script/script.json"], "error": None}}
    (proj / "state.json").write_text(json.dumps(partial), encoding="utf-8")

    s = state.load("demo", projects_dir=pdir)
    assert set(s) == {"script", "narration", "scenes", "voiceover", "storyboard", "render"}
    assert s["script"]["status"] == "done"
    for step in ("narration", "scenes", "voiceover", "storyboard", "render"):
        assert s[step]["status"] == "pending", f"Expected pending for {step}, got {s[step]['status']}"


def test_corrupt_state_file_recovers(tmp_path):
    """A malformed state.json does not crash load(); the bad file is overwritten."""
    proj = _make_project(tmp_path)
    pdir = tmp_path / "projects"
    state_file = proj / "state.json"
    state_file.write_text("{ not json", encoding="utf-8")

    s = state.load("demo", projects_dir=pdir)
    assert set(s) == {"script", "narration", "scenes", "voiceover", "storyboard", "render"}
    assert all(isinstance(v, dict) for v in s.values())
    # The bad file must have been overwritten with valid JSON.
    recovered = json.loads(state_file.read_text(encoding="utf-8"))
    assert set(recovered) == {"script", "narration", "scenes", "voiceover", "storyboard", "render"}
