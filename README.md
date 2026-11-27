# AI Contract Risk Analyzer

A local Streamlit application that extracts likely payment, termination, and renewal passages from searchable PDFs, flags selected wording patterns, lists review items, and compares two versions of a contract.

## Important limitation
This is an educational decision-support prototype, not a legal expert system. It uses transparent keyword and regular-expression rules; it does **not** use a trained AI model, determine legal enforceability, or guarantee complete clause detection. It can miss clauses in tables, images, unusual wording, or scanned PDFs. A "No flags" result does not mean a contract is safe. Always obtain qualified legal review.

## Features
- PDF upload and selectable-text extraction with PyMuPDF
- Likely payment, termination, and renewal passages with PDF page numbers
- Rule-based risk flags with supporting text snippets
- Checks for likely missing governing-law, dispute-resolution, and confidentiality terms
- Two-PDF comparison of extracted key-clause passages and risk-flag changes
- Dashboard with risk-severity pie charts, clause-count charts, and version comparison visuals
- Open account registration and sign-in for multiple users, with salted password hashes and sign-out
- Markdown report downloads
- No API key or external AI service required; files are processed locally by the app

## Requirements
- Python 3.10+
- Windows, macOS, or Linux
- Dependencies listed in `requirements.txt` (including Streamlit and Plotly)

## Setup (Windows PowerShell)
```powershell
cd AI_Contract_Risk_Analyzer
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

If PowerShell blocks activation, run:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Setup (macOS/Linux)
```bash
cd AI_Contract_Risk_Analyzer
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit (usually http://localhost:8501).

## Usage
1. Select **Create account** to register a unique username and password, or choose **Sign in** if you already have an account.
2. Upload a searchable PDF in **Analyze one contract** and review the extracted passages, page references, flags, and items to verify.
3. Download the Markdown report.
4. To compare versions, open **Compare two contracts**, upload the original and revised PDFs, and inspect each changed section.
5. Select **Sign out** to end your current session.

## Scanned PDFs
If no selectable text is detected, OCR the PDF using a trusted OCR tool and upload the searchable/OCR-processed PDF. The app intentionally does not silently claim to analyze image-only pages.

## Authentication scope
Anyone who can reach the app can create an account. Usernames and salted PBKDF2 password hashes are stored in the local `data/users.sqlite3` database; passwords are not stored in plain text. The database is excluded from Git, and sign-in state is limited to the current Streamlit session.

This project is suitable for a local or controlled demonstration, not production public authentication. It has no email verification, password recovery, login throttling, or admin moderation. Public deployment also requires HTTPS, persistent database storage, and protection against abuse; consider an established identity provider and managed database before inviting internet users. On hosting platforms with ephemeral filesystems, the local SQLite database may be lost when the app restarts. Set `CONTRACT_ANALYZER_DB_PATH` to a file on persistent storage when deploying.

## Tests
```bash
pytest -q
```

## Project structure
```text
AI_Contract_Risk_Analyzer/
├── app.py
├── requirements.txt
├── README.md
├── src/
│   ├── auth.py
│   ├── __init__.py
│   └── analyzer.py
├── tests/
│   ├── test_auth.py
│   └── test_analyzer.py
└── sample_contracts/
    ├── original_sample.txt
    └── revised_sample.txt
```

The sample files are illustrative text examples, not legal templates or actual PDFs.
