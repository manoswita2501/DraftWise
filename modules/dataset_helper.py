import streamlit as st
import pandas as pd
import numpy as np
from llm.gemini_client import generate_text, MODEL_DEFAULT


# -----------------------------
# Local profiling (no AI needed)
# -----------------------------
def _basic_profile(df: pd.DataFrame) -> dict:
    n_rows, n_cols = df.shape

    dtypes = df.dtypes.astype(str).to_dict()
    missing_pct = (df.isna().mean() * 100).round(2).to_dict()
    dup_rows = int(df.duplicated().sum())
    nunique = df.nunique(dropna=True).to_dict()

    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = [c for c in df.columns if c not in num_cols]

    likely_id = []
    if n_rows >= 50:
        for c in df.columns:
            if nunique.get(c, 0) >= 0.98 * n_rows:
                likely_id.append(c)

    top_missing = sorted(missing_pct.items(), key=lambda x: x[1], reverse=True)[:15]
    return {
        "shape": (n_rows, n_cols),
        "dtypes": dtypes,
        "missing_pct": missing_pct,
        "top_missing": top_missing,
        "dup_rows": dup_rows,
        "num_cols": num_cols,
        "cat_cols": cat_cols,
        "likely_id": likely_id,
    }


def _local_csv_report(cfg: dict, profile: dict, target_hint: str) -> str:
    n_rows, n_cols = profile["shape"]
    miss_cols = [(c, p) for c, p in profile["top_missing"] if p > 0]
    likely_id = profile["likely_id"][:10]

    lines = []
    lines.append("## Dataset overview")
    lines.append(f"- Rows: **{n_rows}**, Columns: **{n_cols}**")
    if target_hint.strip():
        lines.append(f"- Target/label (user hint): **{target_hint.strip()}**")
    lines.append("")

    lines.append("## Data quality snapshot")
    lines.append(f"- Duplicate rows: **{profile['dup_rows']}**")
    if likely_id:
        lines.append(f"- Likely ID columns (near-unique): {', '.join([f'`{c}`' for c in likely_id])}")
        lines.append("  - Do not use IDs as features; use only for joins/indexing.")
    else:
        lines.append("- Likely ID columns: **None detected**")

    if miss_cols:
        lines.append("- Missingness (top columns):")
        for c, p in miss_cols[:10]:
            lines.append(f"  - `{c}`: **{p}%** missing")
    else:
        lines.append("- Missingness: **No missing values detected** (nice).")

    lines.append("")
    lines.append("## Research-useful guidance (write this in your paper)")
    lines.append(f"- Track: **{cfg['track']}**, Goal: **{cfg['goal']}**, Degree: **{cfg['degree_level']}**, Time: **{cfg['time_days']} days**")
    lines.append("- Suggested split strategy:")
    lines.append("  - Start with a simple train/val/test split.")
    lines.append("  - If data has time/user/product identifiers, avoid random split (risk of leakage).")
    lines.append("- Leakage checks:")
    lines.append("  - Remove post-outcome columns, IDs, timestamps that reveal the answer.")
    lines.append("  - Watch for duplicates across splits.")
    lines.append("- Baseline:")
    lines.append("  - Pick a simple baseline model and report a clean metric table.")
    lines.append("- One improvement (bounded):")
    lines.append("  - One controlled change: preprocessing, encoding choice, regularization, or feature ablation.")
    lines.append("- Limitations:")
    lines.append("  - Missingness/bias, class imbalance, proxy variables, and potential confounders.")
    lines.append("")
    lines.append("## What to produce (minimum viable research)")
    lines.append("- Dataset description paragraph (shape, types, missingness).")
    lines.append("- Experimental setup (split, metrics, baseline).")
    lines.append("- 1 ablation + 1 error analysis paragraph.")
    lines.append("- Limitations section bullet list.")

    return "\n".join(lines)


# ---------------------------------------
# Dataset shortlisting (AI + decision gate)
# ---------------------------------------
def _dataset_shortlist_prompt(cfg: dict, task_type: str, data_constraint: str, notes: str) -> str:
    return f"""
You are DraftWise, a careful CS/IT research mentor.

User context:
- Goal: {cfg["goal"]}
- Help level: {cfg["help_level"]}
- Degree: {cfg["degree_level"]}
- Track: {cfg["track"]}
- Time: {cfg["time_days"]} days
- Paper type: {cfg["paper_type"]}

User needs help picking a dataset.
Task type: {task_type}
Data constraint: {data_constraint}
Notes (optional): {notes.strip()}

Output requirements:
- Markdown only. No JSON. No code fences.
- Provide 5 dataset/source options (not more than 5).
- For each option, use this template:

### Option <n>: <Dataset/Source name>
- What it enables (1 line):
- Why it's feasible in {cfg["time_days"]} days (1 line):
- Baseline (finishable in 1 day):
- One bounded "research contribution" angle:
- Main risk (leakage/imbalance/licensing/noise):
- Mitigation (1 line):

Then end with:
**Recommendation:** Option <n>
**Reason (2–3 lines):** ...

Rules:
- Prefer public datasets when possible.
- Keep the advice practical for CS/IT students.
- Do not include raw URLs.
""".strip()


def _extract_options(markdown_text: str):
    # Looks for headings: ### Option n: Name
    import re
    lines = markdown_text.splitlines()
    idxs = []
    pat = r"^###\s+Option\s+(\d+)\s*:\s*(.+?)\s*$"
    for i, line in enumerate(lines):
        m = re.match(pat, line.strip())
        if m:
            idxs.append((i, int(m.group(1)), m.group(2).strip()))
    out = []
    for k, (start_i, n, title) in enumerate(idxs):
        end_i = idxs[k + 1][0] if k + 1 < len(idxs) else len(lines)
        block = "\n".join(lines[start_i:end_i]).strip()
        out.append({"n": n, "title": title, "block": block})
    return out


def render_dataset_helper(cfg):
    st.subheader("Dataset Helper")
    st.write("Two paths: get help shortlisting a dataset, or upload a CSV for EDA + paper-ready narrative.")

    mode = st.radio(
        "What do you want to do?",
        ["Help me pick a dataset (shortlist)", "I have a CSV (analyze my dataset)"],
        index=0,
        horizontal=True,
    )

    # -------------------------
    # Mode 1: dataset shortlist
    # -------------------------
    if mode.startswith("Help me pick"):
        st.markdown("### Dataset shortlist (guided choice)")
        st.caption("You’ll get a short list. You still choose, and you justify your choice (2–3 lines).")

        task_type = st.selectbox(
            "Task type",
            ["Classification", "Regression", "Clustering", "Information Retrieval / Search", "NLP (text)", "Computer Vision", "Systems / Logs", "Cybersecurity"],
        )
        data_constraint = st.selectbox(
            "Data constraint",
            ["Only public datasets", "Public + scraping is okay", "Public + synthetic data is okay"],
        )
        notes = st.text_area(
            "Optional notes",
            placeholder="e.g., I want something healthcare-ish, I want minimal preprocessing, I want an explainable baseline...",
            height=90,
        )

        c1, c2 = st.columns([1, 1])
        with c1:
            gen = st.button("Generate shortlist", type="primary", use_container_width=True)
        with c2:
            pass

        if gen:
            st.session_state.artifacts["dataset_shortlist_raw"] = None
            st.session_state.artifacts["dataset_shortlist_options"] = None
            st.session_state.artifacts["dataset_choice"] = None

            prompt = _dataset_shortlist_prompt(cfg, task_type, data_constraint, notes)
            with st.status("Generating dataset shortlist...", expanded=False) as status:
                raw = generate_text(prompt)
                status.update(label="Shortlist generated.", state="complete", expanded=False)

            st.session_state.artifacts["dataset_shortlist_raw"] = raw
            st.session_state.artifacts["dataset_shortlist_options"] = _extract_options(raw)

        raw = st.session_state.artifacts.get("dataset_shortlist_raw")
        if not raw:
            st.info("Click **Generate shortlist** to get 5 options.")
            return

        st.markdown(raw)

        options = st.session_state.artifacts.get("dataset_shortlist_options") or []
        if not options:
            st.warning("Could not detect structured options. You can still use the shortlist above manually.")
            return

        st.divider()
        st.markdown("### Decision gate (you choose)")
        titles = [f'Option {o["n"]}: {o["title"]}' for o in options]
        pick = st.radio("Pick one option to proceed", titles, index=0)

        why = st.text_area(
            "Why did you choose this dataset? (2–3 lines)",
            placeholder="I picked this because... It fits my time window because... My contribution will be...",
            height=90,
        )
        risk = st.text_input(
            "One risk you anticipate (short)",
            placeholder="e.g., class imbalance, noisy labels, leakage risk, licensing constraints",
        )

        if st.button("Confirm dataset choice"):
            chosen = options[titles.index(pick)]
            if len(why.strip()) < 15:
                st.error("Write a slightly longer justification (at least ~2 lines).")
                return
            if not risk.strip():
                st.error("Please state at least one anticipated risk.")
                return

            st.session_state.artifacts["dataset_choice"] = {
                "mode": "shortlist",
                "task_type": task_type,
                "data_constraint": data_constraint,
                "notes": notes.strip(),
                "picked_option": chosen,
                "justification": why.strip(),
                "anticipated_risk": risk.strip(),
            }
            st.success(f"Saved dataset choice: {chosen['title']}")

        dc = st.session_state.artifacts.get("dataset_choice")
        if dc:
            st.divider()
            st.subheader("Saved dataset choice (for Writing Studio)")
            st.write(f"**{dc['picked_option']['title']}**")
            st.caption("Your justification:")
            st.write(dc["justification"])
            st.caption("Anticipated risk:")
            st.write(dc["anticipated_risk"])

            report_md = "\n".join([
                "## Dataset decision (DraftWise)",
                f"- Picked: **{dc['picked_option']['title']}**",
                f"- Task type: **{dc['task_type']}**",
                f"- Constraint: **{dc['data_constraint']}**",
                "",
                "### Justification",
                dc["justification"],
                "",
                "### Anticipated risk",
                dc["anticipated_risk"],
                "",
                "### DraftWise option details",
                dc["picked_option"]["block"],
            ])

            st.download_button(
                "Download dataset decision as .md",
                data=report_md.encode("utf-8"),
                file_name="draftwise_dataset_decision.md",
                mime="text/markdown",
            )

        return

    # -------------------------
    # Mode 2: CSV analysis
    # -------------------------
    st.markdown("### CSV analysis (EDA + research narrative)")
    up = st.file_uploader("Upload CSV", type=["csv"])
    if not up:
        st.info("Upload a CSV to continue.")
        st.stop()

    with st.status("Loading CSV...", expanded=False) as status:
        try:
            df = pd.read_csv(up)
        except Exception as e:
            status.update(label="Failed to load CSV.", state="error", expanded=True)
            st.error(f"Could not read CSV: {e}")
            st.stop()
        status.update(label="CSV loaded.", state="complete", expanded=False)

    st.success("Loaded dataset.")
    st.dataframe(df.head(25), use_container_width=True)

    target_hint = st.text_input(
        "Optional: what do you think is the target/label column?",
        placeholder="e.g., label, sentiment, price, churn",
    )

    profile = _basic_profile(df)

    with st.expander("Basic stats", expanded=True):
        n_rows, n_cols = profile["shape"]
        a, b, c = st.columns(3)
        a.metric("Rows", n_rows)
        b.metric("Columns", n_cols)
        c.metric("Duplicate rows", profile["dup_rows"])

        st.write("Likely ID columns (near-unique):")
        st.write(profile["likely_id"] if profile["likely_id"] else "None detected")

        st.write("Missingness (top 15):")
        miss_table = pd.DataFrame(profile["top_missing"], columns=["column", "missing_%"])
        st.dataframe(miss_table, use_container_width=True)

        st.write("Numeric columns (sample):")
        st.write(profile["num_cols"][:20])

        st.write("Non-numeric columns (sample):")
        st.write(profile["cat_cols"][:20])

    st.divider()
    st.subheader("Narrative report")

    report_mode = st.radio(
        "Report mode",
        ["Local (fast, no AI)", f"AI-assisted ({MODEL_DEFAULT})"],
        index=0,
        horizontal=True,
    )

    if st.button("Generate dataset report", type="primary", use_container_width=True):
        if report_mode.startswith("Local"):
            report = _local_csv_report(cfg, profile, target_hint)
        else:
            summary = {
                "rows": profile["shape"][0],
                "cols": profile["shape"][1],
                "target_hint": target_hint.strip(),
                "likely_id": profile["likely_id"][:10],
                "top_missing": profile["top_missing"][:10],
                "dup_rows": profile["dup_rows"],
                "num_cols_sample": profile["num_cols"][:15],
                "cat_cols_sample": profile["cat_cols"][:15],
            }
            prompt = f"""
You are DraftWise. Write a mentor-style dataset analysis for a beginner CS/IT researcher.

User context:
- Goal: {cfg["goal"]}
- Help level: {cfg["help_level"]}
- Degree: {cfg["degree_level"]}
- Track: {cfg["track"]}
- Time: {cfg["time_days"]} days
- Paper type: {cfg["paper_type"]}

Dataset summary (no raw data, only stats):
{summary}

Output requirements:
- Markdown only. No JSON. No code fences.
- Tie it to research writing:
  - What this dataset supports as a research question
  - Leakage risks + confounders
  - Split strategy suggestion
  - Baseline + one bounded improvement idea
  - What to write in “Dataset” and “Experimental Setup”
- Keep it actionable and bounded for the time window.
""".strip()
            with st.status("Generating dataset report...", expanded=False) as status:
                try:
                    report = generate_text(prompt)
                except Exception as e:
                    status.update(label="AI request failed.", state="error", expanded=True)
                    st.error(f"AI request failed: {e}")
                    st.info("Falling back to local report.")
                    report = _local_csv_report(cfg, profile, target_hint)
                else:
                    status.update(label="Dataset report generated.", state="complete", expanded=False)

        st.session_state.artifacts["dataset"] = {
            "mode": "csv",
            "target_hint": target_hint.strip(),
            "profile": {
                "shape": profile["shape"],
                "dup_rows": profile["dup_rows"],
                "likely_id": profile["likely_id"],
                "top_missing": profile["top_missing"][:20],
                "num_cols": profile["num_cols"][:50],
                "cat_cols": profile["cat_cols"][:50],
            },
            "report_md": report,
        }
        st.success("Dataset report saved to workspace.")

    ds = st.session_state.artifacts.get("dataset")
    if not ds:
        st.info("Click **Generate dataset report** to create a reusable narrative.")
        return

    st.markdown(ds["report_md"])
    reviewed = st.checkbox("I reviewed and edited this output.", value=False, key="dataset_reviewed")
    st.download_button(
        "Download report as .md",
        data=ds["report_md"].encode("utf-8"),
        file_name="draftwise_dataset_report.md",
        mime="text/markdown",
        disabled=not reviewed
    )