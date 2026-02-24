import streamlit as st
from pypdf import PdfReader
from llm.gemini_client import generate_text, MODEL_DEFAULT
from llm.prompts import shorten_prompt
#from utils.ui_render import render_compact

MAX_CHARS = 45000  # safety cap for model context

# -----------------------------
# PDF utilities
# -----------------------------
def _extract_pdf_text(file) -> str:
    reader = PdfReader(file)
    texts = []
    for page in reader.pages:
        t = page.extract_text() or ""
        if t.strip():
            texts.append(t)
    return "\n\n".join(texts).strip()


def _truncate(text: str, max_chars: int = MAX_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    head = text[: int(max_chars * 0.7)]
    tail = text[-int(max_chars * 0.3) :]
    return head + "\n\n[...TRUNCATED...]\n\n" + tail


# -----------------------------
# Prompts (kept local to avoid prompt import drift)
# -----------------------------
def _section_analyzer_prompt(cfg: dict, section_type: str, section_text: str, tone: str) -> str:
    depth = cfg.get("output_depth", "Balanced")

    budget = {
        "Short": "Keep total output under ~400 words. Max 5 bullets per section. Max 2 lines per bullet.",
        "Balanced": "Keep total output under ~850 words. Max 7 bullets per section. Max 2–3 lines per bullet.",
        "Detailed": "Keep output structured (no rambling). Max 10 bullets per section. Max 3 lines per bullet.",
    }.get(depth, "Keep total output under ~850 words. Max 7 bullets per section. Max 2–3 lines per bullet.")

    return f"""
You are DraftWise, a CS/IT research writing mentor.

User context:
- Goal: {cfg["goal"]}
- Help level: {cfg["help_level"]}
- Degree: {cfg["degree_level"]}
- Track: {cfg["track"]}
- Paper type: {cfg["paper_type"]}
- Time window: {cfg["time_days"]} days
- Output depth: {depth}

Task:
The student pasted the section: {section_type}. Give feedback on this section ONLY.

Tone:
{tone}

Hard rules:
- Markdown only. No JSON. No code fences.
- {budget}
- Do NOT encourage unethical submission. If you detect fabricated results/claims, flag them clearly.
- Do not ask follow-up questions. Use placeholders like [CITATION_TBD], [RESULTS_TBD] where needed.

Output MUST start with these sections (in this order):

## TL;DR (read this only)
- 4–6 bullets: what to fix first.

## Next actions
- Exactly 3 bullets: the next edits to make in order.

## Risks
- Up to 3 bullets: what could harm credibility (overclaims, missing citations, logical gaps).

Then continue with:

## What’s working
- 2–5 bullets.

## What’s weak
- 2–6 bullets.

## Section-specific checklist
- Missing components (bullets)
- Evidence alignment (bullets)

## High-ROI line edits (quote short snippets)
- Quote (max 2 lines) → Fix (1–2 lines)
(Provide 3–6 items max)

## Suggested rewrite (only if output depth is Balanced or Detailed)
- If {depth} is Short: SKIP this section.
- Otherwise: rewrite the section to be clearer, same approximate length, and avoid any fabricated results.

Section text:
\"\"\"
{section_text}
\"\"\"
""".strip()

def _paper_analyzer_prompt(cfg: dict, paper_text: str, mode: str) -> str:
    depth = cfg.get("output_depth", "Balanced")

    budget = {
        "Short": "Keep total output under ~600 words. Max 6 bullets per section. Max 2 lines per bullet.",
        "Balanced": "Keep total output under ~1200 words. Max 8 bullets per section. Max 2–3 lines per bullet.",
        "Detailed": "Keep output structured (no rambling). Max 12 bullets per section. Max 3 lines per bullet.",
    }.get(depth, "Keep total output under ~1200 words. Max 8 bullets per section. Max 2–3 lines per bullet.")

    reviewer_extra = (
        "## Reviewer notes\n"
        "- Strengths (3–5 bullets)\n"
        "- Weaknesses (3–6 bullets)\n"
        "- Top 3 fixes the authors should do next (exactly 3 bullets)\n"
    )

    reviewer_block = "\n\n" + reviewer_extra if "Reviewer" in mode else ""

    return f"""
You are DraftWise, a CS/IT research mentor helping users understand papers.

User context:
- Goal: {cfg["goal"]}
- Degree: {cfg["degree_level"]}
- Track: {cfg["track"]}
- Paper type they aim to write: {cfg["paper_type"]}
- Output depth: {depth}

Analysis mode: {mode}
- Reader mode = explain and extract.
- Reviewer mode = critique carefully.

Hard rules:
- Markdown only. No JSON. No code fences.
- {budget}
- Be faithful to the paper. If uncertain, say "Not clear from the text provided".
- Do not invent datasets, metrics, results, or claims.

Output MUST start with these sections (in this order):

## TL;DR (read this only)
- 6–10 bullets maximum: what the paper is, what it claims, and what matters.

## Next actions
- Exactly 3 bullets: how a student should use this paper (present it / reuse it / replicate it).

## Risks
- Up to 3 bullets: likely weak points (missing details, unclear evaluation, etc.).

Then continue with:

## One-paragraph plain-English summary
(5–7 lines, beginner friendly)

## Problem + setting
- Problem:
- Why it matters:
- Setting/constraints:

## Main contributions (3–6 bullets)
- ...

## Key assumptions
- ...

## Method overview (high level)
- Inputs:
- Core idea:
- Difference from baselines:

## Experiments & evidence
- Datasets/benchmarks:
- Metrics:
- Baselines:
- What improved (qualitative if numbers missing):

## Limitations and failure cases
- ...

## Reproducibility gap report
- Missing items to reproduce (bullets)
- What’s easy vs hard to reproduce (bullets)

## Replication checklist
- Environment/setup:
- Data:
- Training/inference:
- Evaluation:
- Reporting:

## How you can reuse this (for {cfg["track"]})
- 3–6 reuse directions (bullets)

## Citation-ready summary (3–4 sentences)
Use placeholders: [AUTHOR_TBD], [YEAR_TBD], [PAPER_TITLE_TBD]{reviewer_block}

Paper text:
--- BEGIN PAPER TEXT ---
{paper_text}
--- END PAPER TEXT ---
""".strip()

# -----------------------------
# UI
# -----------------------------
def render_paper_analyzer(cfg):
    st.subheader("Paper Analyzer")
    st.write("Two options: analyze a draft section you wrote, or analyze a full paper PDF.")

    mode = st.radio(
        "Choose analysis type",
        ["Section Analyzer (paste text)", "Full Paper Analyzer (upload PDF)"],
        index=0,
        horizontal=True,
    )

    # -------------------------
    # Section Analyzer
    # -------------------------
    if mode.startswith("Section Analyzer"):
        section_type = st.selectbox(
            "Which section is this?",
            [
                "Abstract",
                "Introduction",
                "Related Work",
                "Method",
                "Experimental Setup",
                "Results",
                "Discussion",
                "Limitations",
                "Conclusion",
            ],
        )

        tone = st.radio(
            "Feedback tone",
            ["Mentor mode (supportive)", "Reviewer mode (strict)"],
            index=0,
            horizontal=True,
        )

        section_text = st.text_area(
            "Paste your section text here",
            height=260,
            placeholder="Paste the exact text from your draft (no need to format).",
        )

        col1, col2 = st.columns([1, 1])
        with col1:
            run = st.button("Analyze this section", type="primary", use_container_width=True)
        with col2:
            clear = st.button("Clear section analysis", use_container_width=True)

        if clear:
            st.session_state.artifacts["paper_analysis"] = None
            st.rerun()

        if run:
            if len(section_text.strip()) < 60:
                st.error("Paste a bit more text (at least a few paragraphs).")
                st.stop()

            st.session_state.artifacts["paper_analysis"] = None
            prompt = _section_analyzer_prompt(cfg, section_type, section_text.strip(), tone)

            with st.status("Analyzing section...", expanded=False) as status:
                try:
                    report = generate_text(prompt)
                except Exception as e:
                    status.update(label="Section analysis failed.", state="error", expanded=True)
                    st.error(f"AI request failed: {e}")
                    st.stop()
                status.update(label="Section analysis complete.", state="complete", expanded=False)

            st.session_state.artifacts["paper_analysis"] = {
                "type": "section",
                "section_type": section_type,
                "tone": tone,
                "report_md": report,
                "last_prompt": prompt,
            }

        pa = st.session_state.artifacts.get("paper_analysis")
        if not pa:
            st.info("Paste a section and click **Analyze this section**.")
            return

        st.success(f"Section analysis ready: {pa.get('section_type','')}")
        c1, c2 = st.columns(2)
        with c1:
            regen_btn = st.button("Regenerate analysis", key="regen_section_analysis")
        with c2:
            shorten_btn = st.button("Shorten analysis", key="short_any_analysis")
            
        if regen_btn:
            with st.status("Regenerating analysis...", expanded=False) as status:
                try:
                    new_md = generate_text(pa["last_prompt"])
                except Exception as e:
                    status.update(label="Regeneration failed.", state="error", expanded=True)
                    st.error(f"AI request failed: {e}")
                    st.stop()
                status.update(label="Analysis regenerated.", state="complete", expanded=False)

            st.session_state.artifacts["paper_analysis"]["report_md"] = new_md
            st.rerun()
    
        if shorten_btn:
            prompt = shorten_prompt(cfg, pa["report_md"])
            with st.status("Shortening analysis...", expanded=False) as status:
                new_md = generate_text(prompt)
                status.update(label="Analysis shortened.", state="complete", expanded=False)
            st.session_state.artifacts["paper_analysis"]["report_md"] = new_md
            st.rerun()

        st.markdown(st.session_state.artifacts["paper_analysis"]["report_md"])
        #render_compact(pa["report_md"], details_title="Show full analysis")

        reviewed = st.checkbox("I reviewed and edited this output.", value=False, key="section_reviewed")
        st.download_button(
            "Download section feedback (.md)",
            data=pa["report_md"].encode("utf-8"),
            file_name="draftwise_section_feedback.md",
            mime="text/markdown",
            disabled=not reviewed
        )
        return

    # -------------------------
    # Full Paper Analyzer
    # -------------------------
    analysis_mode = st.radio(
        "Full paper mode",
        ["Reader mode (extract + explain)", "Reviewer mode (critique)"],
        index=0,
        horizontal=True,
    )

    up = st.file_uploader("Upload PDF", type=["pdf"])
    if not up:
        st.info("Upload a PDF to continue.")
        st.stop()

    show_raw = st.checkbox("Show extracted text preview", value=False)

    col1, col2 = st.columns([1, 1])
    with col1:
        run = st.button("Analyze paper", type="primary", use_container_width=True)
    with col2:
        clear = st.button("Clear paper analysis", use_container_width=True)

    if clear:
        st.session_state.artifacts["paper_analysis"] = None
        st.rerun()

    if run:
        st.session_state.artifacts["paper_analysis"] = None

        with st.status("Extracting text from PDF...", expanded=False) as status:
            try:
                text = _extract_pdf_text(up)
            except Exception as e:
                status.update(label="PDF extraction failed.", state="error", expanded=True)
                st.error(f"PDF text extraction failed: {e}")
                st.stop()
            status.update(label="Text extracted.", state="complete", expanded=False)

        if not text:
            st.error("Could not extract text from this PDF (it might be scanned).")
            st.info("If it is scanned, we’ll need OCR later. For now, try a text-based PDF.")
            return

        short_text = _truncate(text)

        if show_raw:
            st.text_area("Extracted text (preview)", short_text[:6000], height=240)

        prompt = _paper_analyzer_prompt(cfg, short_text, analysis_mode)

        with st.status("Generating paper analysis...", expanded=False) as status:
            try:
                report = generate_text(prompt)
            except Exception as e:
                status.update(label="Paper analysis failed.", state="error", expanded=True)
                st.error(f"AI request failed: {e}")
                st.stop()
            status.update(label="Paper analysis complete.", state="complete", expanded=False)

        st.session_state.artifacts["paper_analysis"] = {
            "type": "paper",
            "mode": analysis_mode,
            "chars_used": len(short_text),
            "report_md": report,
            "last_prompt": prompt,
        }

    pa = st.session_state.artifacts.get("paper_analysis")
    if not pa:
        st.info("Click **Analyze paper** to generate the report.")
        return

    st.success(f"Paper analysis ready (chars sent: {pa.get('chars_used', 0)}).")
    c1, c2 = st.columns(2)
    with c1:
        regen_btn = st.button("Regenerate analysis", key="regen_paper_analysis")
    with c2:
        shorten_btn = st.button("Shorten analysis", key="short_any_analysis")  
        
    if regen_btn:
        with st.status("Regenerating analysis...", expanded=False) as status:
            try:
                new_md = generate_text(pa["last_prompt"])
            except Exception as e:
                status.update(label="Regeneration failed.", state="error", expanded=True)
                st.error(f"AI request failed: {e}")
                st.stop()
            status.update(label="Analysis regenerated.", state="complete", expanded=False)

        st.session_state.artifacts["paper_analysis"]["report_md"] = new_md
        st.rerun()
    
    if shorten_btn:
        prompt = shorten_prompt(cfg, pa["report_md"])
        with st.status("Shortening analysis...", expanded=False) as status:
            new_md = generate_text(prompt)
            status.update(label="Analysis shortened.", state="complete", expanded=False)
        st.session_state.artifacts["paper_analysis"]["report_md"] = new_md
        st.rerun()

    st.markdown(st.session_state.artifacts["paper_analysis"]["report_md"])
    
    #render_compact(pa["report_md"], details_title="Show full analysis")

    reviewed = st.checkbox("I reviewed and edited this output.", value=False, key="paper_reviewed")
    st.download_button(
        "Download paper analysis (.md)",
        data=pa["report_md"].encode("utf-8"),
        file_name="draftwise_paper_analysis.md",
        mime="text/markdown",
        disabled=not reviewed
    )