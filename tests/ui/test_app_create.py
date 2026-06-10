"""Regression test: the sidebar Create button must create a project in ONE click.

Guards against the rerun-ordering bug where the create flag was set in the
sidebar AFTER app.py's top-of-script handler had already run, so nothing
happened until a second interaction.
"""
import shutil
from pathlib import Path

from streamlit.testing.v1 import AppTest

_PROJ = Path("projects/zz_regr_create")


def _cleanup():
    if _PROJ.exists():
        shutil.rmtree(_PROJ)


def test_create_button_creates_project_in_one_click():
    _cleanup()
    try:
        at = AppTest.from_file("ui/app.py", default_timeout=60)
        at.run()
        assert not at.exception

        at.text_input(key="new_project_name").set_value("zz_regr_create").run()
        at.button(key="create_project").click().run()

        assert not at.exception
        assert _PROJ.exists(), "project dir not created on a single click"
        assert (_PROJ / "state.json").exists(), "state.json not seeded"
        assert any("zz_regr_create" in s.value for s in at.success)
        assert at.radio(key="project_pick").value == "zz_regr_create"
    finally:
        _cleanup()
