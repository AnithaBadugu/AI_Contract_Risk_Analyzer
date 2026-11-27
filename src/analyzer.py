import io
import re
from difflib import unified_diff
import fitz

PATTERNS = {
    "payment": re.compile(r"\b(payment|payable|invoice|fee|compensation|consideration|late fee|interest|reimbursement|billing)\b", re.I),
    "termination": re.compile(r"\b(terminat\w*|expire|expiration|cancellation|cancel|breach|notice period)\b", re.I),
    "renewal": re.compile(r"\b(renew(?:al|ed)?|auto(?:matic)?[- ]renew|extend(?:ed|sion)?|successive term)\b", re.I),
}
RISK_RULES = [
    ("High", "Unilateral termination wording", r"\b(at its sole discretion|without cause|for convenience)\b",
     "The wording may allow one party to end the agreement without a stated breach. Check whether rights are balanced and notice is adequate."),
    ("Medium", "Automatic renewal wording", r"\b(automatically renew|auto[- ]renew|shall renew automatically)\b",
     "An automatic renewal mechanism may extend obligations unless notice is given. Verify the renewal term, notice deadline, and delivery method."),
    ("Medium", "Uncapped liability wording", r"\b(unlimited liability|without limitation.*liability|no limit on liability)\b",
     "The text appears to describe liability without an express cap. Check exclusions, carve-outs, and whether a cap exists elsewhere."),
    ("Medium", "Late payment consequences", r"\b(late fee|penalty|default interest|interest at)\b",
     "Payment delay consequences are mentioned. Verify the rate, calculation method, grace period, and applicable law."),
    ("Low", "Broad confidentiality wording", r"\b(all information|any information.*confidential|confidential information)\b",
     "Review the definition, exclusions, permitted disclosures, and duration of confidentiality obligations."),
]

def _extract_pages(pdf_bytes):
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise ValueError("The file is not a readable PDF.") from exc
    if doc.is_encrypted:
        raise ValueError("Password-protected PDFs are not supported.")
    pages = []
    for index, page in enumerate(doc):
        text = page.get_text("text").strip()
        if text:
            pages.append({"page": index + 1, "text": re.sub(r"[ \t]+", " ", text)})
    if not pages:
        raise ValueError("No selectable text was found. Run OCR on this scanned PDF, then upload the searchable PDF.")
    return pages, len(doc)

def _sentences(text):
    # Keep sentence snippets with enough context; PDF line breaks are normalized first.
    text = re.sub(r"\s+", " ", text)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(])", text)
    return [p.strip() for p in parts if p.strip()]

def analyze_pdf(pdf_bytes, filename="contract.pdf"):
    pages, page_count = _extract_pages(pdf_bytes)
    clauses = {}
    for key, pattern in PATTERNS.items():
        matches = []
        for page in pages:
            for sentence in _sentences(page["text"]):
                if pattern.search(sentence):
                    matches.append({"page": page["page"], "text": sentence[:1800]})
        clauses[key] = matches[:30]

    full_text = " ".join(p["text"] for p in pages)
    risks = []
    for severity, title, regex, detail in RISK_RULES:
        match = re.search(regex, full_text, re.I)
        if match:
            context = full_text[max(0, match.start()-100):min(len(full_text), match.end()+180)]
            risks.append({"severity": severity, "title": title, "detail": detail, "basis": context.strip()[:350]})

    missing = []
    for key, label in [("payment", "Payment amount, currency, due date, and invoicing process"),
                        ("termination", "Termination rights, notice period, and post-termination obligations"),
                        ("renewal", "Renewal term, renewal mechanism, and opt-out deadline")]:
        if not clauses[key]:
            missing.append(f"No likely {label.lower()} clause was detected; confirm whether it is absent or expressed using different terminology.")
    if not re.search(r"\b(governing law|jurisdiction|venue)\b", full_text, re.I):
        missing.append("Governing law / jurisdiction clause was not detected.")
    if not re.search(r"\b(dispute resolution|arbitration|mediation|courts?)\b", full_text, re.I):
        missing.append("Dispute-resolution process was not detected.")
    if not re.search(r"\b(confidential|confidentiality)\b", full_text, re.I):
        missing.append("Confidentiality obligations were not detected.")
    severity_order = {"High": 3, "Medium": 2, "Low": 1}
    max_sev = max([severity_order[r["severity"]] for r in risks], default=0)
    level = {0: "No flags", 1: "Low", 2: "Medium", 3: "High"}[max_sev]
    summary = (f"Reviewed {page_count} PDF page(s). The rule-based scan found {sum(map(len, clauses.values()))} likely key-clause passage(s), "
               f"{len(risks)} potential risk flag(s), and {len(missing)} items to verify. Risk level reflects detected wording only, not a legal conclusion.")
    return {"filename": filename, "page_count": page_count, "clauses": clauses, "risks": risks,
            "missing": missing, "risk_level": level, "summary": summary, "pages": pages}

def compare_analyses(a, b):
    changes = []
    labels = {"payment": "Payment", "termination": "Termination", "renewal": "Renewal"}
    for key, label in labels.items():
        before = "\n".join(f'(p.{x["page"]}) {x["text"]}' for x in a["clauses"][key])
        after = "\n".join(f'(p.{x["page"]}) {x["text"]}' for x in b["clauses"][key])
        if before != after:
            status = "Added" if not before else ("Removed" if not after else "Changed")
            changes.append({"section": label, "status": status, "before": before, "after": after})
    old = {r["title"] for r in a["risks"]}
    new = {r["title"] for r in b["risks"]}
    risk_changes = [f"New flag: {x}" for x in sorted(new-old)] + [f"Flag no longer detected: {x}" for x in sorted(old-new)]
    if not risk_changes:
        risk_changes = ["No change in the set of rule-based risk flags."]
    lines = ["# Contract comparison", f"Original: {a['filename']}", f"Revised: {b['filename']}", ""]
    for c in changes:
        lines += [f"## {c['section']} — {c['status']}", "### Original", c["before"] or "Not detected", "### Revised", c["after"] or "Not detected", ""]
    lines += ["## Risk flag changes"] + [f"- {x}" for x in risk_changes]
    lines += ["", "> Text-based comparison of detected passages only. Formatting, tables, images, and clauses not detected by the rules may be missed. Obtain legal review."]
    return {"changes": changes, "risk_changes": risk_changes, "markdown": "\n".join(lines)}

def render_report(result):
    lines = ["# Contract risk analysis", f"File: {result['filename']}", f"Pages: {result['page_count']}",
             f"Rule-based risk level: {result['risk_level']}", "", result["summary"], ""]
    for key in ("payment", "termination", "renewal"):
        lines += [f"## {key.title()} clauses"]
        if result["clauses"][key]:
            lines += [f"- (Page {x['page']}) {x['text']}" for x in result["clauses"][key]]
        else:
            lines += ["- No likely clause detected."]
    lines += ["", "## Potential risks"]
    lines += [f"- **{x['severity']} — {x['title']}**: {x['detail']} Basis: {x['basis']}" for x in result["risks"]] or ["- No rule-based flags."]
    lines += ["", "## Items to verify"] + [f"- {x}" for x in result["missing"]]
    lines += ["", "> This automated scan is not legal advice and may miss clauses. Page references identify the PDF page containing the extracted passage."]
    return "\n".join(lines)
