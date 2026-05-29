"""Prediction endpoint: SMILES → probability + SHAP + bit interpretations."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.state import app_state
from core.model_pipeline import predict_and_interpret

router = APIRouter()


class PredictRequest(BaseModel):
    smiles: str
    top_n: int = 10


class CompareRequest(BaseModel):
    smiles1: str
    smiles2: str


class FocusBitRequest(BaseModel):
    smiles: str
    bit_index: int | None = None
    mode: str | None = None


def _collision_confidence(info: dict) -> dict:
    n_unique = int(info.get("n_unique_substructures", 0))
    dominance = float(info.get("dominance", 0.0))
    if n_unique <= 1:
        return {
            "level": "high",
            "label": "high: one observed substructure in this training set",
            "is_severe": False,
        }
    if dominance > 80:
        return {
            "level": "high",
            "label": "high: one dominant substructure despite hash collisions",
            "is_severe": False,
        }
    if dominance > 50:
        return {
            "level": "moderate",
            "label": "moderate: one substructure covers more than half of observations",
            "is_severe": False,
        }
    return {
        "level": "low",
        "label": "low: multiple substructures contribute with no dominant mapping",
        "is_severe": True,
    }


def _evidence_confidence(info: dict) -> dict:
    total = int(info.get("total_activations", 0))
    if total >= 30:
        return {
            "level": "sufficient",
            "label": "sufficient training-set evidence for a descriptive interpretation",
            "is_reliable": True,
        }
    if total >= 10:
        return {
            "level": "limited",
            "label": "limited training-set evidence; interpret cautiously",
            "is_reliable": False,
        }
    return {
        "level": "insufficient",
        "label": "insufficient training-set evidence for a reliable chemical interpretation",
        "is_reliable": False,
    }


def _bit_db_payload(bit_index: int, info: dict) -> dict:
    total = int(info.get("total_activations", 0))
    substructures = []
    for smiles, count in sorted(
        dict(info.get("substructures", {})).items(),
        key=lambda item: item[1],
        reverse=True,
    ):
        substructures.append({
            "smiles": smiles,
            "count": int(count),
            "percentage": (float(count) / total * 100.0) if total else 0.0,
            "radii": list(dict(info.get("radii", {})).get(smiles, [])),
        })

    confidence = _collision_confidence(info)
    return {
        "bit": f"ECFP{2 * app_state.fp_radius}_{bit_index}",
        "bit_index": bit_index,
        "total_activations": total,
        "active_freq": int(info.get("active_freq", 0)),
        "inactive_freq": int(info.get("inactive_freq", 0)),
        "active_ratio": float(info.get("active_ratio", 0.0)),
        "n_unique_substructures": int(info.get("n_unique_substructures", 0)),
        "dominant_substructure": info.get("dominant_substructure"),
        "dominance": float(info.get("dominance", 0.0)),
        "collision_confidence": confidence,
        "evidence_confidence": _evidence_confidence(info),
        "substructures": substructures,
        "collision_scope": (
            "training-set folded-bit collision: distinct atom environments observed "
            "across the loaded training molecules map to the same folded ECFP bit"
        ),
    }


def _compact_training_info(info: dict | None) -> dict | None:
    if not info:
        return None
    return {
        key: value
        for key, value in dict(info).items()
        if key not in {"substructures", "radii"}
    }


@router.post("")
def predict(req: PredictRequest):
    if not app_state.has_model():
        raise HTTPException(status_code=400, detail="No model loaded. Upload a model first.")

    result = predict_and_interpret(
        smiles=req.smiles,
        model=app_state.model,
        explainer=app_state.explainer,
        bit_db=app_state.bit_db,
        radius=app_state.fp_radius,
        n_bits=app_state.fp_nbits,
        top_n=req.top_n,
    )

    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])

    # Strip numpy arrays (not JSON serialisable)
    result.pop("fp_array", None)
    result.pop("shap_values_all", None)

    return result


def _focus_bit_record(result: dict, bit_index: int) -> dict:
    shap_values = result.get("shap_values_all")
    fp_array = result.get("fp_array")
    if shap_values is None or fp_array is None:
        raise HTTPException(status_code=500, detail="Prediction pipeline did not return SHAP/fingerprint arrays.")
    if bit_index < 0 or bit_index >= len(fp_array):
        raise HTTPException(status_code=422, detail=f"Invalid bit index: valid range is 0-{len(fp_array) - 1}.")

    mol_subs = []
    for item in result.get("active_bits", []):
        if int(item.get("bit_index", -1)) == bit_index:
            mol_subs = item.get("molecule_substructures", [])
            break
    if not mol_subs:
        for item in result.get("top_bits", []):
            if int(item.get("bit_index", -1)) == bit_index:
                mol_subs = item.get("molecule_substructures", [])
                break

    shap_value = float(shap_values[bit_index])
    return {
        "rank": 1,
        "bit": f"ECFP{2 * result['radius']}_{bit_index}",
        "bit_index": bit_index,
        "shap_value": shap_value,
        "abs_shap": abs(shap_value),
        "direction": "-> Active" if shap_value > 0 else "-> Inactive",
        "bit_on": int(fp_array[bit_index]),
        "molecule_substructures": mol_subs,
        "training_info": _compact_training_info(app_state.bit_db.get(bit_index)),
    }


@router.post("/focus-bit")
def focus_bit(req: FocusBitRequest):
    if not app_state.has_model():
        raise HTTPException(status_code=400, detail="No model loaded. Upload a model first.")

    result = predict_and_interpret(
        smiles=req.smiles,
        model=app_state.model,
        explainer=app_state.explainer,
        bit_db=app_state.bit_db,
        radius=app_state.fp_radius,
        n_bits=app_state.fp_nbits,
        top_n=10,
    )
    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])

    shap_values = result.get("shap_values_all")
    if shap_values is None:
        raise HTTPException(status_code=500, detail="Prediction pipeline did not return SHAP values.")

    if req.mode == "strongest-negative":
        bit_index = int(shap_values.argmin())
    elif req.bit_index is not None:
        bit_index = int(req.bit_index)
    else:
        raise HTTPException(status_code=422, detail="Provide bit_index or mode='strongest-negative'.")

    focus = _focus_bit_record(result, bit_index)
    result.pop("fp_array", None)
    result.pop("shap_values_all", None)
    result["top_bits"] = []
    result["active_bits"] = []
    return {"prediction": result, "focus_bit": focus}


@router.get("/bit-db/most-ambiguous")
def most_ambiguous_bit():
    if not app_state.bit_db:
        raise HTTPException(status_code=400, detail="Bit database is not available. Load training data first.")
    bit_index, info = max(
        app_state.bit_db.items(),
        key=lambda item: int(item[1].get("n_unique_substructures", 0)),
    )
    return _bit_db_payload(int(bit_index), info)


@router.get("/bit-db/top-active")
def top_active_ratio_bit():
    if not app_state.bit_db:
        raise HTTPException(status_code=400, detail="Bit database is not available. Load training data first.")
    from core.aggregate_stats import build_aggregate_stats

    stats = build_aggregate_stats(app_state.bit_db)
    row = stats["top_active_bits"][0] if stats["top_active_bits"] else None
    if not row:
        raise HTTPException(status_code=404, detail="No sufficiently frequent bits were found.")
    bit_index = int(row["bit"])
    return _bit_db_payload(bit_index, app_state.bit_db[bit_index])


@router.get("/bit-db/top-inactive")
def top_inactive_association_bit():
    if not app_state.bit_db:
        raise HTTPException(status_code=400, detail="Bit database is not available. Load training data first.")
    from core.aggregate_stats import build_aggregate_stats

    stats = build_aggregate_stats(app_state.bit_db)
    row = stats["top_inactive_bits"][0] if stats["top_inactive_bits"] else None
    if not row:
        raise HTTPException(status_code=404, detail="No sufficiently frequent bits were found.")
    bit_index = int(row["bit"])
    return _bit_db_payload(bit_index, app_state.bit_db[bit_index])


@router.post("/bit-db/active-on-most-ambiguous")
def active_on_most_ambiguous_bit(req: FocusBitRequest):
    if not app_state.has_model():
        raise HTTPException(status_code=400, detail="No model loaded. Upload a model first.")
    if not app_state.bit_db:
        raise HTTPException(status_code=400, detail="Bit database is not available. Load training data first.")

    result = predict_and_interpret(
        smiles=req.smiles,
        model=app_state.model,
        explainer=app_state.explainer,
        bit_db=app_state.bit_db,
        radius=app_state.fp_radius,
        n_bits=app_state.fp_nbits,
        top_n=10,
    )
    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])

    candidates = [
        bit for bit in result.get("active_bits", [])
        if bit.get("training_info")
    ]
    if not candidates:
        raise HTTPException(status_code=404, detail="No active ON bits with training-set collision context were found for this molecule.")
    chosen = max(
        candidates,
        key=lambda bit: int(bit["training_info"].get("n_unique_substructures", 0)),
    )
    payload = _bit_db_payload(int(chosen["bit_index"]), chosen["training_info"])
    payload["molecule_context"] = {
        "canonical_smiles": result["canonical_smiles"],
        "bit_on": True,
        "molecule_substructures": chosen.get("molecule_substructures", []),
    }
    return payload


@router.get("/bit-db/{bit_index}")
def bit_database_entry(bit_index: int):
    if not app_state.bit_db:
        raise HTTPException(status_code=400, detail="Bit database is not available. Load training data first.")
    if bit_index < 0 or bit_index >= app_state.fp_nbits:
        raise HTTPException(status_code=422, detail=f"Invalid bit index: valid range is 0-{app_state.fp_nbits - 1}.")
    info = app_state.bit_db.get(bit_index)
    if not info:
        raise HTTPException(status_code=404, detail=f"ECFP{2 * app_state.fp_radius}_{bit_index} was not observed in the loaded bit database.")
    return _bit_db_payload(bit_index, info)


@router.post("/compare")
def compare(req: CompareRequest):
    if not app_state.has_model():
        raise HTTPException(status_code=400, detail="No model loaded. Upload a model first.")

    from core.comparison_pipeline import compare_molecules

    result = compare_molecules(
        req.smiles1,
        req.smiles2,
        app_state.model,
        app_state.explainer,
        app_state.bit_db,
        radius=app_state.fp_radius,
        n_bits=app_state.fp_nbits,
    )

    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])
    if result.get("identical"):
        return result

    for key in ("mol1", "mol2"):
        result[key].pop("fp_array", None)
        result[key].pop("shap_values_all", None)

    return result
