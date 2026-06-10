"""Sidebar: project picker, new project, nav links."""
from pathlib import Path

import streamlit as st


def render_sidebar(projects_dir: Path = Path("projects")) -> str | None:
    """Render sidebar; return the selected project name (or None)."""
    st.sidebar.markdown("**video explainer** · local")
    projects = sorted(p.name for p in Path(projects_dir).iterdir() if p.is_dir()) \
        if Path(projects_dir).exists() else []

    selected = st.sidebar.radio("Projects", projects, key="project_pick") if projects else None

    with st.sidebar.expander("+ new project"):
        new_name = st.text_input("Project id", key="new_project_name")
        if st.button("Create", key="create_project") and new_name:
            st.session_state["_create_project"] = new_name

    st.sidebar.markdown("---")
    show_settings = st.sidebar.toggle("Settings", key="show_settings")
    st.sidebar.markdown("[Remotion Studio ↗](http://localhost:3000)")
    st.session_state["_show_settings"] = show_settings
    return selected
