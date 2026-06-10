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
