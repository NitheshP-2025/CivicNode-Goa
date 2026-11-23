"""FastAPI router for AI-2. Swetha can mount it (``app.include_router(router)``) or call the
Python functions directly. Run alone:  uvicorn civicnode_ai2.api:app --reload

Voice:
  POST /voice/sessions                       {language, claim_type}      -> snapshot
  GET  /voice/sessions/{id}                                             -> snapshot
  POST /voice/sessions/{id}/audio            multipart file=<audio>     -> snapshot
  POST /voice/sessions/{id}/transcript       {text, stt_confidence?}    -> snapshot
  POST /voice/sessions/{id}/typed            {fields:{...}}             -> snapshot (typed fallback)
Flood:
  GET  /flood/layer                                                     -> layer info
  POST /flood/check                          {plot, date}               -> verdict, confidence, reason
  POST /flood/evidence                       {plot, date}               -> image/png
"""
import datetime as dt
from typing import Dict, List, Literal, Optional

from fastapi import APIRouter, FastAPI, File, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator

from . import config
from .flood.evidence import render_evidence_png
from .flood.layer import FloodLayer, get_default_layer
from .flood.query import FloodChecker
from .voice.intake import TypedValidationError, VoiceIntakeSession
from .voice.stt import get_transcriber

router = APIRouter()

_SESSIONS: Dict[str, VoiceIntakeSession] = {}      # in-memory; Swetha can persist snapshots in the DB
_transcriber = None
_layer: Optional[FloodLayer] = None


def set_transcriber(t) -> None:
    """Override the speech engine (tests, or plug in a different engine)."""
    global _transcriber
    _transcriber = t


def set_layer(layer: Optional[FloodLayer]) -> None:
    global _layer
    _layer = layer


def _get_transcriber():
    global _transcriber
    if _transcriber is None:
        _transcriber = get_transcriber()
    return _transcriber


def _get_layer() -> FloodLayer:
    global _layer
    if _layer is None:
        _layer = get_default_layer()
    return _layer


def _session(session_id: str) -> VoiceIntakeSession:
    s = _SESSIONS.get(session_id)
    if s is None:
        raise HTTPException(404, "unknown session")
    return s


# ------------------------------------------------------------------ models
class NewSession(BaseModel):
    language: Literal["en", "mr", "kok"] = "en"
    claim_type: Literal["flood_relief", "land_acquisition"] = "flood_relief"


class TranscriptIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    stt_confidence: Optional[float] = Field(default=None, ge=0, le=1)


class TypedIn(BaseModel):
    fields: Dict[str, str]


class PlotIn(BaseModel):
    plot_id: Optional[str] = None
    polygon: Optional[List[List[float]]] = Field(default=None, description="[[lon, lat], ...]")
    lat: Optional[float] = None
    lon: Optional[float] = None
    area_sq_m: Optional[float] = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _one_form(self):
        has_poly = bool(self.polygon)
        has_point = None not in (self.lat, self.lon, self.area_sq_m)
        if not (has_poly or has_point):
            raise ValueError("give either polygon, or lat + lon + area_sq_m")
        return self


class FloodQuery(BaseModel):
    plot: PlotIn
    date: dt.date


# ------------------------------------------------------------------ routes
@router.get("/health")
def health():
    return {"status": "ok", "module": "civicnode-ai2"}


@router.post("/voice/sessions")
def create_session(body: NewSession):
    s = VoiceIntakeSession(body.language, body.claim_type, transcriber=_get_transcriber())
    _SESSIONS[s.session_id] = s
    return s.snapshot().to_dict()


@router.get("/voice/sessions/{session_id}")
def get_session(session_id: str):
    return _session(session_id).snapshot().to_dict()


@router.post("/voice/sessions/{session_id}/audio")
def submit_audio(session_id: str, file: UploadFile = File(...)):
    s = _session(session_id)
    data = file.file.read(config.MAX_AUDIO_BYTES + 1)
    if len(data) > config.MAX_AUDIO_BYTES:
        raise HTTPException(413, "audio file too large")
    if not data:
        raise HTTPException(422, "empty audio file")
    return s.submit_audio(data).to_dict()


@router.post("/voice/sessions/{session_id}/transcript")
def submit_transcript(session_id: str, body: TranscriptIn):
    return _session(session_id).submit_transcript(body.text, body.stt_confidence).to_dict()


@router.post("/voice/sessions/{session_id}/typed")
def submit_typed(session_id: str, body: TypedIn):
    s = _session(session_id)
    try:
        return s.submit_typed(body.fields).to_dict()
    except TypedValidationError as exc:
        raise HTTPException(422, {"errors": exc.errors})


@router.get("/flood/layer")
def layer_info():
    return _get_layer().info()


def _plot_dict(p: PlotIn) -> dict:
    return p.model_dump(exclude_none=True)


@router.post("/flood/check")
def flood_check(body: FloodQuery):
    try:
        return FloodChecker(_get_layer()).was_plot_flooded(_plot_dict(body.plot), body.date).to_dict()
    except ValueError as exc:
        raise HTTPException(422, str(exc))


@router.post("/flood/evidence")
def flood_evidence(body: FloodQuery):
    try:
        png = render_evidence_png(_get_layer(), _plot_dict(body.plot), body.date)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return Response(content=png, media_type="image/png")


def create_app() -> FastAPI:
    app = FastAPI(title="CivicNode-Goa AI-2 (voice, flood evidence)", version="1.0.0")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    app.include_router(router)
    return app


app = create_app()
