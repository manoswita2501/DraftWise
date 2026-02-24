import re
import streamlit as st
from llm.gemini_client import generate_text, MODEL_DEFAULT
from llm.prompts import topic_picker_prompt
from utils.ui_render import render_compact

# -----------------------------
# Helpers
# -----------------------------
def _extract_ideas(markdown_text: str):
    """
    Extract Idea blocks based on headings:
    ### Idea n: Title
    Returns list of dicts: {n, title, block}
    """
    ideas = []
    pattern = r"^###\s+Idea\s+(\d+)\s*:\s*(.+?)\s*$"
    lines = markdown_text.splitlines()

    idxs = []
    for i, line in enumerate(lines):
        m = re.match(pattern, line.strip())
        if m:
            idxs.append((i, int(m.group(1)), m.group(2).strip()))

    for k, (start_i, n, title) in enumerate(idxs):
        end_i = idxs[k + 1][0] if k + 1 < len(idxs) else len(lines)
        block = "\n".join(lines[start_i:end_i]).strip()
        ideas.append({"n": n, "title": title, "block": block})

    return ideas


def _feasibility_prompt(cfg: dict, title: str, problem: str, plan: str, data: str, metric: str, baseline: str) -> str:
    return f"""
You are DraftWise, a careful CS/IT research mentor.

User context:
- Goal: {cfg["goal"]}
- Help level: {cfg["help_level"]}
- Degree: {cfg["degree_level"]}
- Track: {cfg["track"]}
- Time: {cfg["time_days"]} days
- Paper type: {cfg["paper_type"]}

Student-proposed topic:
Title: {title.strip()}
Problem statement:
{problem.strip()}

What I plan to do (rough plan):
{plan.strip()}

Data situation:
{data.strip()}

Metric (if known):
{metric.strip()}

Baseline (if known):
{baseline.strip()}

Task:
Run a feasibility analysis and give a clear verdict on whether the student should proceed as-is.

Output requirements:
- Markdown only. No JSON. No code fences.
- Use this exact structure:

## Feasibility verdict
**Status:** Green / Yellow / Red
**One-line reason:** ...

## Score breakdown (0–2 each, total /10)
- Clarity:
- Data feasibility:
- Evaluation feasibility:
- Scope fit:
- Execution risk:
**Total:** x/10

## What is strong (2–5 bullets)
- ...

## Biggest risks (3–6 bullets)
- ...

## Tightened scope (MVP you can finish in {cfg["time_days"]} days)
- Problem (1–2 lines):
- Minimum experiments (bullets):
- Minimum deliverables (bullets):

## What you must decide next (max 5 items)
1. ...
2. ...

Rules:
- Stay grounded. Do not invent datasets or results.
- If the topic is too broad, narrow it.
- If the topic depends on private data / heavy compute, propose a feasible alternative direction.
""".strip()


def _parse_status(feas_md: str) -> str:
    # Try to parse Status line: **Status:** Green / Yellow / Red
    m = re.search(r"\*\*Status:\*\*\s*(Green|Yellow|Red)", feas_md, re.IGNORECASE)
    if not m:
        return "Unknown"
    return m.group(1).capitalize()


# -----------------------------
# Main
# -----------------------------

def render_topic_picker(cfg):
    st.subheader("Topic Picker")
    st.write("Pick from DraftWise suggestions, or bring your own topic and run a feasibility check.")

    path = st.radio(
        "Choose your path",
        ["Suggest topics (DraftWise)", "I already have a topic"],
        index=0,
        horizontal=True,
    )

    
    # Guardrail (optional): if on Suggest mode and nothing generated yet, hint user
    if path.startswith("Suggest topics") and not st.session_state.artifacts.get("topics_raw"):
        st.info("No shortlist yet. Click **Generate topics** to continue.")

    # ---------------------------------------------------------
    # Path A: Suggest topics (existing behavior)
    # ---------------------------------------------------------
    if path.startswith("Suggest topics"):
        col1, col2 = st.columns([1, 1])
        with col1:
            regen = st.button("Generate topics", type="primary", use_container_width=True)
        with col2:
            clear = st.button("Clear topics", use_container_width=True)

        if clear:
            st.session_state.artifacts["topics_raw"] = None
            st.session_state.artifacts["selected_topic"] = None
            st.rerun()

        if regen:
            st.session_state.artifacts["topics_raw"] = None
            st.session_state.artifacts["selected_topic"] = None

            prompt = topic_picker_prompt(cfg)
            with st.status("Generating topic ideas...", expanded=False) as status:
                raw = generate_text(prompt)
                status.update(label="Topic ideas generated.", state="complete", expanded=False)

            st.session_state.artifacts["topics_raw"] = raw

        raw = st.session_state.artifacts.get("topics_raw")
        if not raw:
            st.info("Click **Generate topics** to get 3–5 tailored ideas.")
            return

        render_compact(raw, details_title="Show full shortlist details")

        ideas = _extract_ideas(raw)
        if not ideas:
            st.warning("Could not detect idea blocks. Still showing the output above.")
            return

        st.divider()
        st.subheader("Select a topic")

        titles = [f'Idea {it["n"]}: {it["title"]}' for it in ideas]
        choice = st.radio("Pick one to proceed", titles, index=0)

        picked = ideas[titles.index(choice)]
        if st.button("Confirm selection"):
            st.session_state.artifacts["selected_topic"] = {
                "idea_number": picked["n"],
                "title": picked["title"],
                "full_text": picked["block"],
                "source": "draftwise_suggested",
            }
            st.success(f"Selected: {picked['title']}")

    # ---------------------------------------------------------
    # Path B: Student brings their own topic + feasibility gate
    # ---------------------------------------------------------
    else:
        st.markdown("### Bring your own topic")
        st.caption("You’ll enter your topic, DraftWise will evaluate feasibility, then you decide whether to proceed.")

        title = st.text_input("Topic title", placeholder="e.g., Detecting phishing emails using lightweight NLP baselines")
        problem = st.text_area(
            "Problem statement (2–5 lines)",
            placeholder="What exactly are you trying to predict/measure? Why does it matter? What’s the input/output?",
            height=120,
        )
        plan = st.text_area(
            "What do you plan to do? (rough steps)",
            placeholder="e.g., pick dataset, clean it, train baseline, try 1 improvement, evaluate, write report",
            height=110,
        )
        data = st.selectbox(
            "Data situation",
            ["Public dataset available", "I will scrape (legal/allowed)", "I will create synthetic data", "I have private data (risky)"],
        )
        metric = st.text_input("Metric (optional)", placeholder="e.g., F1, accuracy, ROC-AUC, MSE, latency")
        baseline = st.text_input("Baseline (optional)", placeholder="e.g., Logistic Regression, Random Forest, BERT baseline, BM25")

        col1, col2 = st.columns([1, 1])
        with col1:
            run = st.button("Run feasibility check", type="primary", use_container_width=True)
        with col2:
            use_anyway = st.button("Use my topic without checking")

        if use_anyway:
            if not title.strip() or not problem.strip():
                st.error("Please fill at least Title and Problem statement.")
                return
            st.session_state.artifacts["selected_topic"] = {
                "idea_number": "USER",
                "title": title.strip(),
                "full_text": f"### User topic: {title.strip()}\n\n**Problem statement:**\n{problem.strip()}\n\n**Rough plan:**\n{plan.strip()}\n\n**Data situation:** {data}\n\n**Metric:** {metric.strip()}\n\n**Baseline:** {baseline.strip()}",
                "source": "user_provided",
            }
            st.success("Saved your topic. You can proceed to Plan Builder.")

        if run:
            if not title.strip() or not problem.strip():
                st.error("Please fill at least Title and Problem statement.")
                return

            prompt = _feasibility_prompt(cfg, title, problem, plan, data, metric, baseline)
            with st.spinner("Analyzing feasibility..."):
                feas_md = generate_text(prompt)

            st.session_state.artifacts["feasibility_raw"] = feas_md

        feas = st.session_state.artifacts.get("feasibility_raw")
        if feas:
            st.divider()
            st.subheader("Feasibility report")
            st.markdown(feas)

            status = _parse_status(feas)
            if status == "Green":
                st.success("Verdict: GREEN — feasible to proceed.")
            elif status == "Yellow":
                st.warning("Verdict: YELLOW — proceed after narrowing scope / fixing gaps.")
            elif status == "Red":
                st.error("Verdict: RED — likely too risky or too broad. Pivot recommended.")
            else:
                st.info("Verdict: (Could not parse status line, but report is shown above.)")

            if st.button("Use this topic (with feasibility notes)"):
                st.session_state.artifacts["selected_topic"] = {
                    "idea_number": "USER",
                    "title": title.strip(),
                    "full_text": "\n".join([
                        f"### User topic: {title.strip()}",
                        "",
                        "**Problem statement:**",
                        problem.strip(),
                        "",
                        "**Rough plan:**",
                        plan.strip(),
                        "",
                        f"**Data situation:** {data}",
                        f"**Metric:** {metric.strip()}",
                        f"**Baseline:** {baseline.strip()}",
                        "",
                        "---",
                        "",
                        "## DraftWise feasibility report",
                        feas.strip(),
                    ]),
                    "source": "user_provided_with_feasibility",
                    "feasibility_status": status,
                }
                st.success("Saved your topic + feasibility report. Proceed to Plan Builder.")

    # ---------------------------------------------------------
    # Show selected topic (common)
    # ---------------------------------------------------------
    chosen = st.session_state.artifacts.get("selected_topic")
    if chosen:
        st.divider()
        st.subheader("Selected topic (stored)")
        st.write(f"**{chosen.get('idea_number')}: {chosen.get('title')}**")
        st.text(chosen.get("full_text", ""))