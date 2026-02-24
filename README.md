# DraftWise

DraftWise is a structured research companion for CS/IT projects and papers. It helps you move from a rough idea to a workable plan, dataset direction, readable draft sections, and paper/section-level feedback — without feeling overwhelmed.

> **Ethics note (important):** DraftWise is meant to guide and support learning. It does **not** endorse or recommend submitting AI-generated work as your own. Always follow your institution’s academic integrity policies, verify outputs, and write/own your final submission.

## Key Features (5 Tabs)

### 1) Topic Picker:
- Generates a shortlist of feasible project/research topics tailored to your goal, degree level, time window, and track
- Lets you **bring your own topic** and runs a feasibility check before proceeding

### 2) Plan Builder:
- Converts the selected topic into a bounded research plan: hypotheses, metrics, baseline vs improvement, ablations, failure modes, reproducibility checklist, and timeline
- Supports **regenerate** and **shorten** to keep outputs focused

### 3) Dataset Helper:
2 paths:
- **Help me pick a dataset:** generates a short dataset shortlist and makes you finalize a choice with a justification (decision gate)
- **I have a CSV:** runs basic EDA + leakage cues + a paper-ready dataset narrative

### 4) Writing Studio:
- Generates paper sections (e.g., Abstract, Intro, Method, Setup, Limitations) using your selected topic + plan + dataset context
- Supports **Template vs Draft** writing modes
- Supports **regenerate/shorten per section** and a combined draft download (with review gate)

### 5) Paper Analyzer:
2 modes:
- **Section Analyzer:** paste your draft section text and get mentor/reviewer feedback + rewrite suggestions
- **Full Paper Analyzer:** upload a paper PDF for a structured breakdown (summary, contributions, assumptions, limitations, reproducibility gaps, replication checklist, reuse ideas)

## Tech Stack
- **Frontend:** Streamlit
- **LLM:** Google Gemini API (gemini-2.5-flash-lite)
- **Data/Utilities:** Python, Pandas, NumPy
- **PDF Parsing:** PyPDF
- **State:** Session state + Export/Import **Project Pack** (JSON)

## Future Improvements I hope to incorporate
- Stronger PDF handling for scanned papers (OCR)
- Better dataset discovery (optional curated sources/search integration)
- Citation helper (BibTeX placeholders, related-work assist)
