import os
from datetime import datetime

import streamlit as st
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="SOP Copilot", page_icon="📘", layout="wide")

def build_system(mode: str, query: str) -> str:
    tasks = {
        "Summarize": "Summarize the SOP into: Purpose, Scope, Key Steps, Roles, Compliance.",
        "Checklist": "Convert the SOP into a structured checklist grouped by phases.",
        "Risk Assessment": "Analyze risks in a markdown table: Risk | Severity | Mitigation.",
        "Step Guide": "Create a numbered step-by-step guide for technicians.",
        "Incident Response": "Create an incident response playbook.",
        "Custom Query": f"Answer this question only from the SOP context: {query}"
    }

    return f"""You are a secure SOP agent with ZERO external knowledge.
Your ONLY source of truth is the text inside <SOP_CONTEXT> tags.
If the request is NOT fully answerable from <SOP_CONTEXT>, output EXACTLY:
provided query is out of context
Task: {tasks[mode]}"""

if "result" not in st.session_state:
    st.session_state.result = ""
if "token_usage" not in st.session_state:
    st.session_state.token_usage = None

with st.sidebar:
    api_key = os.getenv("GROQ_API_KEY") or st.text_input("Groq API Key", type="password", key="api_key")
    model = st.selectbox(
        "Model",
        ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
        key="model"
    )
    mode = st.selectbox(
        "Mode",
        ["Summarize", "Checklist", "Risk Assessment", "Step Guide", "Incident Response", "Custom Query"],
        key="mode"
    )
    temp = st.slider("Temperature", 0.0, 1.0, 0.1, 0.1, key="temp")
    max_tok = st.slider("Max Tokens", 256, 4096, 1200, 128, key="max_tok")

st.title("📘 SOP Copilot")

with st.form("sop_form"):
    method = st.radio("Input method", ["Paste Text", "Upload File"], horizontal=True, key="method")

    sop = ""
    if method == "Paste Text":
        sop = st.text_area(
            "SOP Content",
            height=280,
            placeholder="Paste your SOP here...",
            key="sop_text"
        )
    else:
        uploaded = st.file_uploader("Upload SOP", type=["txt", "md", "pdf"], key="uploaded_file")
        if uploaded:
            try:
                if uploaded.type == "application/pdf":
                    import PyPDF2
                    reader = PyPDF2.PdfReader(uploaded)
                    sop = "\n".join(page.extract_text() or "" for page in reader.pages)
                else:
                    sop = uploaded.read().decode("utf-8")
                st.success(f"Loaded: {uploaded.name}")
            except Exception as e:
                st.error(f"File read error: {e}")

    query = ""
    if mode == "Custom Query":
        query = st.text_input(
            "Your Question",
            placeholder="Ask something only about the SOP...",
            key="custom_query"
        )

    submitted = st.form_submit_button("🚀 Generate Output")

if submitted:
    if not api_key:
        st.error("Please provide a Groq API Key.")
    elif not sop.strip():
        st.warning("Please provide SOP content.")
    elif mode == "Custom Query" and not query.strip():
        st.warning("Please enter a question.")
    else:
        user_msg = f"<SOP_CONTEXT>\n{sop}\n</SOP_CONTEXT>"
        if mode == "Custom Query":
            user_msg += f"\n<USER_QUERY>\n{query}\n</USER_QUERY>"

        try:
            with st.spinner("Processing SOP..."):
                client = Groq(api_key=api_key)
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": build_system(mode, query)},
                        {"role": "user", "content": user_msg}
                    ],
                    temperature=temp,
                    max_tokens=max_tok
                )

                st.session_state.result = resp.choices[0].message.content.strip()
                st.session_state.token_usage = getattr(resp.usage, "total_tokens", None)

        except Exception as e:
            st.error(f"Groq error: {e}")

if st.session_state.result:
    if st.session_state.result == "provided query is out of context":
        st.info("provided query is out of context")
    else:
        st.subheader("Output")
        st.markdown(st.session_state.result)

        st.download_button(
            "⬇ Download Markdown",
            st.session_state.result,
            file_name=f"sop_output_{datetime.now():%H%M%S}.md",
            mime="text/markdown",
            key="download_btn"
        )

        if st.session_state.token_usage is not None:
            st.caption(f"Tokens used: {st.session_state.token_usage}")