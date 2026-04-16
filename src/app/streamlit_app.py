"""ATNA Streamlit application entrypoint with explicit routing."""

from __future__ import annotations

import sys
from pathlib import Path

# Pytest adds `src` via pytest.ini; `streamlit run src/app/streamlit_app.py` does not.
_src_root = Path(__file__).resolve().parent.parent
if str(_src_root) not in sys.path:
    sys.path.insert(0, str(_src_root))

import streamlit as st

from app.pages.airport_explorer import render_airport_explorer_page
from app.pages.communities import render_communities_page
from app.pages.methodology import render_methodology_page
from app.pages.network_map import render_network_map_page
from app.pages.overview import render_overview_page
from app.pages.route_explorer import render_route_explorer_page
from app.pages.scenario_editor import render_scenario_editor_page


st.set_page_config(
    page_title="ATNA",
    page_icon=":airplane:",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = [
    st.Page(render_overview_page, title="APP-01 Overview", icon=":material/dashboard:"),
    st.Page(render_network_map_page, title="APP-02 Network Map", icon=":material/public:"),
    st.Page(
        render_airport_explorer_page,
        title="APP-03 Airport Explorer",
        icon=":material/location_city:",
    ),
    st.Page(render_communities_page, title="APP-04 Communities", icon=":material/group_work:"),
    st.Page(render_route_explorer_page, title="APP-05 Route Explorer", icon=":material/route:"),
    st.Page(render_scenario_editor_page, title="APP-06 Scenario Editor", icon=":material/tune:"),
    st.Page(render_methodology_page, title="APP-07 Methodology", icon=":material/menu_book:"),
]

router = st.navigation(pages)
router.run()
