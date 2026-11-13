# LLM-Based Build/Error-Log Summarization

A beginner-friendly Streamlit application that extracts important signals from
software build logs and explains failures in plain English. It can use Google's
Gemini API for explanations or a deterministic offline analyzer when no API
request is desired.

## Problem statement

Build output can contain hundreds or thousands of lines. Important errors may be
buried among routine status messages, and the original error is often difficult
to interpret. This project extracts likely errors, preserves nearby context,
identifies common failure types, and presents an actionable summary.

## Aim and objectives

- Accept pasted logs, `.log`/`.txt` uploads, and included sample logs.
- Extract error, warning, info, and debug messages where possible.
- Detect common Python, dependency, compilation, test, and network failures.
- Explain the likely cause and recommended fixes in simple English.
- Validate structured summaries before displaying or downloading them.
- Provide offline analysis and tests that do not need an API key or network.

## Technologies

Python 3.10+, Google `google-genai`, Streamlit, pytest, JSON, and GitHub Actions.

## Project structure

```text
.
├── app.py
├── src/
│   ├── __init__.py
│   ├── log_analyzer.py
│   ├── log_parser.py
│   └── llm_summarizer.py
├── tests/
│   ├── test_log_analyzer.py
│   ├── test_llm_summarizer.py
│   └── test_log_parser.py
├── samples/
│   ├── sample_build_error.log
│   ├── sample_success.log
│   ├── sample_syntax_error.log
│   └── sample_test_failure.log
├── .github/workflows/ci.yml
├── .env.example
├── .gitignore
├── pytest.ini
├── README.md
└── requirements.txt
```

## How it works

1. Choose pasted text, an uploaded `.log`/`.txt` file, or one of the sample logs.
2. The parser extracts severity-tagged lines, common failure signatures, and
   configurable surrounding context. It does not depend on one log format.
3. Select offline mode for a deterministic rule-based explanation, or configure
   a Gemini API key and use Gemini for a natural-language summary.
4. The response is checked for required JSON fields, types, and allowed severity
   and confidence values before the UI renders it.
5. Download the validated result as JSON or plain text.

The offline analyzer is a useful baseline, not a generative model. It reports
uncertainty when the available evidence is insufficient. Gemini is instructed
to treat log text as untrusted evidence, not as instructions.

## Gemini API key

1. Obtain an API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
   and follow Google's current account and API terms.
2. Copy `.env.example` to `.env` in the project root.
3. Replace the example value with your key:

   ```dotenv
   GEMINI_API_KEY=your_actual_key
   ```

4. Keep `.env` private; it is excluded by `.gitignore`. Never paste a real key
   into source code, logs, screenshots, or version control.

The app loads `.env` locally. Alternatively, set `GEMINI_API_KEY` in the
environment where Streamlit runs. Without a key, select offline mode.

## Installation

From the project directory, create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On macOS or Linux, activation is `source .venv/bin/activate`.

## Run the application

```powershell
streamlit run app.py
```

Open the local URL printed by Streamlit. Select a log source, choose offline
analysis or Gemini, then click **Analyse Log**.

## Example

Input:

```text
ERROR: No matching distribution found for requests==99.0.0
Build step "Install dependencies" failed with exit code 1
```

Offline output identifies a dependency installation failure, quotes the error
as evidence, and recommends checking the package name, Python compatibility,
and package installer output. Gemini may provide additional context when online
analysis is enabled.

## Tests

```powershell
python -m pytest -q
```

Tests cover parsing and uploads, failure signatures, successful builds, invalid
inputs, response validation, missing keys, deterministic offline summaries,
and mocked Gemini API failures. No test calls the live Gemini service.

## GitHub Actions

`.github/workflows/ci.yml` runs on pushes to `main` and pull requests targeting
`main`. It installs `requirements.txt` on Python 3.10 and runs
`python -m pytest -q`. The workflow does not need a Gemini secret because tests
use offline behavior and mocked API calls.

## Limitations and future improvements

- Pattern-based parsing cannot understand every build tool or log format.
- Gemini output can be incomplete or incorrect despite schema validation;
  verify important fixes against the original log.
- Gemini analysis sends extracted error and context lines to Google's API.
- Very large logs may be reduced to bounded excerpts for the API request.
- Future improvements could include additional build-system parsers, redaction
  of sensitive log values, configurable context selection, and richer
  language-specific remediation guidance.
