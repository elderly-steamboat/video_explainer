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


def test_voiceover_provider():
    argv = build_argv("voiceover", "demo", {"provider": "edge"})
    assert argv == [sys.executable, "-m", "src.cli", "voiceover", "demo",
                    "--provider", "edge"]


def test_render_horizontal_1080():
    argv = build_argv("render", "demo", {"resolution": "1080p"})
    assert argv == [sys.executable, "-m", "src.cli", "render", "demo", "--resolution", "1080p"]


def test_render_vertical_1080_adds_short():
    argv = build_argv("render", "demo", {"resolution": "Vertical 1080"})
    assert argv == [sys.executable, "-m", "src.cli", "render", "demo",
                    "--resolution", "1080p", "--short"]


def test_resolution_presets_labels():
    assert set(RESOLUTION_PRESETS) == {"4K", "1080p", "720p", "Vertical 1080", "Vertical 720"}
