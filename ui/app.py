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
