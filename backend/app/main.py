import os, tempfile
from datetime import datetime
from uuid import uuid4
from typing import Generator
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, Text, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./speech.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
class Base(DeclarativeBase): pass
class Transcript(Base):
    __tablename__ = "transcriptions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(180), default="Untitled transcription")
    text: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(32), default="auto")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
Base.metadata.create_all(engine)
app = FastAPI(title="Procucev Speech to Text API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "*").split(","), allow_methods=["*"], allow_headers=["*"])
def db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try: yield db
    finally: db.close()
class TranscriptPayload(BaseModel):
    title: str | None = Field(default=None, max_length=180)
    text: str | None = None
def serialize(x): return {"id":x.id,"title":x.title,"text":x.text,"language":x.language,"created_at":x.created_at}
@app.get("/api/health")
def health(): return {"status":"ok","service":"procucev-speech-to-text"}
@app.get("/api/transcriptions")
def list_transcriptions(db: Session=Depends(db_session)):
    return [serialize(x) for x in db.query(Transcript).order_by(Transcript.created_at.desc()).all()]
@app.get("/api/transcriptions/{transcript_id}")
def get_transcription(transcript_id: str, db: Session=Depends(db_session)):
    x=db.get(Transcript, transcript_id)
    if not x: raise HTTPException(404,"Transcription not found")
    return serialize(x)
@app.post("/api/transcriptions", status_code=201)
def create_transcription(payload: TranscriptPayload, db: Session=Depends(db_session)):
    if not (payload.text or "").strip(): raise HTTPException(422,"Transcript text is required")
    x=Transcript(title=(payload.title or "Untitled transcription").strip() or "Untitled transcription", text=payload.text.strip())
    db.add(x); db.commit(); db.refresh(x); return serialize(x)
@app.patch("/api/transcriptions/{transcript_id}")
def update_transcription(transcript_id: str, payload: TranscriptPayload, db: Session=Depends(db_session)):
    x=db.get(Transcript, transcript_id)
    if not x: raise HTTPException(404,"Transcription not found")
    if payload.title is not None: x.title=payload.title.strip() or "Untitled transcription"
    if payload.text is not None: x.text=payload.text.strip()
    db.commit(); db.refresh(x); return serialize(x)
@app.delete("/api/transcriptions/{transcript_id}", status_code=204)
def delete_transcription(transcript_id: str, db: Session=Depends(db_session)):
    x=db.get(Transcript, transcript_id)
    if not x: raise HTTPException(404,"Transcription not found")
    db.delete(x); db.commit()
@app.post("/api/transcribe")
async def transcribe_audio(audio: UploadFile=File(...)):
    if not (audio.content_type or "").startswith("audio/"): raise HTTPException(415,"Upload an audio file")
    data=await audio.read()
    if not data: raise HTTPException(400,"Empty audio segment")
    try:
        from faster_whisper import WhisperModel
        global whisper_model
        if "whisper_model" not in globals():
            whisper_model=WhisperModel(os.getenv("WHISPER_MODEL","base"), device="cpu", compute_type="int8")
        suffix={"audio/webm":".webm","audio/ogg":".ogg","audio/mp4":".mp4","audio/mpeg":".mp3"}.get(audio.content_type,".wav")
        with tempfile.NamedTemporaryFile(suffix=suffix) as f:
            f.write(data); f.flush()
            segments, info=whisper_model.transcribe(f.name, task="transcribe", vad_filter=True, beam_size=1)
            text=" ".join(s.text.strip() for s in segments).strip()
        return {"text":text,"language":info.language,"language_probability":info.language_probability}
    except ImportError: raise HTTPException(503,"Whisper dependency unavailable")
    except Exception as exc: raise HTTPException(422,f"Audio transcription failed: {type(exc).__name__}") from exc
