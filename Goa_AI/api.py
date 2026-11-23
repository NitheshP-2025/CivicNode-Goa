from __future__ import annotations

from typing import List

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from .config import load_thresholds
from .documents.extract import extract_document
from .matching.registry_compare import compare_with_registry
from .recommend.engine import recommend
from .schemas import ClaimBundle, CompareRequest, ExtractionResult, MatchResult, Recommendation

MAX_BYTES = 10 * 1024 * 1024
app = FastAPI(title="CivicNode-Goa AI service", version="0.1.0")


@app.get("/ai/health")
def health():
    return {"status": "ok"}


@app.get("/ai/config")
def config():
    """Current thresholds (handy to show in the demo)."""
    return load_thresholds()


@app.post("/ai/extract", response_model=ExtractionResult)
async def extract(file: UploadFile = File(...), document_id: str = Form(...)):
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File is larger than 10 MB")
    try:
        return extract_document(data, file.filename or "", document_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/ai/compare", response_model=List[MatchResult])
def compare(body: CompareRequest):
    return compare_with_registry(body.extraction, body.registry)


@app.post("/ai/recommend", response_model=Recommendation)
def recommend_endpoint(bundle: ClaimBundle):
    return recommend(bundle)
