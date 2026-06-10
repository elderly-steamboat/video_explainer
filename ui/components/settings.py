"""Settings panel — edits config.yaml in place."""
from pathlib import Path

import streamlit as st

from ui.config_io import load_config, save_config


def _safe_index(options: list, value, default: int = 0) -> int:
    """Return the index of *value* in *options*, or *default* if not found."""
    try:
        return options.index(value)
    except ValueError:
        return default


def render_settings(config_path: Path = Path("config.yaml")) -> None:
    st.markdown("#### Settings")
    cfg = load_config(config_path)
    llm = cfg.setdefault("llm", {})
    tts = cfg.setdefault("tts", {})
    video = cfg.setdefault("video", {})

    llm_providers = ["claude-code", "mock"]
    llm["provider"] = st.selectbox(
        "LLM provider", llm_providers,
        index=_safe_index(llm_providers, llm.get("provider", "claude-code")),
    )
    llm["model"] = st.text_input("LLM model", value=llm.get("model", ""))

    tts_providers = ["mock", "edge", "elevenlabs"]
    tts["provider"] = st.selectbox(
        "TTS provider", tts_providers,
        index=_safe_index(tts_providers, tts.get("provider", "mock")),
    )
    video["fps"] = st.number_input("FPS", value=int(video.get("fps", 30)), min_value=1)

    if st.button("Apply", type="primary"):
        save_config(config_path, cfg)
        st.success("config.yaml updated.")
