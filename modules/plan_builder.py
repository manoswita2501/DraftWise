import streamlit as st
from llm.gemini_client import generate_text, MODEL_DEFAULT
from llm.prompts import plan_builder_prompt, shorten_prompt 
from utils.ui_render import render_compact

def render_plan_builder(cfg):
    st.subheader("Plan Builder")
    st.write("Turn your selected topic into a concrete experimental plan and a reviewer-style critique.")
    
    chosen = st.session_state.artifacts.get("selected_topic")
    if not chosen:
        st.warning("No topic selected yet. Select a topic in **Topic Picker** first.")
        st.stop()

    with st.expander("Selected topic", expanded=False):
        st.write(f"**Idea {chosen.get('idea_number')}: {chosen.get('title')}**")
        st.text(chosen.get("full_text", ""))

    col1, col2 = st.columns([1, 1])
    with col1:
        run = st.button("Generate plan", type="primary", use_container_width=True)
    with col2:
        pass

    if run:
        st.session_state.artifacts["plan"] = None
        prompt = plan_builder_prompt(cfg, chosen)
        with st.status("Generating a bounded plan...", expanded=False) as status:
            plan_md = generate_text(prompt)
            status.update(label="Plan generated.", state="complete", expanded=False)
        st.session_state.artifacts["plan"] = plan_md

    plan = st.session_state.artifacts.get("plan")
    if not plan:
        st.info("Click **Generate plan** to create your experimental protocol and timeline.")
        return

    render_compact(plan, details_title="Show full plan details")
    
    c1, c2 = st.columns(2)
    with c1:
        regen2 = st.button("Regenerate plan")
    with c2:
        shorten = st.button("Shorten plan")

    if regen2:
        prompt = plan_builder_prompt(cfg, chosen)
        with st.status("Regenerating plan...", expanded=False) as status:
            plan_md = generate_text(prompt)
            status.update(label="Plan regenerated.", state="complete", expanded=False)
        st.session_state.artifacts["plan"] = plan_md
        st.rerun()

    if shorten:
        prompt = shorten_prompt(cfg, plan)
        with st.status("Shortening plan...", expanded=False) as status:
            short_md = generate_text(prompt)
            status.update(label="Plan shortened.", state="complete", expanded=False)
        st.session_state.artifacts["plan"] = short_md
        st.rerun()

    st.divider()
    st.subheader("Save / export")
    reviewed = st.checkbox("I reviewed and edited this output.", value=False, key="plan_reviewed")
    st.download_button(
        "Download plan as .md",
        data=plan.encode("utf-8"),
        file_name="draftwise_plan.md",
        mime="text/markdown",
        disabled=not reviewed,
    )