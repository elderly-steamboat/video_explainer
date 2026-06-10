"""Live log strip backed by a Streamlit placeholder."""
import streamlit as st


def make_log_area():
    """Return a Streamlit empty placeholder to stream log lines into."""
    return st.empty()


def update_log(placeholder, lines: list[str], max_lines: int = 200) -> None:
    """Render the last max_lines lines in a monospace code block."""
    tail = "\n".join(lines[-max_lines:])
    placeholder.code(tail or "waiting...", language="text")
