"""Persist and restore FastAPI model/session assets."""

from __future__ import annotations

import json
import pickle
import shutil
from pathlib import Path
from typing import Any

import numpy as np

from backend.state import app_state
from config.settings import settings
from core.model_pipeline import create_explainer, load_model


SESSION_DIR = settings.data_dir / "session"
MODEL_FILE = SESSION_DIR / "model.bin"
META_FILE = SESSION_DIR / "meta.json"
TRAINING_FILE = SESSION_DIR / "training.npz"
TEST_FILE = SESSION_DIR / "test.npz"
BIT_DB_FILE = SESSION_DIR / "bit_db.pkl"


def _ensure_session_dir() -> None:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)


def _read_meta() -> dict[str, Any]:
    if not META_FILE.exists():
        return {}
    try:
        return json.loads(META_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_meta(meta: dict[str, Any]) -> None:
    _ensure_session_dir()
    META_FILE.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def persist_model(model_bytes: bytes, model_name: str) -> None:
    _ensure_session_dir()
    MODEL_FILE.write_bytes(model_bytes)
    meta = _read_meta()
    meta["model_name"] = model_name
    _write_meta(meta)


def session_meta() -> dict[str, Any]:
    meta = _read_meta()
    manual_save = bool(meta.get("manual_save"))
    has_model = MODEL_FILE.exists()
    has_training = TRAINING_FILE.exists()
    has_test = TEST_FILE.exists()
    return {
        "exists": manual_save and (has_model or has_training or has_test),
        "model_loaded": manual_save and has_model,
        "training_data": manual_save and has_training,
        "test_data": manual_save and has_test,
        "model_name": str(meta.get("model_name") or ""),
        "n_molecules": int(meta.get("n_molecules") or 0),
        "n_test": int(meta.get("n_test") or 0),
        "fp_radius": int(meta.get("fp_radius") or app_state.fp_radius),
        "fp_nbits": int(meta.get("fp_nbits") or app_state.fp_nbits),
        "saved_at": meta.get("saved_at"),
    }


def clear_session() -> None:
    if SESSION_DIR.exists():
        shutil.rmtree(SESSION_DIR, ignore_errors=True)


def reset_active_session() -> None:
    app_state.model = None
    app_state.model_bytes = None
    app_state.explainer = None
    app_state.bit_db = {}
    app_state.training_fps = None
    app_state.training_smiles = []
    app_state.training_labels = None
    app_state.training_probs = None
    app_state.model_name = ""
    app_state.test_fps = None
    app_state.test_smiles = []
    app_state.test_labels = None
    app_state.test_probs = None
    app_state.fp_radius = 3
    app_state.fp_nbits = 2048


def save_current_session() -> dict[str, Any]:
    if app_state.model is None and not app_state.has_training_data() and not app_state.has_test_data():
        raise ValueError("Nothing to save: upload a model or dataset first.")

    clear_session()

    if app_state.model is not None:
        raw = app_state.model_bytes
        if raw is None:
            raw = pickle.dumps(app_state.model, protocol=pickle.HIGHEST_PROTOCOL)
        persist_model(raw, app_state.model_name or "model")
    if app_state.has_training_data():
        persist_training()
    if app_state.has_test_data():
        persist_test()

    from datetime import datetime, timezone

    meta = _read_meta()
    meta["n_molecules"] = len(app_state.training_smiles)
    meta["n_test"] = len(app_state.test_smiles)
    meta["manual_save"] = True
    meta["saved_at"] = datetime.now(timezone.utc).isoformat()
    _write_meta(meta)
    return session_meta()


def persist_training() -> None:
    if app_state.training_fps is None or app_state.training_labels is None:
        return
    _ensure_session_dir()
    np.savez_compressed(
        TRAINING_FILE,
        fps=app_state.training_fps,
        labels=app_state.training_labels,
        smiles=np.asarray(app_state.training_smiles, dtype=object),
        allow_pickle=True,
    )
    with BIT_DB_FILE.open("wb") as fh:
        pickle.dump(app_state.bit_db, fh, protocol=pickle.HIGHEST_PROTOCOL)
    meta = _read_meta()
    meta["fp_radius"] = app_state.fp_radius
    meta["fp_nbits"] = app_state.fp_nbits
    _write_meta(meta)


def persist_test() -> None:
    if app_state.test_fps is None or app_state.test_labels is None:
        return
    _ensure_session_dir()
    np.savez_compressed(
        TEST_FILE,
        fps=app_state.test_fps,
        labels=app_state.test_labels,
        smiles=np.asarray(app_state.test_smiles, dtype=object),
        allow_pickle=True,
    )
    meta = _read_meta()
    meta["fp_radius"] = app_state.fp_radius
    meta["fp_nbits"] = app_state.fp_nbits
    _write_meta(meta)


def clear_persisted_test() -> None:
    try:
        TEST_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def restore_session() -> bool:
    if not bool(_read_meta().get("manual_save")):
        return False

    restored = False
    meta = _read_meta()

    if MODEL_FILE.exists():
        try:
            raw = MODEL_FILE.read_bytes()
            app_state.model = load_model(raw)
            app_state.model_bytes = raw
            app_state.explainer = create_explainer(app_state.model)
            app_state.model_name = str(meta.get("model_name") or MODEL_FILE.name)
            restored = True
        except Exception:
            app_state.model = None
            app_state.model_bytes = None
            app_state.explainer = None
            app_state.model_name = ""

    if TRAINING_FILE.exists():
        try:
            data = np.load(TRAINING_FILE, allow_pickle=True)
            app_state.training_fps = data["fps"]
            app_state.training_labels = data["labels"]
            app_state.training_smiles = data["smiles"].astype(str).tolist()
            app_state.fp_radius = int(meta.get("fp_radius", app_state.fp_radius))
            app_state.fp_nbits = int(meta.get("fp_nbits", app_state.fp_nbits))
            if BIT_DB_FILE.exists():
                with BIT_DB_FILE.open("rb") as fh:
                    app_state.bit_db = pickle.load(fh)
            app_state.training_probs = None
            restored = True
        except Exception:
            app_state.training_fps = None
            app_state.training_labels = None
            app_state.training_smiles = []
            app_state.bit_db = {}

    if TEST_FILE.exists():
        try:
            data = np.load(TEST_FILE, allow_pickle=True)
            app_state.test_fps = data["fps"]
            app_state.test_labels = data["labels"]
            app_state.test_smiles = data["smiles"].astype(str).tolist()
            app_state.test_probs = None
            restored = True
        except Exception:
            app_state.test_fps = None
            app_state.test_labels = None
            app_state.test_smiles = []

    return restored
