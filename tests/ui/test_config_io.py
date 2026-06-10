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
