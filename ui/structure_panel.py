"""Structure panel — right-column viewer for referenced molecules."""

import streamlit as st
from io import BytesIO
from typing import Optional


@st.cache_data(show_spinner=False)
def _render_mol_png(smiles: str, width: int = 280, height: int = 200) -> bytes | None:
    """Render a SMILES string to PNG bytes. Cached by SMILES string."""
    from rdkit import Chem
    from rdkit.Chem import Draw
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        mol = Chem.MolFromSmarts(smiles)
    if mol is None:
        return None
    img = Draw.MolToImage(mol, size=(width, height))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class StructurePanel:
    """Right-column panel: Referenced Structures."""

    def render(self):
        """Render the structure panel."""
        st.markdown(
            "<div class='panel-title'>🔬 Structure Viewer</div>",
            unsafe_allow_html=True,
        )
        self._render_referenced_structures()

    def _render_referenced_structures(self):
        st.markdown('<div class="section-header">Referenced Structures</div>',
                    unsafe_allow_html=True)

        structures = st.session_state.get("current_structures", [])

        if not structures:
            st.caption("Structures mentioned in chat will appear here.")
            return

        border_colors = {
            "active":   "var(--color-success)",
            "inactive": "var(--color-danger)",
            "absent":   "var(--color-warning)",
            "neutral":  "var(--color-text-dim)",
        }
        # Text labels paired with colors so state is never color-only (WCAG 1.4.1)
        state_labels = {
            "active":   "Active",
            "inactive": "Inactive",
            "absent":   "Absent from molecule",
            "neutral":  "Fragment",
        }

        for struct in structures:
            smiles = struct.get("smiles", "")
            label = struct.get("label", "")
            sublabel = struct.get("sublabel", "")
            card_type = struct.get("type", "neutral")
            color = border_colors.get(card_type, "var(--color-text-dim)")
            state_text = state_labels.get(card_type, "")

            try:
                png_bytes = _render_mol_png(smiles)
                if png_bytes is None:
                    continue

                state_badge = (
                    f"<span style='font-size:0.6rem;padding:1px 5px;border-radius:3px;"
                    f"background:{color};color:var(--color-bg);font-weight:600;"
                    f"letter-spacing:0.04em;margin-right:0.4rem;vertical-align:middle;"
                    f"opacity:0.9;'>{state_text}</span>"
                    if state_text else ""
                )
                st.markdown(
                    f"<div class='mol-card-label' "
                    f"style='color:{color};border-left:3px solid {color};'>"
                    f"{state_badge}{label}"
                    f"<span style='color:var(--color-text-dark);font-size:0.6875rem;margin-left:0.4rem;'>"
                    f"{sublabel}</span></div>",
                    unsafe_allow_html=True,
                )
                st.image(
                    BytesIO(png_bytes),
                    width="stretch",
                    caption=smiles,
                )

            except Exception:
                st.caption(f"⚠ {label} (render error)")

