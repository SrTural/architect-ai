"""FastAPI REST endpoint for ArchitectAI."""

from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel

from app.core.refactor_engine import RefactorEngine


# ==== FastAPI App ====
app = FastAPI(
    title="ArchitectAI",
    description="Local-first AI-powered legacy code refactoring engine.",
    version="0.1.0",
)

engine = RefactorEngine()


# ==== Schemas ====
class RefactorRequest(BaseModel):
    """Refactor sorğusu üçün schema."""
    code: str


class RefactorResponse(BaseModel):
    """Refactor cavabı üçün schema."""
    old_code: str
    new_code: str
    valid_syntax: bool
    attempts: int


# ==== Endpoints ====
@app.get("/", tags=["Health"])
def root():
    """Root endpoint."""
    return {
        "name": "ArchitectAI",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health", tags=["Health"])
def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/refactor", response_model=RefactorResponse, tags=["Refactor"])
def refactor(request: RefactorRequest):
    """
    Kodu refaktor edir.

    Body-də `code` sahəsi ilə legacy kod göndərilir,
    AI onu müasir arxitekturaya çevirir.
    """
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="Code cannot be empty")

    result = engine.refactor(request.code)
    return RefactorResponse(**result)


@app.post("/refactor/file", response_model=RefactorResponse, tags=["Refactor"])
async def refactor_file(file: UploadFile = File(...)):
    """
    Fayl yükləyərək kodu refaktor edir.

    Multipart form-data ilə `.py` faylı göndərilir.
    """
    content = await file.read()
    try:
        code = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")

    result = engine.refactor(code)
    return RefactorResponse(**result)