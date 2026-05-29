"""Design endpoint: guided beam-search molecular variant generation."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.state import app_state
from core.design_engine import run_guided_pipeline

router = APIRouter()


class DesignRequest(BaseModel):
    smiles: str
    n_variants: int = 200
    top_k: int = 9
    n_iterations: int = 5
    beam_size: int = 3
    n_per_iter: int = 100
    patience: int = 3
    use_druglikeness: bool = True
    w_activity: float = 0.50
    w_diversity: float = 0.25
    w_ad: float = 0.25


@router.post("")
def design(req: DesignRequest):
    if not app_state.has_model():
        raise HTTPException(status_code=400, detail="No model loaded.")

    # Auto-renormalise weights so they sum to 1.0
    w_sum = req.w_activity + req.w_diversity + req.w_ad
    if w_sum <= 0:
        w_activity, w_diversity, w_ad = 0.50, 0.25, 0.25
    else:
        w_activity  = req.w_activity  / w_sum
        w_diversity = req.w_diversity / w_sum
        w_ad        = req.w_ad        / w_sum

    result = run_guided_pipeline(
        smiles=req.smiles,
        model=app_state.model,
        radius=app_state.fp_radius,
        n_bits=app_state.fp_nbits,
        n_variants_per_iter=req.n_per_iter,
        n_iterations=req.n_iterations,
        beam_size=req.beam_size,
        dataset_fps=app_state.training_fps,
        train_smiles=app_state.training_smiles if app_state.training_smiles else None,
        top_k=req.top_k,
        patience=req.patience,
        shap_explainer=app_state.explainer,
        bit_db=app_state.bit_db if app_state.bit_db else None,
        use_druglikeness=req.use_druglikeness,
        w_prob=w_activity,
        w_div=w_diversity,
        w_ad=w_ad,
    )

    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])

    # Serialise DesignCandidate dataclasses — use top_total (top_k by probability)
    candidates = []
    for c in result.get("top_total", []):
        candidates.append({
            "smiles":        c.smiles,
            "probability":   c.probability,
            "delta":         c.delta,
            "source":        c.source,
            "transformation": c.transformation,
            "rank":          c.rank,
            "ad_score":      c.ad_score,
            "parent_smiles": c.parent_smiles,
            "iteration":     c.iteration,
        })

    def _ser_history(items: list) -> list:
        out = []
        for h in items:
            out.append({
                "iteration":   int(h.get("iteration", 0)),
                "n_generated": int(h.get("n_generated", 0)),
                "best_prob":   float(h.get("best_prob", 0.0)),
                "ad_score":    float(h.get("ad_score", 1.0)),
                "best_smiles": str(h.get("best_smiles", "")),
            })
        return out

    return {
        "base_smiles":              result.get("base_smiles"),
        "base_probability":         result.get("base_prob", 0.0),
        "n_generated":              result.get("n_generated", 0),
        "n_valid":                  result.get("n_valid", result.get("n_generated", 0)),
        "candidates":               candidates,
        "history":                  _ser_history(result.get("history", [])),
        "timeline_path":            _ser_history(result.get("timeline_path", [])),
        "top_candidate_prob":       result.get("top_candidate_prob"),
        "top_candidate_iteration":  result.get("top_candidate_iteration"),
    }
