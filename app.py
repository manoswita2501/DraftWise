import streamlit as st

from core.state import init_state, UserConfig, set_config, reset_workspace, restore_workspace
from core.pack import build_pack, dumps_pack, loads_pack, validate_pack
from modules.topic_picker import render_topic_picker
from modules.plan_builder import render_plan_builder
from modules.dataset_helper import render_dataset_helper
from modules.writing_studio import render_writing_studio
from modules.paper_analyzer import render_paper_analyzer

APP_NAME = "DraftWise"

DISCLAIMER = (
    "Ethics notice: DraftWise is meant to guide beginners and reduce overwhelm. "
    "It does not endorse or recommend submitting AI-generated work as your own. "
    "Use it to learn, plan, and structure your work, and always follow your institution’s academic integrity rules."
)

st.set_page_config(page_title=APP_NAME, layout="wide")

init_state()

# ----- ONE place only: Disclaimer in SIDEBAR (st.info) -----
st.sidebar.markdown(f"## {APP_NAME}")
st.sidebar.info(DISCLAIMER)

st.sidebar.markdown("---")
st.sidebar.subheader("Project Pack")

# Export (only if configured)
if st.session_state.configured:
    pack_obj = build_pack(st.session_state.config, st.session_state.artifacts)
    pack_str = dumps_pack(pack_obj)
    st.sidebar.download_button(
        "Export workspace (.json)",
        data=pack_str.encode("utf-8"),
        file_name="draftwise_project_pack.json",
        mime="application/json",
    )
else:
    st.sidebar.caption("Export available after workspace setup.")

# Import (always available)
uploaded_pack = st.sidebar.file_uploader("Import workspace (.json)", type=["json"], key="pack_uploader")
if uploaded_pack is not None:
    try:
        text = uploaded_pack.read().decode("utf-8")
        pack = loads_pack(text)
        validate_pack(pack)
        restore_workspace(pack["config"], pack["artifacts"])
        st.sidebar.success("Imported workspace successfully.")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"Import failed: {e}")
        
st.sidebar.markdown("---")
st.sidebar.subheader("Progress")

a = st.session_state.artifacts if st.session_state.configured else {}

def done(label: str, ok: bool):
    st.sidebar.write(("✅ " if ok else "⬜ ") + label)

topic_ok = bool(a.get("selected_topic"))
plan_ok = bool(a.get("plan"))
dataset_ok = bool(a.get("dataset")) or bool(a.get("dataset_choice"))
writing_ok = bool(a.get("writing")) and any((v or "").strip() for v in a.get("writing", {}).values())
paper_ok = bool(a.get("paper_analysis"))

done("Topic selected", topic_ok)
done("Plan generated", plan_ok)
done("Dataset chosen/analyzed", dataset_ok)
done("Draft sections generated", writing_ok)
done("Paper/section analyzed", paper_ok)

st.sidebar.caption(f"Completed: {sum([topic_ok, plan_ok, dataset_ok, writing_ok, paper_ok])}/5")

with st.sidebar.expander("Workspace snapshot", expanded=False):
    if not st.session_state.configured:
        st.write("Set up a workspace to see snapshot.")
    else:
        cfg = st.session_state.config
        st.write(f"**Goal:** {cfg['goal']}")
        st.write(f"**Help:** {cfg['help_level']}")
        st.write(f"**Degree:** {cfg['degree_level']}")
        st.write(f"**Track:** {cfg['track']}")
        st.write(f"**Time:** {cfg['time_days']} days")
        st.write(f"**Paper type:** {cfg['paper_type']}")

        if topic_ok:
            st.write(f"**Topic:** {a['selected_topic'].get('title','')}")

if st.session_state.configured:
    with st.sidebar.expander("Danger zone", expanded=False):
        st.caption("This will clear your current workspace state (topic, plan, dataset, drafts, analyses).")
        confirm_reset = st.checkbox("I understand and want to reset", value=False, key="confirm_reset")

        if st.button("Reset workspace", key="reset_workspace_btn"):
            if not confirm_reset:
                st.warning("Please tick the confirmation checkbox first.")
            else:
                reset_workspace()
                st.rerun()

st.title(APP_NAME)
st.caption("A structured research companion for CS/IT: topics, plans, drafts, and paper analysis.")

if not st.session_state.configured:
    st.subheader("Setup")

    with st.form("onboarding"):
        goal = st.selectbox("Goal", ["College submission", "Personal project"])
        help_level = st.selectbox("Help level", ["DIY", "Guided", "Done-for-you"])
        degree_level = st.selectbox("Degree level", ["Bachelors", "Masters"])
        paper_type = st.selectbox("Paper type", ["College-level", "Conference-level", "Report-level"])
        output_depth = st.selectbox("Output depth", ["Short", "Balanced", "Detailed"], index=1)
        track = st.text_input("Track (free text)", placeholder="e.g., NLP, Cybersecurity, Distributed Systems, CV, MLOps…")
        time_days = st.slider("Time window (days)", min_value=7, max_value=180, value=14, step=1)

        ack = st.checkbox("I understand this is a guide and I will follow academic integrity policies.", value=True)
        submitted = st.form_submit_button("Create workspace", type="primary")

    if submitted:
        if not track.strip():
            st.error("Please enter a track.")
        elif not ack:
            st.error("Please acknowledge the integrity checkbox.")
        else:
            set_config(
                UserConfig(
                    goal=goal,
                    help_level=help_level,
                    degree_level=degree_level,
                    track=track.strip(),
                    time_days=time_days,
                    paper_type=paper_type,
                    output_depth=output_depth,
                )
            )
            st.rerun()

else:
    cfg = st.session_state.config

    st.write("")
    st.subheader("Workspace")
    c1, c2, c3 = st.columns(3)

    with c1:
        st.caption("Goal")
        st.write(f"**{cfg['goal']}**")
        st.caption("Help level")
        st.write(f"**{cfg['help_level']}**")

    with c2:
        st.caption("Degree level")
        st.write(f"**{cfg['degree_level']}**")
        st.caption("Paper type")
        st.write(f"**{cfg['paper_type']}**")

    with c3:
        st.caption("Track")
        st.write(f"**{cfg['track']}**")
        st.caption("Time window")
        st.write(f"**{cfg['time_days']} days**")

    st.write("")
    tabs = st.tabs(["Topic Picker", "Plan Builder", "Dataset Helper", "Writing Studio", "Paper Analyzer"])

    with tabs[0]:
        render_topic_picker(cfg)
    with tabs[1]:
        render_plan_builder(cfg)
    with tabs[2]:
        render_dataset_helper(cfg)
    with tabs[3]:
        render_writing_studio(cfg)
    with tabs[4]:
        render_paper_analyzer(cfg)