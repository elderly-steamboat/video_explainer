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
