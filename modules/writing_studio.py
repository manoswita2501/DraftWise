import streamlit as st
from llm.gemini_client import generate_text, MODEL_DEFAULT
from llm.prompts import writing_studio_prompt, shorten_prompt
#from utils.ui_render import render_compact

SECTIONS = [
    "Abstract",
    "Introduction",
    "Related Work (skeleton)",
    "Method",
    "Experimental Setup",
    "Limitations & Ethics",
    "Conclusion & Future Work",
]

def _gather_context() -> dict:
    a = st.session_state.artifacts
    topic = a.get("selected_topic") or {}
    plan = a.get("plan") or ""
    dataset = a.get("dataset") or None
    dataset_choice = a.get("dataset_choice") or None

    dataset_md = ""
    if isinstance(dataset, dict) and dataset.get("report_md"):
        dataset_md = dataset.get("report_md", "")
    elif isinstance(dataset_choice, dict):
        # turn dataset choice into a small markdown snippet
        picked = dataset_choice.get("picked_option", {})
        dataset_md = "\n".join([
            "## Dataset decision",
            f"- Picked: **{picked.get('title','')}**",
            f"- Justification: {dataset_choice.get('justification','')}",
            f"- Anticipated risk: {dataset_choice.get('anticipated_risk','')}",
            "",
            "### Option details",
            picked.get("block", ""),
        ])

    return {
        "topic_title": topic.get("title", ""),
        "topic_text": topic.get("full_text", ""),
        "plan_md": plan,
        "dataset_md": dataset_md,
    }

def _ensure_writing_state():
    if "writing" not in st.session_state.artifacts or st.session_state.artifacts["writing"] is None:
        st.session_state.artifacts["writing"] = {}

def _compile_draft(writing: dict) -> str:
    order = [
        ("Abstract", "Abstract"),
        ("Introduction", "Introduction"),
        ("Related Work (skeleton)", "Related Work"),
        ("Method", "Method"),
        ("Experimental Setup", "Experimental Setup"),
        ("Limitations & Ethics", "Limitations & Ethics"),
        ("Conclusion & Future Work", "Conclusion & Future Work"),
    ]
    parts = []
    for key, title in order:
        if key in writing and writing[key].strip():
            parts.append(f"## {title}\n\n{writing[key].strip()}\n")
    if not parts:
        return ""
    return "# DraftWise Paper Draft\n\n" + "\n".join(parts)

def render_writing_studio(cfg):
    st.subheader("Writing Studio")
    st.write("Generate paper sections from your selected topic + plan + dataset info. No fake results.")

    _ensure_writing_state()
    ctx = _gather_context()

    # Hard guardrail: topic is required
    if not ctx["topic_title"]:
        st.warning("Select a topic in **Topic Picker** first.")
        st.stop()

    # Soft guardrails: plan/dataset are recommended (not required)
    plan_ok = bool(st.session_state.artifacts.get("plan"))
    dataset_ok = bool(st.session_state.artifacts.get("dataset")) or bool(st.session_state.artifacts.get("dataset_choice"))

    if not plan_ok:
        st.info("Plan not found. You can still draft, but **Plan Builder** will improve quality.")
    if not dataset_ok:
        st.info("Dataset not found. You can still draft, but **Dataset Helper** will improve setup sections.")

    with st.expander("What Writing Studio will use (context)", expanded=False):
        st.write(f"**Topic:** {ctx['topic_title']}")
        st.caption("Plan included?" + (" Yes" if ctx["plan_md"] else " No"))
        st.caption("Dataset info included?" + (" Yes" if ctx["dataset_md"] else " No"))

    sel = st.multiselect("Choose sections to generate", SECTIONS, default=["Abstract", "Introduction"])
    write_mode = st.radio("Writing mode", ["Template", "Draft"], index=0, horizontal=True)
    extra_notes = st.text_area(
        "Optional: extra notes / constraints",
        placeholder="e.g., keep it short, focus on reproducibility, emphasize my intended contribution...",
        height=90,
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        gen = st.button("Generate selected sections", type="primary", use_container_width=True)
    with col2:
        clear = st.button("Clear generated sections", use_container_width=True)

    if clear:
        st.session_state.artifacts["writing"] = {}
        st.rerun()

    if gen:
        writing = st.session_state.artifacts["writing"]
        for section in sel:
            prompt = writing_studio_prompt(
                cfg,
                section=section,
                context={
                    **ctx,
                    "extra_notes": extra_notes.strip(),
                },
                write_mode=write_mode
            )
            with st.status(f"Generating {section}...", expanded=False) as status:
                text = generate_text(prompt)
                status.update(label=f"{section} generated.", state="complete", expanded=False)
            writing[section] = text
        st.session_state.artifacts["writing"] = writing
        st.success("Generated.")

    writing = st.session_state.artifacts.get("writing", {})

    if not writing:
        st.info("Generate at least one section to see output here.")
        return

    st.divider()
    st.subheader("Generated sections")

    for section in SECTIONS:
        if section in writing:
            with st.expander(section, expanded=True):
                b1, b2 = st.columns(2)
                with b1:
                    regen_sec = st.button(f"Regenerate {section}", key=f"regen_{section}")
                with b2:
                    short_sec = st.button(f"Shorten {section}", key=f"short_{section}")

                if regen_sec:
                    prompt = writing_studio_prompt(cfg, section=section, context=ctx, write_mode=write_mode)
                    with st.status(f"Regenerating {section}...", expanded=False) as status:
                        try:
                            new_text = generate_text(prompt)
                        except Exception as e:
                            status.update(label=f"{section} regeneration failed.", state="error", expanded=True)
                            st.error(f"AI request failed: {e}")
                            st.stop()
                        status.update(label=f"{section} regenerated.", state="complete", expanded=False)

                    st.session_state.artifacts["writing"][section] = new_text
                    st.rerun()

                if short_sec:
                    prompt = shorten_prompt(cfg, writing[section])
                    with st.status(f"Shortening {section}...", expanded=False) as status:
                        try:
                            new_text = generate_text(prompt)
                        except Exception as e:
                            status.update(label=f"{section} shortening failed.", state="error", expanded=True)
                            st.error(f"AI request failed: {e}")
                            st.stop()
                        status.update(label=f"{section} shortened.", state="complete", expanded=False)

                    st.session_state.artifacts["writing"][section] = new_text
                    st.rerun()

                st.markdown(st.session_state.artifacts["writing"][section])

                #render_compact(writing[section], details_title="Show full section")

    draft = _compile_draft(writing)
    if draft:
        st.divider()
        st.subheader("Download full draft")
        reviewed = st.checkbox("I reviewed and edited this output.", value=False, key="draft_reviewed")
    st.download_button(
        "Download combined draft (.md)",
        data=draft.encode("utf-8"),
        file_name="draftwise_paper_draft.md",
        mime="text/markdown",
        disabled=not reviewed,
    )