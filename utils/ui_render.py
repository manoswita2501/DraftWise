import streamlit as st

def render_compact(markdown_text: str, details_title: str = "Show full details"):
    """
    Assumes the model output starts with:
    ## TL;DR (read this only)
    ...
    Then other sections.
    """
    if not markdown_text or not markdown_text.strip():
        st.info("Nothing to display yet.")
        return

    text = markdown_text.strip()

    # If TL;DR heading exists, split it out
    key = "## TL;DR"
    idx = text.find(key)

    if idx == -1:
        # fallback: just show everything
        st.markdown(text)
        return

    # Show TL;DR section only (up to next '## ' heading)
    rest = text[idx:]
    parts = rest.split("\n## ", 1)

    if len(parts) == 1:
        st.markdown(text)  # only TL;DR exists
        return

    tldr_block = parts[0]
    remaining = "## " + parts[1]  # restore heading prefix

    st.markdown(tldr_block)

    with st.expander(details_title, expanded=False):
        st.markdown(remaining)