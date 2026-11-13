"""Streamlit interface for build and error log summarization."""

from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src.llm_summarizer import (
    InvalidSummaryError,
    LLMServiceError,
    MissingAPIKeyError,
    summarize_log,
)
from src.log_parser import read_log_file

PROJECT_ROOT = Path(__file__).parent
SAMPLE_DIR = PROJECT_ROOT / "samples"

load_dotenv(PROJECT_ROOT / ".env")

st.set_page_config(page_title="Build Log Summarizer", page_icon="🛠️", layout="wide")
st.title("LLM-Based Build/Error-Log Summarization")
st.write(
    "Turn long software build logs into a clear explanation of the failure, "
    "its evidence, and practical next steps."
)

source = st.radio(
    "Choose a log source",
    ("Paste log", "Upload file", "Sample log"),
    horizontal=True,
)
log_text = ""
if source == "Paste log":
    log_text = st.text_area(
        "Paste a build or error log",
        height=250,
        placeholder="Paste log output here...",
    )
elif source == "Upload file":
    uploaded_file = st.file_uploader(
        "Choose a .log or .txt file",
        type=["log", "txt"],
    )
    if uploaded_file is not None:
        try:
            log_text = read_log_file(uploaded_file)
        except (ValueError, OSError) as exc:
            st.error(str(exc))
else:
    sample_files = sorted(SAMPLE_DIR.glob("*.log"))
    sample_names = [path.name for path in sample_files]
    selected_sample = st.selectbox("Choose a sample", sample_names)
    if selected_sample:
        try:
            log_text = read_log_file(SAMPLE_DIR / selected_sample)
            st.text_area("Sample log preview", log_text, height=200, disabled=True)
        except (ValueError, OSError) as exc:
            st.error(str(exc))

api_key_configured = bool(os.getenv("GEMINI_API_KEY", "").strip())
offline_mode = st.checkbox(
    "Use deterministic offline analysis",
    value=not api_key_configured,
    help="Offline mode needs no API key or network connection.",
)

if st.button("Analyse Log", type="primary"):
    if not log_text.strip():
        st.warning("Enter, upload, or select a non-empty log before analysing.")
    else:
        try:
            with st.spinner("Analysing the log..."):
                result = summarize_log(log_text, offline=offline_mode)
            st.subheader("Error summary")
            st.write(result["summary"])
            st.metric("Severity", result["severity"])

            st.subheader("Root cause")
            st.write(result["root_cause"])
            st.caption(
                f"Error type: {result['error_type']} · "
                f"Confidence: {result['confidence']} · "
                f"Further investigation: "
                f"{'Recommended' if result['needs_investigation'] else 'Not indicated'}"
            )

            st.subheader("Suggested solutions")
            for fix in result["suggested_fix"]:
                st.markdown(f"- {fix}")
            st.subheader("Recommended steps")
            for index, step in enumerate(result["recommended_steps"], start=1):
                st.markdown(f"{index}. {step}")

            st.subheader("Relevant log evidence")
            if result["evidence"]:
                for evidence in result["evidence"]:
                    st.code(evidence, language="text")
            else:
                st.info("No error evidence was extracted from this log.")

            json_summary = json.dumps(result, indent=2, ensure_ascii=False)
            text_summary = (
                f"Summary: {result['summary']}\n"
                f"Error type: {result['error_type']}\n"
                f"Severity: {result['severity']}\n"
                f"Root cause: {result['root_cause']}\n"
                f"Evidence:\n"
                + "\n".join(f"- {item}" for item in result["evidence"])
                + "\nSuggested fixes:\n"
                + "\n".join(f"- {item}" for item in result["suggested_fix"])
                + "\nRecommended steps:\n"
                + "\n".join(
                    f"{index}. {item}"
                    for index, item in enumerate(result["recommended_steps"], start=1)
                )
                + f"\nConfidence: {result['confidence']}\n"
                f"Needs investigation: {result['needs_investigation']}\n"
            )
            json_column, text_column = st.columns(2)
            json_column.download_button(
                "Download summary as JSON",
                data=json_summary,
                file_name="build-log-summary.json",
                mime="application/json",
            )
            text_column.download_button(
                "Download summary as TXT",
                data=text_summary,
                file_name="build-log-summary.txt",
                mime="text/plain",
            )
        except MissingAPIKeyError as exc:
            st.error(str(exc))
        except (LLMServiceError, InvalidSummaryError, ValueError) as exc:
            st.error(f"Could not analyse this log: {exc}")

st.divider()
st.caption(
    "Gemini analysis sends extracted log details to Google's Gemini API. "
    "Use offline mode when you do not want to make an API request."
)
