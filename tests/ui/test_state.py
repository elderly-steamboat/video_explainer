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
