
from fastapi import Depends, FastAPI, status
from fastapi.responses import JSONResponse

from rules.errors import RulesServiceError
from rules.schemas import CalculationRequest, EvaluateRequest
from rules.security import verify_internal_key
from rules.service import calculate_claim
from rules.engine.evaluate import evaluate_claim
from fastapi import HTTPException
from fastapi.responses import Response

from rules.receipts.builder import build_receipt
from rules.receipts.pdf_generator import generate_receipt_pdf
from rules.receipts.audit_chain import verify_audit_chain

from rules.receipts.storage import (
    save_receipt,
    get_receipt,
    save_receipt_with_audit,
)


app = FastAPI(
    title="CivicNode-Goa Rules & Calculator Service",
    description=(
        "Deterministic compensation calculations "
        "and claim rule evaluation."
    ),
    version="1.0.0",
)


@app.exception_handler(RulesServiceError)
async def rules_error_handler(request, exc: RulesServiceError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


@app.get("/health")
async def health_check():
    return {
        "service": "rules",
        "status": "healthy",
        "port": 8002,
    }


@app.post("/rules/evaluate")
async def evaluate_rules(
    request: EvaluateRequest,
    _: None = Depends(verify_internal_key),
):
    return evaluate_claim(request)


@app.post("/calc")
async def calculate_compensation(
    request: CalculationRequest,
    _: None = Depends(verify_internal_key),
):
    return calculate_claim(request)



@app.post("/receipts/pdf")
def create_receipt_pdf(
    payload: dict,
    _: None = Depends(verify_internal_key),
):
    """
    Build a receipt and return it as a downloadable PDF.
    """

    try:
        receipt = build_receipt(payload)

        # Generate the PDF before committing the receipt.
        pdf_bytes = generate_receipt_pdf(receipt)

        # Save receipt and audit event in one transaction.
        save_receipt_with_audit(receipt)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition":
                    f'attachment; filename="{receipt["receipt_id"]}.pdf"'
            },
        )

    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

@app.get("/receipts/{receipt_id}")
def retrieve_receipt(
    receipt_id: str,
    _: None = Depends(verify_internal_key),
):
    receipt = get_receipt(receipt_id)

    if receipt is None:
        raise HTTPException(
            status_code=404,
            detail="Receipt not found",
        )

    return receipt

@app.get("/audit/verify")
def verify_audit(
    _: None = Depends(verify_internal_key),
):
    """
    Verify the integrity of the audit hash chain.
    """

    result = verify_audit_chain()

    return {
        "service": "rules",
        "audit_integrity": (
            "valid" if result["valid"] else "compromised"
        ),
        "valid": result["valid"],
        "entries_checked": result["entries_checked"],
        "error": result["error"],
        "last_hash": result["last_hash"],
    }


@app.get("/receipts/{receipt_id}/pdf")
def download_saved_receipt_pdf(
    receipt_id: str,
    _: None = Depends(verify_internal_key),
):
    receipt = get_receipt(receipt_id)

    if receipt is None:
        raise HTTPException(
            status_code=404,
            detail="Receipt not found",
        )

    try:
        pdf_bytes = generate_receipt_pdf(receipt)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition":
                    f'attachment; filename="{receipt_id}.pdf"'
            },
        )

    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
