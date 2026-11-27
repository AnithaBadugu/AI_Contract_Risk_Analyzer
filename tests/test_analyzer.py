import fitz
from src.analyzer import analyze_pdf, compare_analyses

def make_pdf(text):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(50, 50, 550, 750), text)
    data = doc.tobytes()
    doc.close()
    return data

def test_extracts_key_clauses_and_flags():
    pdf = make_pdf("Payment is due within 30 days of invoice. This agreement shall renew automatically for one year. Either party may terminate for convenience.")
    result = analyze_pdf(pdf, "test.pdf")
    assert result["clauses"]["payment"]
    assert result["clauses"]["renewal"]
    assert result["clauses"]["termination"]
    assert result["risk_level"] == "High"
    assert result["clauses"]["payment"][0]["page"] == 1

def test_compare_detects_change():
    a = analyze_pdf(make_pdf("Payment is due within 30 days."), "a.pdf")
    b = analyze_pdf(make_pdf("Payment is due within 15 days."), "b.pdf")
    diff = compare_analyses(a, b)
    assert any(x["section"] == "Payment" for x in diff["changes"])

def test_rejects_image_only_or_empty_pdf():
    doc = fitz.open()
    doc.new_page()
    data = doc.tobytes()
    doc.close()
    try:
        analyze_pdf(data)
    except ValueError as exc:
        assert "selectable text" in str(exc)
    else:
        assert False, "Expected a clear error for a PDF without selectable text"
