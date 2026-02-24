import streamlit as st

DISCLAIMER = (
    "Ethics notice: DraftWise is meant to guide beginners and reduce overwhelm. "
    "It does not endorse or recommend submitting AI-generated work as your own. "
    "Use it to learn, plan, and structure your work, and always follow your institution’s academic integrity rules."
)

def inject_theme():
    st.markdown(
        """
        <style>
          /* Keep CSS minimal and stable. Let Streamlit theme handle widgets. */

          .block-container { max-width: 1050px; padding-top: 1.4rem; }

          .dw-subtitle{
            color: #374151;
            font-size: 1.02rem;
            margin-top: -0.2rem;
            margin-bottom: 1.2rem;
          }

          .dw-card{
            background: #ffffff;
            border: 1px solid #E5E7EB;
            border-radius: 14px;
            padding: 16px 16px 10px 16px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            margin-bottom: 0.9rem;
          }

          .dw-muted{
            color: #4B5563;
            font-size: 0.95rem;
          }

          .dw-pills{
            margin: 0.4rem 0 0.9rem 0;
          }
          .dw-pill{
            display: inline-block;
            padding: 0.22rem 0.55rem;
            margin: 0 0.35rem 0.35rem 0;
            border: 1px solid #E5E7EB;
            background: #F9FAFB;
            color: #374151;
            border-radius: 999px;
            font-size: 0.86rem;
          }

          /* Sidebar: keep it calm and readable */
          section[data-testid="stSidebar"]{
            border-right: 1px solid #E5E7EB;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

def sidebar_disclaimer():
    st.sidebar.markdown("### DraftWise")
    st.sidebar.caption("A calm mentor-style research workspace.")
    with st.sidebar.expander("Ethics notice", expanded=False):
        st.write(DISCLAIMER)

def inline_disclaimer():
    st.info(DISCLAIMER)