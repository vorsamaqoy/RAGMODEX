"""aggregate_stats.py — Pre-computed aggregate statistics over the training dataset bit database.

No Streamlit dependencies. Pure logic module.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _add_collision_context(lines: list[str], stats: dict) -> None:
    cs = stats["collision_stats"]
    lines.append("--- Bit Collision / Ambiguity Statistics ---")
    lines.append(f"Total bits observed: {cs['total_bits']}")
    lines.append(f"Unambiguous bits (1 unique substructure): {cs['unambiguous']}")
    lines.append(f"Ambiguous bits (>1 unique substructure): {cs['ambiguous']}")
    lines.append(f"Highly ambiguous bits (>=5 unique substructures): {cs['highly_ambiguous']}")
    lines.append(f"Ambiguity rate: {cs['ambiguity_rate']:.1f}%")
    lines.append("")

    top = stats["most_ambiguous_bits"][:10]
    if top:
        lines.append("Top ambiguous bits (bit → n_unique_substructures → dominant substructure):")
        for entry in top:
            dom = entry["dominant_sub"] or "none"
            lines.append(
                f"  Bit {entry['bit']}: {entry['n_unique_subs']} substructures, "
                f"dominant={dom}, activations={entry['n_activations']}"
            )
    lines.append("")


def _add_active_bits_context(lines: list[str], stats: dict, limit: int = 15) -> None:
    bits = stats["top_active_bits"][:limit]
    lines.append("--- Top Active-Associated Bits (by active_ratio) ---")
    if not bits:
        lines.append("No active-associated bits found.")
    else:
        for entry in bits:
            dom = entry["dominant_sub"] or "none"
            lines.append(
                f"  Bit {entry['bit']}: active_ratio={entry['active_ratio']:.3f}, "
                f"activations={entry['n_activations']}, unique_subs={entry['n_unique_subs']}, "
                f"dominant={dom}"
            )
    lines.append("")


def _add_inactive_bits_context(lines: list[str], stats: dict, limit: int = 15) -> None:
    bits = stats["top_inactive_bits"][:limit]
    lines.append("--- Top Inactive-Associated Bits (by active_ratio ascending) ---")
    if not bits:
        lines.append("No inactive-associated bits found.")
    else:
        for entry in bits:
            dom = entry["dominant_sub"] or "none"
            lines.append(
                f"  Bit {entry['bit']}: active_ratio={entry['active_ratio']:.3f}, "
                f"activations={entry['n_activations']}, unique_subs={entry['n_unique_subs']}, "
                f"dominant={dom}"
            )
    lines.append("")


def _add_exclusive_context(lines: list[str], stats: dict) -> None:
    active_excl = stats["active_exclusive_bits"]
    inactive_excl = stats["inactive_exclusive_bits"]

    lines.append("--- Active-Exclusive Bits (active_ratio > 0.9, activations >= 3) ---")
    if not active_excl:
        lines.append("  None found.")
    else:
        for entry in active_excl[:15]:
            dom = entry["dominant_sub"] or "none"
            lines.append(
                f"  Bit {entry['bit']}: active_ratio={entry['active_ratio']:.3f}, "
                f"activations={entry['n_activations']}, dominant={dom}"
            )
    lines.append("")

    lines.append("--- Inactive-Exclusive Bits (active_ratio < 0.1, activations >= 3) ---")
    if not inactive_excl:
        lines.append("  None found.")
    else:
        for entry in inactive_excl[:15]:
            dom = entry["dominant_sub"] or "none"
            lines.append(
                f"  Bit {entry['bit']}: active_ratio={entry['active_ratio']:.3f}, "
                f"activations={entry['n_activations']}, dominant={dom}"
            )
    lines.append("")


def _add_substructure_context(
    lines: list[str], stats: dict, actives_only: bool = False
) -> None:
    lines.append("--- Most Common Substructures in Actives ---")
    top_act = stats["top_substructures_actives"][:15]
    if not top_act:
        lines.append("  None found.")
    else:
        for sub, weighted_count in top_act:
            lines.append(f"  {sub}  (weighted count: {weighted_count:.1f})")
    lines.append("")

    if not actives_only:
        lines.append("--- Most Common Substructures in Inactives ---")
        top_inact = stats["top_substructures_inactives"][:15]
        if not top_inact:
            lines.append("  None found.")
        else:
            for sub, weighted_count in top_inact:
                lines.append(f"  {sub}  (weighted count: {weighted_count:.1f})")
        lines.append("")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_aggregate_stats(bit_db: dict) -> dict:
    """Compute dataset-level statistics from the bit database.

    Does NOT need shap_train. Derives statistics from bit_db only.

    Returns dict with keys:
        top_active_bits: list of {bit, active_ratio, dominant_sub, n_activations, n_unique_subs}
                         sorted by active_ratio descending, min 3 activations
        top_inactive_bits: same but sorted by active_ratio ascending
        active_exclusive_bits: active_ratio > 0.9, n_activations >= 3
        inactive_exclusive_bits: active_ratio < 0.1, n_activations >= 3
        top_substructures_actives: list of (sub_smi, weighted_count), most common in actives
        top_substructures_inactives: same for inactives
        collision_stats: {total_bits, unambiguous, ambiguous, highly_ambiguous(>=5), ambiguity_rate}
        most_ambiguous_bits: top 20 by n_unique_substructures
    """
    if not bit_db:
        empty: dict[str, Any] = {
            "top_active_bits": [],
            "top_inactive_bits": [],
            "active_exclusive_bits": [],
            "inactive_exclusive_bits": [],
            "top_substructures_actives": [],
            "top_substructures_inactives": [],
            "collision_stats": {
                "total_bits": 0,
                "unambiguous": 0,
                "ambiguous": 0,
                "highly_ambiguous": 0,
                "ambiguity_rate": 0.0,
            },
            "most_ambiguous_bits": [],
        }
        return empty

    # --- Build per-bit summary rows ---
    rows: list[dict] = []
    for bit, info in bit_db.items():
        n_activations: int = info.get("total_activations", 0)
        n_unique_subs: int = info.get("n_unique_substructures", 0)
        dominant_sub: str | None = info.get("dominant_substructure")
        active_ratio: float = float(info.get("active_ratio", 0.0))

        rows.append(
            {
                "bit": bit,
                "active_ratio": active_ratio,
                "dominant_sub": dominant_sub,
                "n_activations": n_activations,
                "n_unique_subs": n_unique_subs,
            }
        )

    # --- Filtered rows (min 3 activations) ---
    qualified = [r for r in rows if r["n_activations"] >= 3]

    top_active_bits = sorted(qualified, key=lambda r: r["active_ratio"], reverse=True)
    top_inactive_bits = sorted(qualified, key=lambda r: r["active_ratio"])
    active_exclusive_bits = [r for r in qualified if r["active_ratio"] > 0.9]
    inactive_exclusive_bits = [r for r in qualified if r["active_ratio"] < 0.1]

    # Sort exclusive lists for determinism
    active_exclusive_bits.sort(key=lambda r: r["active_ratio"], reverse=True)
    inactive_exclusive_bits.sort(key=lambda r: r["active_ratio"])

    # --- Substructure frequency weighted by active/inactive counts ---
    active_sub_counts: dict[str, float] = defaultdict(float)
    inactive_sub_counts: dict[str, float] = defaultdict(float)

    for bit, info in bit_db.items():
        substructures: dict[str, int] = info.get("substructures", {})
        active_freq: int = info.get("active_freq", 0)
        inactive_freq: int = info.get("inactive_freq", 0)
        total: int = active_freq + inactive_freq
        if total == 0:
            continue
        active_frac = active_freq / total
        inactive_frac = inactive_freq / total

        for sub_smi, count in substructures.items():
            active_sub_counts[sub_smi] += count * active_frac
            inactive_sub_counts[sub_smi] += count * inactive_frac

    top_substructures_actives = sorted(
        active_sub_counts.items(), key=lambda x: x[1], reverse=True
    )
    top_substructures_inactives = sorted(
        inactive_sub_counts.items(), key=lambda x: x[1], reverse=True
    )

    # --- Collision statistics ---
    total_bits = len(bit_db)
    unambiguous = sum(1 for r in rows if r["n_unique_subs"] <= 1)
    ambiguous = sum(1 for r in rows if r["n_unique_subs"] > 1)
    highly_ambiguous = sum(1 for r in rows if r["n_unique_subs"] >= 5)
    ambiguity_rate = (ambiguous / total_bits * 100.0) if total_bits > 0 else 0.0

    collision_stats = {
        "total_bits": total_bits,
        "unambiguous": unambiguous,
        "ambiguous": ambiguous,
        "highly_ambiguous": highly_ambiguous,
        "ambiguity_rate": ambiguity_rate,
    }

    most_ambiguous_bits = sorted(rows, key=lambda r: r["n_unique_subs"], reverse=True)[:20]

    return {
        "top_active_bits": top_active_bits,
        "top_inactive_bits": top_inactive_bits,
        "active_exclusive_bits": active_exclusive_bits,
        "inactive_exclusive_bits": inactive_exclusive_bits,
        "top_substructures_actives": top_substructures_actives,
        "top_substructures_inactives": top_substructures_inactives,
        "collision_stats": collision_stats,
        "most_ambiguous_bits": most_ambiguous_bits,
    }


def select_aggregate_context(query: str, stats: dict) -> str:
    """Select the most relevant aggregate stats for the given query.

    Routes by keywords:
    - collision/ambiguous/hash → collision stats + most ambiguous bits
    - active/activit/correl/assoc → top active bits
    - inactive → top inactive bits
    - exclusive → active_exclusive_bits + inactive_exclusive_bits
    - substructure/fragment/common/frequent → top substructures (actives only if "activ" in query)
    - how many/number/count/statistic/summary → collision stats + counts
    - (nothing matched) → collision stats + top active bits

    Returns a multi-line string starting with '=== TRAINING DATASET STATISTICS ===' ready for LLM injection.
    """
    q = query.lower()
    lines: list[str] = ["=== TRAINING DATASET STATISTICS ===", ""]

    matched = False

    if any(kw in q for kw in ("collision", "ambiguous", "hash")):
        _add_collision_context(lines, stats)
        matched = True

    elif any(kw in q for kw in ("exclusive",)):
        _add_exclusive_context(lines, stats)
        matched = True

    elif any(kw in q for kw in ("substructure", "fragment", "common", "frequent")):
        actives_only = "activ" in q
        _add_substructure_context(lines, stats, actives_only=actives_only)
        matched = True

    elif any(kw in q for kw in ("how many", "number", "count", "statistic", "summary")):
        _add_collision_context(lines, stats)
        cs = stats["collision_stats"]
        lines.append(f"Active-exclusive bits (ratio>0.9, n>=3): {len(stats['active_exclusive_bits'])}")
        lines.append(f"Inactive-exclusive bits (ratio<0.1, n>=3): {len(stats['inactive_exclusive_bits'])}")
        lines.append(f"Bits with >=3 activations: {sum(1 for b in stats['top_active_bits']) + sum(1 for b in stats['top_inactive_bits']) - len([b for b in stats['top_active_bits'] if b in stats['top_inactive_bits']])}")
        lines.append("")
        matched = True

    elif "inactive" in q:
        _add_inactive_bits_context(lines, stats)
        matched = True

    elif any(kw in q for kw in ("active", "activit", "correl", "assoc")):
        _add_active_bits_context(lines, stats)
        matched = True

    if not matched:
        _add_collision_context(lines, stats)
        _add_active_bits_context(lines, stats)

    return "\n".join(lines)
