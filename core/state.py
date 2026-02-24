import streamlit as st
from dataclasses import dataclass, asdict

@dataclass
class UserConfig:
    goal: str
    help_level: str
    degree_level: str
    track: str
    time_days: int
    paper_type: str
    output_depth: str

def init_state():
    if "configured" not in st.session_state:
        st.session_state.configured = False
    if "config" not in st.session_state:
        st.session_state.config = None
    if "artifacts" not in st.session_state:
        st.session_state.artifacts = {
            "topics": None,
            "selected_topic": None,
            "plan": None,
            "dataset": None,
            "writing": {},
            "paper_analysis": None,
        }

def set_config(cfg: UserConfig):
    st.session_state.config = asdict(cfg)
    st.session_state.configured = True

def reset_workspace():
    st.session_state.configured = False
    st.session_state.config = None
    st.session_state.artifacts = {
        "topics": None,
        "topics_raw": None,
        "selected_topic": None,
        "plan": None,
        "dataset": None,
        "writing": {},
        "paper_analysis": None,
    }

def restore_workspace(config: dict, artifacts: dict):
    st.session_state.config = config
    st.session_state.artifacts = artifacts
    st.session_state.configured = True