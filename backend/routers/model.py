"""Model upload and training data upload endpoints."""

from __future__ import annotations

import io
import os
import json
from pathlib import Path
from urllib import request as urlrequest
import numpy as np
import pandas as pd
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query

from backend.state import app_state
from backend.session_store import clear_session, reset_active_session, session_meta, restore_session, save_current_session
from core.model_pipeline import load_model, create_explainer
from core.fingerprint_engine import FingerprintEngine
from core.bit_database import build_bit_database

router = APIRouter()

API_KEY_ENV = {
    "groq": "GROQ_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _persist_env_value(key: str, value: str) -> None:
    """Update or append one key in the project .env file."""
    env_path = _project_root() / ".env"
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    prefix = f"{key}="
    updated = False
    for i, line in enumerate(lines):
        if line.startswith(prefix):
            lines[i] = f"{key}={value}"
            updated = True
            break
    if not updated:
        lines.append(f"{key}={value}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _provider_catalog() -> list[dict]:
    from llm.client_factory import LLMClientFactory, LocalOllamaClient

    providers = []
    for info in LLMClientFactory.list_all_providers():
        models = info.models
        if info.name == "local":
            models = LocalOllamaClient.list_models(app_state.llm_local_endpoint)
        env_key = API_KEY_ENV.get(info.name)
        providers.append({
            "name": info.name,
            "available": info.available,
            "requires_key": env_key is not None,
            "key_configured": bool(os.getenv(env_key, "")) if env_key else True,
            "default_model": info.default_model,
            "models": models,
        })
    return providers


@router.post("/upload")
async def upload_model(file: UploadFile = File(...)):
    """Upload a .pkl or .joblib sklearn model file."""
    raw = await file.read()
    try:
        model = load_model(raw)
        explainer = create_explainer(model)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    app_state.model = model
    app_state.model_bytes = raw
    app_state.explainer = explainer
    app_state.model_name = file.filename or "model"
    app_state.bit_db = {}
    app_state.training_probs = None  # invalidate cached probs

    return {"ok": True, "model_name": app_state.model_name}


@router.post("/training-data")
async def upload_training_data(
    file: UploadFile = File(...),
    smiles_col: str = Form("smiles"),
    label_col: str = Form("label"),
    radius: int = Form(3),
    nbits: int = Form(2048),
):
    """Upload a CSV with SMILES + labels to build fingerprint index and bit database."""
    raw = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse CSV: {e}")

    if smiles_col not in df.columns or label_col not in df.columns:
        raise HTTPException(
            status_code=422,
            detail=f"CSV must contain columns '{smiles_col}' and '{label_col}'",
        )

    smiles_list = df[smiles_col].tolist()
    labels = df[label_col].tolist()

    fps_list, valid_smiles, valid_labels = [], [], []
    try:
        for smi, lbl in zip(smiles_list, labels):
            if not isinstance(smi, str) or not smi.strip():
                continue
            result = FingerprintEngine.generate_morgan(smi, radius=radius, n_bits=nbits)
            if result is not None:
                fp_arr = FingerprintEngine.fingerprint_to_array(result.fingerprint)
                fps_list.append(fp_arr)
                valid_smiles.append(smi)
                valid_labels.append(lbl)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fingerprint generation failed: {e}")

    if not fps_list:
        raise HTTPException(status_code=422, detail="No valid SMILES found in CSV")

    training_fps = np.array(fps_list, dtype=np.int32)
    training_labels = np.array(valid_labels, dtype=np.int32)

    try:
        df_for_bitdb = pd.DataFrame({"smiles": valid_smiles, "label": valid_labels})
        bit_db, _ = build_bit_database(df_for_bitdb, smiles_col="smiles", label_col="label", radius=radius, n_bits=nbits)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bit database build failed: {e}")

    app_state.fp_radius = radius
    app_state.fp_nbits = nbits
    app_state.training_fps = training_fps
    app_state.training_smiles = valid_smiles
    app_state.training_labels = training_labels
    app_state.bit_db = bit_db
    app_state.training_probs = None  # invalidate cached probs
    app_state.test_fps = None
    app_state.test_smiles = []
    app_state.test_labels = None
    app_state.test_probs = None

    return {
        "ok": True,
        "n_molecules": len(valid_smiles),
        "n_bits": nbits,
        "active": int(training_labels.sum()),
        "inactive": int((training_labels == 0).sum()),
    }


@router.post("/training-data/test")
async def upload_test_data(
    file: UploadFile = File(...),
    smiles_col: str = Form("smiles"),
    label_col: str = Form("label"),
    radius: int = Form(3),
    nbits: int = Form(2048),
):
    """Upload a CSV with SMILES + labels to use as a held-out test set."""
    raw = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse CSV: {e}")

    if smiles_col not in df.columns or label_col not in df.columns:
        raise HTTPException(
            status_code=422,
            detail=f"CSV must contain columns '{smiles_col}' and '{label_col}'",
        )

    smiles_list = df[smiles_col].tolist()
    labels = df[label_col].tolist()

    fps_list, valid_smiles, valid_labels = [], [], []
    try:
        for smi, lbl in zip(smiles_list, labels):
            if not isinstance(smi, str) or not smi.strip():
                continue
            result = FingerprintEngine.generate_morgan(smi, radius=radius, n_bits=nbits)
            if result is not None:
                fp_arr = FingerprintEngine.fingerprint_to_array(result.fingerprint)
                fps_list.append(fp_arr)
                valid_smiles.append(smi)
                valid_labels.append(lbl)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fingerprint generation failed: {e}")

    if not fps_list:
        raise HTTPException(status_code=422, detail="No valid SMILES found in CSV")

    test_fps = np.array(fps_list, dtype=np.int32)
    test_labels = np.array(valid_labels, dtype=np.int32)

    app_state.test_fps = test_fps
    app_state.test_smiles = valid_smiles
    app_state.test_labels = test_labels
    app_state.test_probs = None  # invalidate cached probs

    return {
        "ok": True,
        "n_molecules": len(valid_smiles),
        "active": int(test_labels.sum()),
        "inactive": int((test_labels == 0).sum()),
    }


@router.post("/config")
async def set_llm_config(
    provider: str = Form("groq"),
    model: str = Form("llama-3.3-70b-versatile"),
    temperature: float = Form(0.3),
    api_key: str = Form(""),
    persist_api_key: bool = Form(False),
    local_endpoint: str = Form("http://127.0.0.1:11434"),
):
    """Set LLM provider / model / temperature."""
    from llm.chat_handler import ChatHandler

    try:
        provider = provider.lower()
        if provider == "local":
            endpoint = (local_endpoint or "http://127.0.0.1:11434").rstrip("/")
            os.environ["LOCAL_LLM_ENDPOINT"] = endpoint
            app_state.llm_local_endpoint = endpoint
        elif api_key.strip():
            env_key = API_KEY_ENV.get(provider)
            if env_key:
                os.environ[env_key] = api_key.strip()
                if persist_api_key:
                    _persist_env_value(env_key, api_key.strip())

        handler = ChatHandler(provider=provider, model=model)
        handler.set_temperature(temperature)
        app_state.chat_handler = handler
        app_state.llm_provider = provider
        app_state.llm_model = model
        app_state.temperature = temperature
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    return {"ok": True, "provider": provider, "model": model}


@router.get("/llm/catalog")
def llm_catalog():
    return {
        "provider": app_state.llm_provider,
        "model": app_state.llm_model,
        "temperature": app_state.temperature,
        "local_endpoint": app_state.llm_local_endpoint,
        "providers": _provider_catalog(),
    }


@router.post("/llm/local/pull")
def pull_local_model(
    model_name: str = Form(...),
    local_endpoint: str = Form("http://127.0.0.1:11434"),
):
    """Pull an Ollama model into the local runtime."""
    model_name = model_name.strip()
    if not model_name:
        raise HTTPException(status_code=422, detail="Model name is required.")

    endpoint = (local_endpoint or app_state.llm_local_endpoint).rstrip("/")
    payload = json.dumps({"name": model_name, "stream": False}).encode("utf-8")
    req = urlrequest.Request(
        f"{endpoint}/api/pull",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlrequest.urlopen(req, timeout=900) as res:
            data = json.loads(res.read().decode("utf-8") or "{}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not pull local model from Ollama: {e}")

    app_state.llm_local_endpoint = endpoint
    return {"ok": True, "model": model_name, "status": data.get("status", "pulled")}


@router.get("/status")
def model_status():
    return {
        "model_loaded": app_state.has_model(),
        "training_data": app_state.has_training_data(),
        "model_name": app_state.model_name,
        "n_molecules": len(app_state.training_smiles),
        "fp_radius": app_state.fp_radius,
        "fp_nbits": app_state.fp_nbits,
        "test_data": app_state.has_test_data(),
        "n_test": len(app_state.test_smiles),
        "llm_provider": app_state.llm_provider,
        "llm_model": app_state.llm_model,
        "temperature": app_state.temperature,
    }


@router.get("/session")
def saved_session_status():
    return session_meta()


@router.post("/session/save")
def save_session():
    try:
        return save_current_session()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save session: {e}")


@router.post("/session/restore")
def restore_saved_session():
    if not session_meta()["exists"]:
        raise HTTPException(status_code=404, detail="No saved session found.")
    if not restore_session():
        raise HTTPException(status_code=500, detail="Saved session could not be restored.")
    return {"ok": True, **model_status()}


@router.post("/session/clear")
def clear_saved_session():
    clear_session()
    return {"ok": True, **session_meta()}


@router.post("/session/new")
def start_new_session():
    reset_active_session()
    return {"ok": True, **model_status()}


@router.get("/visualizer")
def visualizer_data(
    page: int = Query(1, ge=1),
    per_page: int = Query(48, ge=1, le=200),
    filter_class: str = Query("all"),
    sort: str = Query("default"),
    search: str = Query(""),
):
    """Paginated training molecule list with predicted probabilities and histogram data."""
    if not app_state.has_model() or not app_state.has_training_data():
        raise HTTPException(status_code=400, detail="Model and training data required.")

    fps = app_state.training_fps
    smiles = app_state.training_smiles
    labels = app_state.training_labels

    # Compute or use cached probabilities
    if app_state.training_probs is None:
        try:
            app_state.training_probs = app_state.model.predict_proba(fps)[:, 1]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")
    probs = app_state.training_probs

    # Build filtered index
    indices = np.arange(len(smiles))
    if filter_class == "active":
        indices = indices[labels[indices] == 1]
    elif filter_class == "inactive":
        indices = indices[labels[indices] == 0]
    if search:
        lo = search.lower()
        indices = np.array([i for i in indices if lo in smiles[i].lower()])

    # Sort
    if sort == "prob_asc":
        indices = indices[np.argsort(probs[indices])]
    elif sort == "prob_desc":
        indices = indices[np.argsort(-probs[indices])]

    total = int(len(indices))
    n_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, n_pages))
    start = (page - 1) * per_page
    page_idx = indices[start: start + per_page]

    molecules = [
        {
            "index": int(i),
            "smiles": smiles[i],
            "label": int(labels[i]),
            "probability": round(float(probs[i]), 4),
        }
        for i in page_idx
    ]

    # Histogram over all training data (unfiltered)
    bins = np.linspace(0, 1, 41)
    active_mask = labels == 1
    inactive_mask = labels == 0
    hist_active, _ = np.histogram(probs[active_mask], bins=bins)
    hist_inactive, _ = np.histogram(probs[inactive_mask], bins=bins)
    accuracy = float(((probs >= 0.5).astype(int) == labels).mean())

    return {
        "molecules": molecules,
        "total": total,
        "n_pages": n_pages,
        "page": page,
        "n_active": int(active_mask.sum()),
        "n_inactive": int(inactive_mask.sum()),
        "accuracy": accuracy,
        "hist_bins": bins.tolist(),
        "hist_active": hist_active.tolist(),
        "hist_inactive": hist_inactive.tolist(),
    }
