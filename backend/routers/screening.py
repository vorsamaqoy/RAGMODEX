"""Virtual screening: batch SMILES prediction."""

from __future__ import annotations

import io
import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse

from backend.state import app_state
from core.fingerprint_engine import FingerprintEngine

router = APIRouter()


@router.post("")
async def screen(
    file: UploadFile = File(...),
    smiles_col: str = Form("smiles"),
):
    """Upload a CSV/TXT of SMILES, return predictions as JSON."""
    if not app_state.has_model():
        raise HTTPException(status_code=400, detail="No model loaded.")

    raw = await file.read()
    ext = (file.filename or "").lower()

    if ext.endswith(".txt") or ext.endswith(".smi"):
        smiles_list = [s.strip() for s in raw.decode().splitlines() if s.strip()]
        df = pd.DataFrame({"smiles": smiles_list})
        smiles_col = "smiles"
    else:
        try:
            df = pd.read_csv(io.BytesIO(raw))
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Could not parse file: {e}")

    if smiles_col not in df.columns:
        raise HTTPException(status_code=422, detail=f"Column '{smiles_col}' not found.")

    radius = app_state.fp_radius
    n_bits = app_state.fp_nbits

    results = []
    for smi in df[smiles_col].tolist():
        smi_str = str(smi) if not isinstance(smi, str) else smi
        if not smi_str.strip():
            results.append({"smiles": smi, "valid": False, "probability": None, "prediction": None})
            continue
        fp_result = FingerprintEngine.generate_morgan(smi_str, radius=radius, n_bits=n_bits)
        if fp_result is None:
            results.append({"smiles": smi, "valid": False, "probability": None, "prediction": None})
            continue
        fp_arr = FingerprintEngine.fingerprint_to_array(fp_result.fingerprint)
        try:
            prob = float(app_state.model.predict_proba(fp_arr.reshape(1, -1))[0][1])
        except Exception:
            results.append({"smiles": smi, "valid": True, "probability": None, "prediction": None})
            continue
        results.append({
            "smiles": smi,
            "valid": True,
            "probability": round(prob, 4),
            "prediction": "Active" if prob >= 0.5 else "Inactive",
        })

    return {"n_total": len(results), "results": results}


@router.post("/export")
async def screen_export(
    file: UploadFile = File(...),
    smiles_col: str = Form("smiles"),
):
    """Same as /screen but returns a downloadable CSV."""
    if not app_state.has_model():
        raise HTTPException(status_code=400, detail="No model loaded.")

    raw = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    if smiles_col not in df.columns:
        raise HTTPException(status_code=422, detail=f"Column '{smiles_col}' not found.")

    radius = app_state.fp_radius
    n_bits = app_state.fp_nbits
    probs, preds = [], []

    for smi in df[smiles_col].tolist():
        smi_str = str(smi) if not isinstance(smi, str) else smi
        fp_result = FingerprintEngine.generate_morgan(smi_str, radius=radius, n_bits=n_bits) if smi_str.strip() else None
        if fp_result is None:
            probs.append(None)
            preds.append("Invalid")
        else:
            fp_arr = FingerprintEngine.fingerprint_to_array(fp_result.fingerprint)
            try:
                p = float(app_state.model.predict_proba(fp_arr.reshape(1, -1))[0][1])
                probs.append(round(p, 4))
                preds.append("Active" if p >= 0.5 else "Inactive")
            except Exception:
                probs.append(None)
                preds.append("Error")

    df["probability_active"] = probs
    df["prediction"] = preds

    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=screening_results.csv"},
    )
