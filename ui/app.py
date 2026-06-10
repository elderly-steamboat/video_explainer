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
    result = subprocess.run(
        [sys.executable, "-m", "src.cli", "create", name],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        state.load(name, PROJECTS_DIR)  # seeds state.json
        st.session_state["project_pick"] = name  # select the new project
        st.session_state["_flash"] = ("success", f"Created project '{name}'.")
    else:
        detail = (result.stderr or result.stdout or "").strip().splitlines()
        msg = detail[-1] if detail else "create failed"
        st.session_state["_flash"] = ("error", f"Could not create '{name}': {msg}")
    st.session_state["new_project_name"] = ""  # clear the input box
    st.rerun()

project = render_sidebar(PROJECTS_DIR)

# Surface the result of the last create attempt
flash = st.session_state.pop("_flash", None)
if flash:
    getattr(st.sidebar, flash[0])(flash[1])

if st.session_state.get("_show_settings"):
    from ui.components.settings import render_settings
    render_settings()
    st.stop()

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
    # A script upload is saved into the project's input/ folder and passed via -i.
    if step == "script" and options.get("upload") is not None:
        up = options.pop("upload")
        dest = PROJECTS_DIR / project / "input" / up.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(up.getbuffer())
        options["input"] = str(dest)
        options.pop("url", None)  # an uploaded file takes precedence over a URL
    state.set_running(project, step, PROJECTS_DIR)
    lines: list[str] = []
    exit_code = 0
    with st.spinner(f"Running {step}…"):
        gen = run(build_argv(step, project, options))
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
