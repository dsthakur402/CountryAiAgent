import os

import streamlit as st

# Streamlit Cloud exposes secrets via st.secrets; copy it into env so the
# rest of the code can stay plain-python and unaware of Streamlit.
if "GOOGLE_API_KEY" in st.secrets and not os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]

from config import setup_logging  # noqa: E402
from agent import run  # noqa: E402

setup_logging()

st.set_page_config(page_title="Country Info Agent", page_icon=None)
st.title("Country Info Agent")
st.caption("Ask me about any country. Data comes from restcountries.com.")

EXAMPLES = [
    "What is the population of Germany?",
    "What currency does Japan use?",
    "What is the capital and population of Brazil?",
    "Compare the area of India and Pakistan.",
    "Which countries border France?",
]

with st.sidebar:
    st.markdown("**Try one of these**")
    for q in EXAMPLES:
        if st.button(q, use_container_width=True, key=f"ex-{q}"):
            st.session_state["pending"] = q
    st.markdown("---")
    if st.button("Clear chat", use_container_width=True):
        st.session_state["history"] = []
        st.rerun()

if "history" not in st.session_state:
    st.session_state["history"] = []

for role, text in st.session_state["history"]:
    with st.chat_message(role):
        st.markdown(text)

pending = st.session_state.pop("pending", None)
user_input = pending or st.chat_input("Ask a question about a country")

if user_input:
    st.session_state["history"].append(("user", user_input))
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                state = run(user_input)
                answer = state.get("answer") or "(no answer produced)"
            except Exception as exc:
                answer = f"Something went wrong: {exc}"
        st.markdown(answer)

    st.session_state["history"].append(("assistant", answer))
