"""session_persistence.py — Save and restore computed session state to disk.

Saved automatically after each major data-load (training CSV, model).
On next startup the app offers to resume or start fresh.
"""

from __future__ import annotations

import pickle
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any

# Session file lives next to app.py
SESSION_FILE = Path(__file__).parent.parent / ".molchat_session.pkl"

# Session format version — bump when the schema changes incompatibly
_VERSION = 2

# Keys copied verbatim from st.session_state into the save file
_PLAIN_KEYS = [
    "fp_radius",
    "fp_nbits",
    "fp_use_features",
    "current_smiles",
    "model_meta",
    "X_train",
    "smiles_train",
    "y_train",
    "bit_database",
    "bit_database_meta",
    "aggregate_stats",
    "ad_model",
    "test_df",
    "test_df_meta",
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def session_exists() -> bool:
    """Return True if a saved session file is present."""
    return SESSION_FILE.exists()


def delete_session() -> None:
    """Remove the session file (start-fresh action)."""
    try:
        SESSION_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def save_session(session_state: Any) -> bool:
    """Persist the current session to disk.  Returns True on success."""
    try:
        data: dict = {
            "version":   _VERSION,
            "timestamp": datetime.now().isoformat(),
        }

        for key in _PLAIN_KEYS:
            val = session_state.get(key)
            if val is not None:
                data[key] = val

        # Re-pickle the sklearn model so we store raw bytes
        model = session_state.get("rf_model")
        if model is not None:
            data["model_bytes"] = pickle.dumps(model, protocol=5)

        # SHAP explainer (may be large but is pickle-able for TreeExplainer)
        explainer = session_state.get("shap_explainer")
        if explainer is not None:
            try:
                data["shap_explainer_bytes"] = pickle.dumps(explainer, protocol=5)
            except Exception:
                pass   # skip if not serialisable

        with open(SESSION_FILE, "wb") as fh:
            pickle.dump(data, fh, protocol=5)
        return True

    except Exception:
        return False


def load_session(session_state: Any) -> bool:
    """Restore a previously saved session.  Returns True on success."""
    try:
        with open(SESSION_FILE, "rb") as fh:
            data = pickle.load(fh)

        if data.get("version", 1) < _VERSION:
            # Incompatible old format — ignore
            return False

        for key in _PLAIN_KEYS:
            if key in data:
                session_state[key] = data[key]

        # Restore sklearn model
        if "model_bytes" in data:
            from sklearn.exceptions import InconsistentVersionWarning
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", InconsistentVersionWarning)
                session_state["rf_model"] = pickle.loads(data["model_bytes"])

            # Restore SHAP explainer from bytes if saved
            if "shap_explainer_bytes" in data:
                try:
                    session_state["shap_explainer"] = pickle.loads(
                        data["shap_explainer_bytes"]
                    )
                except Exception:
                    session_state["shap_explainer"] = None
            else:
                # Rebuild from the model (one-time cost)
                try:
                    from core.model_pipeline import create_explainer
                    session_state["shap_explainer"] = create_explainer(
                        session_state["rf_model"]
                    )
                except Exception:
                    session_state["shap_explainer"] = None

        # Invalidate derived caches that must be recomputed from restored data
        session_state.pop("_design_canonical_train", None)
        session_state.pop("_design_cache", None)

        return True

    except Exception:
        return False


def peek_session_meta() -> dict:
    """Return a lightweight metadata dict from the session file without
    fully loading it.  Used only to populate the restore dialog."""
    try:
        with open(SESSION_FILE, "rb") as fh:
            data = pickle.load(fh)
        meta = data.get("bit_database_meta", {})
        model_meta = data.get("model_meta", {})
        return {
            "timestamp":  data.get("timestamp", "")[:19].replace("T", " "),
            "model_name": model_meta.get("filename", "—"),
            "model_type": model_meta.get("type", "—"),
            "n_molecules": meta.get("n_molecules", "—"),
            "n_bits":      meta.get("n_bits_indexed", "—"),
            "has_model":   "model_bytes" in data,
            "has_training": "X_train" in data,
        }
    except Exception:
        return {}
