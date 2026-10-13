from pathlib import Path

import pandas as pd
import streamlit as st

from email_analyzer import (
    EmailAnalysis,
    analyze_files,
    answer_follow_up,
    build_follow_up,
)


DEFAULT_DATASET = Path(
    r"C:\Users\shrut\Downloads\Emails_Dataset-20261010T064922Z-1-001\Emails_Dataset"
)

st.set_page_config(page_title="Email Analysis & Prioritization", page_icon="✉️", layout="wide")
st.title("✉️ Email Analysis & Prioritization")
st.caption("Local, explainable analysis of PDF emails. No email content leaves this machine.")

with st.sidebar:
    st.header("Dataset")
    dataset_path = st.text_input("Dataset folder", value=str(DEFAULT_DATASET))
    uploaded_files = st.file_uploader(
        "Or upload PDF emails",
        type=["pdf"],
        accept_multiple_files=True,
    )
    analyze_button = st.button("Analyze emails", type="primary", use_container_width=True)
    st.divider()
    st.markdown(
        "**Criteria**\n"
        "- Spam: promotional and suspicious-content indicators\n"
        "- Validity: sender structure and contextual validity\n"
        "- Importance: business impact, urgency, risk, and action required"
    )


def load_inputs() -> list[Path] | list[object]:
    if uploaded_files:
        return uploaded_files
    folder = Path(dataset_path)
    if not folder.is_dir():
        st.error(f"Dataset folder does not exist: {folder}")
        return []
    return sorted(folder.glob("*.pdf"))


if analyze_button or "analyses" not in st.session_state:
    inputs = load_inputs()
    if inputs:
        with st.spinner("Extracting and analyzing email PDFs..."):
            st.session_state.analyses = analyze_files(inputs)
        st.success(f"Analyzed {len(st.session_state.analyses)} email(s).")

analyses: list[EmailAnalysis] = st.session_state.get("analyses", [])
if not analyses:
    st.info("Choose the supplied dataset folder or upload PDF files, then click Analyze emails.")
    st.stop()

counts = pd.Series([email.importance for email in analyses]).value_counts()
spam_count = sum(email.spam_status == "Spam" for email in analyses)
invalid_count = sum(email.validity == "Invalid" for email in analyses)
high_count = sum(email.importance == "High" for email in analyses)
metric_columns = st.columns(4)
metric_columns[0].metric("Emails analyzed", len(analyses))
metric_columns[1].metric("High importance", high_count)
metric_columns[2].metric("Spam / suspicious", spam_count)
metric_columns[3].metric("Invalid sender", invalid_count)

st.subheader("Results")
table = pd.DataFrame([email.as_row() for email in analyses])
visible_columns = [
    "email_id", "subject", "sender", "spam_status", "validity", "importance", "reason"
]
st.dataframe(
    table[visible_columns].rename(
        columns={
            "email_id": "Email ID",
            "subject": "Subject",
            "sender": "Sender",
            "spam_status": "Spam status",
            "validity": "Validity",
            "importance": "Importance",
            "reason": "Reason",
        }
    ),
    use_container_width=True,
    hide_index=True,
)

st.subheader("Inspect an email")
selected_id = st.selectbox("Email", [email.email_id for email in analyses])
selected = next(email for email in analyses if email.email_id == selected_id)
left, right = st.columns(2)
with left:
    st.write(f"**Subject:** {selected.subject}")
    st.write(f"**From:** {selected.sender}")
    st.write(f"**Reply-To:** {selected.reply_to}")
    st.write(f"**To:** {selected.recipient}")
    st.write(f"**Date:** {selected.date}")
with right:
    st.write(f"**Classification:** {selected.spam_status} | {selected.validity} | {selected.importance}")
    st.write(f"**Sender identity:** {selected.sender_identity}")
    st.write(f"**Sender context:** {selected.sender_context}")
    st.write(f"**Reason:** {selected.reason}")
with st.expander("Extracted email text"):
    st.text(selected.text)

st.subheader("Follow-up comparison")
st.write(build_follow_up(analyses))
question = st.text_input(
    "Ask about the analyzed emails",
    placeholder="For example: compare EML-002 and EML-040",
)
if question:
    st.info(answer_follow_up(question, analyses))
st.download_button(
    "Download analysis CSV",
    data=table.to_csv(index=False).encode("utf-8"),
    file_name="email_analysis_results.csv",
    mime="text/csv",
)
