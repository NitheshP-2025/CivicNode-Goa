import pytest
from rules.receipts.pdf_generator import generate_receipt_pdf


@pytest.fixture
def sample_receipt():
    return {
        "receipt_id": "RCP-TEST123456",
        "claim_id": "CLM-TEST-001",
        "scheme": "flood_relief",
        "incident_date": "2026-06-15",
        "rule_pack": {
            "version": "v1",
            "status": "demo",
            "sha256": "a" * 64,
        },
        "calculation": {
            "formula": "eligible_area_hectares * rate_per_hectare",
            "total": "2222.22",
            "currency": "INR",
            "rounding": "ROUND_HALF_UP",
        },
        "decision_status": "pending_officer_review",
        "notices": [
            "Synthetic demonstration calculation.",
            "Requires authorised officer review.",
        ],
    }


def test_generates_pdf_bytes(sample_receipt):
    pdf = generate_receipt_pdf(sample_receipt)

    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF")


def test_pdf_is_not_empty(sample_receipt):
    pdf = generate_receipt_pdf(sample_receipt)

    assert len(pdf) > 500



from io import BytesIO
from pypdf import PdfReader


def test_pdf_contains_receipt_information(sample_receipt):
    pdf = generate_receipt_pdf(sample_receipt)

    reader = PdfReader(BytesIO(pdf))
    extracted_text = "\n".join(
        page.extract_text() or ""
        for page in reader.pages
    )

    assert "RCP-TEST123456" in extracted_text
    assert "CLM-TEST-001" in extracted_text


def test_pdf_rejects_missing_fields():
    import pytest

    with pytest.raises(ValueError):
        generate_receipt_pdf({"claim_id": "CLM-001"})
