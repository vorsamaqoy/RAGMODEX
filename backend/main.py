"""RAGMODEX FastAPI backend."""

from contextlib import asynccontextmanager
from pathlib import Path
import sys

# Make project root importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from rdkit import RDLogger
RDLogger.DisableLog("rdApp.*")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.state import app_state
from backend.routers import model, predict, design, chat, molecule, evaluate, screening, rag


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: keep RAG lazy so the API does not block while embedding
    # dependencies or persisted indexes initialize. RAG routes create it on demand.
    from config.settings import settings
    from backend.session_store import restore_session

    settings.ensure_dirs()
    restore_session()
    app_state.retriever = None
    yield
    # Shutdown: nothing to clean up


app = FastAPI(title="RAGMODEX API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(model.router,     prefix="/api/model",     tags=["model"])
app.include_router(predict.router,   prefix="/api/predict",   tags=["predict"])
app.include_router(design.router,    prefix="/api/design",    tags=["design"])
app.include_router(chat.router,      prefix="/api/chat",      tags=["chat"])
app.include_router(molecule.router,  prefix="/api/molecule",  tags=["molecule"])
app.include_router(evaluate.router,  prefix="/api/evaluate",  tags=["evaluate"])
app.include_router(screening.router, prefix="/api/screening", tags=["screening"])
app.include_router(rag.router,       prefix="/api/rag",       tags=["rag"])


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "model_loaded": app_state.has_model(),
        "training_data": app_state.has_training_data(),
        "model_name": app_state.model_name,
        "fp_radius": app_state.fp_radius,
        "fp_nbits": app_state.fp_nbits,
        "llm_provider": app_state.llm_provider,
        "llm_model": app_state.llm_model,
        "temperature": app_state.temperature,
    }
