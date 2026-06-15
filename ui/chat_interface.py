"""Chat interface component."""

import streamlit as st
from typing import Optional
import re
from io import BytesIO

from llm.chat_handler import ChatHandler
from llm.prompt_templates import PromptTemplates
from rag.retriever import Retriever
from core.molecule_parser import MoleculeParser
from fingerprints.maccs_interpreter import MACCSInterpreter
from fingerprints.maccs_keys import MACCSKeys
from descriptors.descriptor_explainer import DescriptorExplainer
from descriptors.descriptor_registry import DescriptorRegistry
from core.query_router import extract_smiles as _extract_smiles

# Shown when a query implies a SMILES but none could be extracted from the text.
_NO_SMILES_HINT = (
    'I couldn\'t find a valid SMILES string in your message. '
    'Please put your SMILES between quotes so I can identify it correctly.\n\n'
    'Example: `Predict this molecule: "O=C(Nc1ccccc1)c1ccncc1"`'
)

# Returned deterministically when the query needs a trained model that is not loaded.
_NEED_MODEL_LOADED = (
    "No model loaded. To run predictions, upload a labelled training CSV "
    "(SMILES + activity column) in the **Evaluation** tab — the model trains automatically."
)

# Returned deterministically (no LLM call) when an action verb is detected
# but no molecule is available — prevents hallucination of fake descriptors.
_NEED_SMILES_FOR_ACTION = (
    "To run a prediction I need a SMILES string. You can:\n\n"
    "- Paste it directly in your message "
    "(e.g. `predict CC(=O)Oc1ccccc1C(=O)O`)\n"
    "- Select a molecule in the **Visualizer** panel on the left\n"
    "- Load a dataset in the **Evaluation** or **Virtual Screening** section"
)

# Keywords that signal a query is within RAGMODEX scope.
# Any match → LLM is called. No match → out-of-scope guard fires.
_SCOPE_KEYWORDS = re.compile(
    r'smiles|ecfp|fcfp|morgan|maccs|fingerprint|substructure|smarts'
    r'|\binchi\b|tanimoto|jaccard|ecfp6|ecfp4|fcfp6|fcfp4|bit.vector|hash.collision'
    r'|\bshap\b|qsar|random.forest|feature.importan|bioactiv|applicability.domain'
    r'|virtual.screening|cheminformatic'
    r'|lipinski|drug.lik|drug-lik|rule.of.five|drug.discov|drug.design|pharmacophor'
    r'|\badmet\b|\bscaffold\b|lead.compound|fragment.based'
    r'|solubil|bioavailab|membrane.permeab'
    r'|\bqed\b|\btpsa\b|\blogp\b|molecular.weight|molar.weight'
    r'|hydrogen.bond|\bhbd\b|\bhba\b|rotatable.bond|heavy.atom|polar.surface'
    r'|chirality|stereocentr|conformer|isomer'
    r'|inhibitor|\bligand\b|binding.affinity|\bic50\b|\bki\b'
    r'|selectiv|potenc|\bmolecule\b|\bmolecular\b|\bdescriptor\b'
    r'|ragmodex',
    re.IGNORECASE,
)

# Common Italian function words for language detection (no LLM needed).
_ITALIAN_WORDS = re.compile(
    r'\b(?:cosa|come|chi|quando|dove|perch[eé]|vorrei|puoi|posso|può|puo'
    r'|barzelletta|raccontami|spiegami|fammi|dimmi|aiutami|voglio'
    r'|questo|questa|questi|queste|sono|hai|ho|siamo|avete'
    r'|della|delle|degli|nella|nelle|negli|dal|dalla|nel|sul)\b',
    re.IGNORECASE,
)

_OUT_OF_SCOPE_IT = (
    "Questa domanda esula dallo scopo di RAGMODEX. Posso aiutarti con:\n\n"
    "- Predizione di attività biologica e interpretazione SHAP\n"
    "- Analisi bit-collision e substructure search\n"
    "- Applicability domain e affidabilità del modello\n"
    "- Guided design e virtual screening\n"
    "- Concetti di QSAR, fingerprint e drug-likeness\n\n"
    "Come posso esserti utile?"
)

_OUT_OF_SCOPE_EN = (
    "This question is outside the scope of RAGMODEX. I can help you with:\n\n"
    "- Bioactivity prediction and SHAP interpretation\n"
    "- Bit-collision analysis and substructure search\n"
    "- Applicability domain and model reliability\n"
    "- Guided design and virtual screening\n"
    "- QSAR, fingerprint, and drug-likeness concepts\n\n"
    "How can I help you?"
)


class ChatInterface:
    """Chat interface component for LLM interactions."""

    # Common synonym aliases for descriptor names
    DESCRIPTOR_SYNONYMS: dict[str, str] = {
        "mw": "MolWt",
        "molwt": "MolWt",
        "weight": "MolWt",
        "molecular weight": "MolWt",
        "mol weight": "MolWt",
        "logp": "MolLogP",
        "log p": "MolLogP",
        "alogp": "MolLogP",
        "xlogp": "MolLogP",
        "hbd": "NumHDonors",
        "h bond donors": "NumHDonors",
        "hbond donors": "NumHDonors",
        "donors": "NumHDonors",
        "hba": "NumHAcceptors",
        "h bond acceptors": "NumHAcceptors",
        "hbond acceptors": "NumHAcceptors",
        "acceptors": "NumHAcceptors",
        "tpsa": "TPSA",
        "polar surface area": "TPSA",
        "psa": "TPSA",
        "rotbonds": "NumRotatableBonds",
        "rotatable bonds": "NumRotatableBonds",
        "rot bonds": "NumRotatableBonds",
        "rings": "RingCount",
        "ring count": "RingCount",
        "aromatic rings": "NumAromaticRings",
        "qed": "qed",
        "heavy atoms": "NumHeavyAtoms",
        "fsp3": "FractionCSP3",
        "sp3": "FractionCSP3",
        "exactmw": "ExactMolWt",
        "exact mw": "ExactMolWt",
        "exact weight": "ExactMolWt",
        "mr": "MolMR",
        "molar refractivity": "MolMR",
        "heteroatoms": "NumHeteroatoms",
        "asa": "LabuteASA",
        "labute asa": "LabuteASA",
    }

    def __init__(
        self,
        chat_handler: Optional[ChatHandler] = None,
        retriever: Optional[Retriever] = None,
    ):
        self.chat_handler = chat_handler
        self.retriever = retriever
        self.descriptor_explainer = DescriptorExplainer()
        self._pending_visuals: dict | None = None
        self._init_session_state()

    def _init_session_state(self):
        if "messages" not in st.session_state:
            st.session_state.messages = []

    def render_messages(self):
        """Render chat message history (call inside st.container for scrolling)."""
        if not st.session_state.messages:
            self._render_welcome()
            return
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                self._render_message(message)

    def _render_welcome(self):
        """Context-aware welcome: setup guide when app is unconfigured, live examples when ready."""
        has_model = st.session_state.get("rf_model") is not None
        has_data = st.session_state.get("bit_database") is not None

        st.markdown(
            "<div style='padding:1.2rem 0 0.6rem 0;' role='region' aria-label='Welcome'>"
            "<h1 style='font-family:var(--font-main);color:var(--color-text);"
            "font-size:1.3rem;margin:0 0 0.3rem 0;'>MolChat</h1>"
            "<p style='color:var(--color-text-muted);font-size:0.85rem;margin:0;'>"
            "Molecular AI Interpreter &mdash; ask questions about bioactivity predictions, "
            "fingerprint bits, SHAP values, and applicability domain."
            "</p></div>",
            unsafe_allow_html=True,
        )

        if not has_model or not has_data:
            # ── Setup guide (partial or nothing loaded) ────────────────────
            st.markdown(
                "<div class='section-header' style='margin-top:1rem;'>Setup</div>",
                unsafe_allow_html=True,
            )
            setup_steps = [
                (
                    has_data,
                    "Upload training data",
                    "CSV with a SMILES column and a binary activity label (0/1)",
                    "Open <b>Training Data</b> in the sidebar",
                ),
                (
                    has_model,
                    "Upload your model",
                    "Scikit-learn RandomForest (.pkl or .joblib)",
                    "Open <b>Model</b> in the sidebar",
                ),
                (
                    has_model and has_data,
                    "Start chatting",
                    "Predict molecules, explain bits, check applicability domain",
                    None,
                ),
            ]
            steps_html = "<ol style='list-style:none;padding:0;margin:0;'>"
            for i, (done, title, desc, hint) in enumerate(setup_steps, 1):
                check_color = "var(--color-success)" if done else "var(--color-text-dim)"
                check_icon  = "✓" if done else str(i)
                border_color = "var(--color-success)" if done else "var(--color-border)"
                hint_html   = (
                    f"<div style='color:var(--color-text-dim);font-size:0.75rem;"
                    f"margin-top:0.2rem;line-height:1.4;'>{hint}</div>"
                    if hint and not done else ""
                )
                done_attr = " aria-current='step'" if not done else ""
                steps_html += (
                    f"<li{done_attr} style='display:flex;align-items:flex-start;gap:0.7rem;"
                    f"padding:0.6rem 0.75rem;margin-bottom:0.35rem;"
                    f"background:var(--color-card);border-radius:8px;"
                    f"border:1px solid {border_color};'>"
                    f"<span aria-hidden='true' style='color:{check_color};font-size:0.8rem;"
                    f"font-weight:700;background:var(--color-surface-deep);"
                    f"border:1px solid {border_color};border-radius:50%;width:1.4rem;"
                    f"height:1.4rem;display:flex;align-items:center;justify-content:center;"
                    f"flex-shrink:0;margin-top:0.05rem;'>{check_icon}</span>"
                    f"<div>"
                    f"<div style='font-size:0.875rem;font-weight:600;color:var(--color-text);line-height:1.3;'>"
                    f"{title}</div>"
                    f"<div style='font-size:0.75rem;color:var(--color-text-muted);margin-top:0.05rem;line-height:1.4;'>{desc}</div>"
                    f"{hint_html}"
                    f"</div></li>"
                )
            steps_html += "</ol>"
            st.markdown(steps_html, unsafe_allow_html=True)

            # ── Command reference (always useful, collapsed by default) ────
            with st.expander(":material/terminal: Chat commands", expanded=False):
                st.markdown(
                    "These phrases trigger structured responses — faster than free-form questions:\n\n"
                    "| Command | Example |\n"
                    "|---|---|\n"
                    "| `explain <descriptor>` | `explain LogP` |\n"
                    "| `calculate <desc> for <SMILES>` | `calculate TPSA for \"c1ccccc1\"` |\n"
                    "| `validate <SMILES>` | `validate \"CC(=O)Oc1ccc\"` |\n"
                    "| `maccs key <N>` | `maccs key 160` |\n"
                    "| Predict with SMILES in quotes | `Predict \"CC(C)Cc1ccccc1\"` |"
                )
        else:
            # ── Example queries (app is ready) — compact chemical command palette ──
            st.markdown(
                "<div class='section-header' style='margin-top:1rem;'>Example queries</div>",
                unsafe_allow_html=True,
            )
            examples = [
                ("PREDICT",  "#8890c4",
                 'Predict bioactivity of <code style="color:#50c896;background:#0e1128;padding:1px 4px;border-radius:3px;">c1ccccc1</code>',
                 'Predict this molecule: "c1ccccc1"'),
                ("ECFP BIT", "#8890c4",
                 'What substructure does <code style="color:#50c896;background:#0e1128;padding:1px 4px;border-radius:3px;">ECFP6_1220</code> encode?',
                 "What does ECFP6_1220 represent?"),
                ("COMPARE",  "#8890c4",
                 'Activity delta: <code style="color:#50c896;background:#0e1128;padding:1px 4px;border-radius:3px;">CC</code> vs <code style="color:#50c896;background:#0e1128;padding:1px 4px;border-radius:3px;">CCC</code>',
                 'Compare "CC" vs "CCC"'),
                ("AD CHECK", "#8890c4",
                 'Is <code style="color:#50c896;background:#0e1128;padding:1px 4px;border-radius:3px;">c1ccccc1</code> inside the applicability domain?',
                 'Can I trust the prediction for "c1ccccc1"?'),
            ]
            col_a, col_b = st.columns(2)
            for i, (tag, tag_color, query_html, prompt) in enumerate(examples):
                col = col_a if i % 2 == 0 else col_b
                with col:
                    st.markdown(
                        f"<div style='background:var(--color-surface-deep);"
                        f"border:1px solid var(--color-border);border-radius:8px;"
                        f"padding:0.55rem 0.7rem;margin-bottom:0.35rem;"
                        f"line-height:1.4;'>"
                        f"<span style='font-size:0.625rem;font-weight:700;color:{tag_color};"
                        f"text-transform:uppercase;letter-spacing:0.08em;"
                        f"margin-right:0.45rem;'>{tag}</span>"
                        f"<span style='font-size:0.75rem;color:var(--color-text);'>"
                        f"{query_html}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "Ask →",
                        key=f"_welcome_ex_{tag.replace(' ', '_')}",
                        width="stretch",
                    ):
                        st.session_state["_pending_prompt"] = prompt
                        st.rerun()

            # ── Command reference ──────────────────────────────────────────
            with st.expander(":material/terminal: Chat commands", expanded=False):
                st.markdown(
                    "These phrases trigger structured responses — faster than free-form questions:\n\n"
                    "| Command | Example |\n"
                    "|---|---|\n"
                    "| `explain <descriptor>` | `explain LogP` |\n"
                    "| `calculate <desc> for <SMILES>` | `calculate TPSA for \"c1ccccc1\"` |\n"
                    "| `validate <SMILES>` | `validate \"CC(=O)Oc1ccc\"` |\n"
                    "| `maccs key <N>` | `maccs key 160` |\n"
                    "| Predict with SMILES in quotes | `Predict \"CC(C)Cc1ccccc1\"` |"
                )

    def _render_message(self, message: dict):
        """Render a single message. Images go to the right panel; only cards/text stay here."""
        if message["role"] == "user":
            st.markdown(message["content"])
            return

        visuals = message.get("visuals") or {}

        # Prediction card (stays in chat)
        if "prediction" in visuals:
            p = visuals["prediction"]
            self._render_prediction_card(p["label"], p["p_active"], p["p_inactive"])

        # AD badge (stays in chat)
        if "ad_result" in visuals:
            a = visuals["ad_result"]
            self._render_ad_badge(a["inside_ad"], a["distance"], a["threshold"])

        # Comparison summary line (no images in chat)
        if "comparison" in visuals:
            comp = visuals["comparison"]
            delta = comp["p2"] - comp["p1"]
            color = "var(--color-success)" if delta > 0 else "var(--color-danger)"
            st.markdown(
                f"<div style='font-size:0.85rem;color:var(--color-text-muted);margin-bottom:0.3rem;'>"
                f"Tanimoto: <b style='color:var(--color-text);'>{comp['tanimoto']:.3f}</b> &nbsp;·&nbsp; "
                f"ΔP(active): <b style='color:{color};'>{delta:+.4f}</b>"
                f"</div>",
                unsafe_allow_html=True,
            )

        # Edit summary line (no images in chat)
        if "edit_result" in visuals:
            edit = visuals["edit_result"]
            delta = edit["p_mod"] - edit["p_orig"]
            color = "var(--color-success)" if delta > 0 else "var(--color-danger)"
            st.markdown(
                f"<div style='font-size:0.85rem;color:var(--color-text-muted);margin-bottom:0.3rem;'>"
                f"ΔP(active): <b style='color:{color};'>{delta:+.4f}</b> &nbsp;·&nbsp; "
                f"Structures updated in panel →"
                f"</div>",
                unsafe_allow_html=True,
            )

        # LLM / static text
        st.markdown(message["content"])

    # ── Visual helpers ────────────────────────────────────────────────────

    @staticmethod
    def _render_prediction_card(label: str, p_active: float, p_inactive: float):
        card_class = "prediction-active" if label == "Active" else "prediction-inactive"
        icon = "🟢" if label == "Active" else "🔴"
        bar_class = "prob-bar-active" if label == "Active" else "prob-bar-inactive"
        bar_width = p_active * 100
        st.markdown(f"""
        <div class="prediction-card {card_class}">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-size:1.15rem;font-weight:600;font-family:var(--font-main);">
                    {icon} {label.upper()}
                </span>
                <span style="color:var(--color-text-muted);font-size:0.85rem;">
                    P(active) = {p_active:.4f} &nbsp;·&nbsp; P(inactive) = {p_inactive:.4f}
                </span>
            </div>
            <div class="prob-bar">
                <div class="prob-bar-fill {bar_class}" style="width:{bar_width:.1f}%;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    @staticmethod
    def _render_ad_badge(inside_ad: bool, distance: float, threshold: float):
        if inside_ad:
            cls, icon, status = "ad-inside", "✅", "INSIDE AD"
        else:
            cls, icon, status = "ad-outside", "⚠️", "OUTSIDE AD"
        st.markdown(
            f'<div><span class="ad-badge {cls}">'
            f'{icon} {status} — distance: {distance:.3f} &nbsp;(threshold: {threshold:.3f})'
            f'</span></div>',
            unsafe_allow_html=True,
        )

    @staticmethod
    def _mol_to_bytes(smiles: str, size: tuple = (280, 220)) -> Optional[bytes]:
        """Render a single molecule to PNG bytes. Returns None on failure."""
        try:
            from rdkit import Chem
            from rdkit.Chem import Draw
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                mol = Chem.MolFromSmarts(smiles)
            if mol is None:
                return None
            img = Draw.MolToImage(mol, size=size)
            buf = BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
        except Exception:
            return None

    @staticmethod
    def _grid_to_bytes(
        items: list,
        cols: int = 4,
        sub_size: tuple = (220, 180),
    ) -> Optional[bytes]:
        """Render a list of {smiles, label} dicts as a grid PNG. Returns None on failure."""
        try:
            from rdkit import Chem
            from rdkit.Chem import Draw
            mols, legends = [], []
            for item in items:
                smi = item.get("smiles", "")
                mol = Chem.MolFromSmiles(smi) or Chem.MolFromSmarts(smi)
                if mol is not None:
                    mols.append(mol)
                    legends.append(item.get("label", ""))
            if not mols:
                return None
            img = Draw.MolsToGridImage(
                mols,
                molsPerRow=min(cols, len(mols)),
                subImgSize=sub_size,
                legends=legends,
            )
            buf = BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
        except Exception:
            return None

    def handle_input(self, prompt: str):
        """Process user input and update session state."""
        self._pending_visuals = None
        st.session_state.messages.append({"role": "user", "content": prompt})
        response = self._check_special_commands(prompt)
        if response is None:
            response = self._generate_response(prompt)
        msg: dict = {"role": "assistant", "content": response}
        if self._pending_visuals:
            msg["visuals"] = self._pending_visuals
        st.session_state.messages.append(msg)
        st.rerun()

    # ── SMILES detection pattern (used in both _check_special_commands and
    #    _generate_response to find SMILES strings embedded in free-form text)
    _SMILES_PAT = re.compile(
        r"(?<!\w)"                          # not preceded by a word char
        r"([A-Za-z\[][A-Za-z0-9@+\-\[\]"
        r"\\/#%().=]+(?:[cnops]|[A-Z])"     # must contain ≥1 chemistry character
        r"[A-Za-z0-9@+\-\[\]\\/#%().=]*)"  # rest of token
        r"(?!\w)",                          # not followed by word char
    )

    def _check_special_commands(self, prompt: str) -> Optional[str]:
        """Check for special commands and patterns in prompt."""
        prompt_lower = prompt.lower().strip()

        # Guard: action verb present but no molecule available → deterministic
        # message, no LLM call, no risk of hallucination.
        if re.match(r'^(?:predict|interpret|analyze)\b', prompt_lower):
            _smiles_in_msg = _extract_smiles(prompt)
            if not _smiles_in_msg:
                # Also validate the raw argument after the verb — handles short SMILES
                # like "CCO" (3 chars) that fall below the router's 6-char tier-2 minimum.
                _arg_m = re.match(r'^(?:predict|interpret|analyze)\s+(.+)', prompt, re.IGNORECASE)
                if _arg_m:
                    _arg_raw = _arg_m.group(1).strip().strip("\"'")
                    if MoleculeParser.validate(_arg_raw)[0]:
                        _smiles_in_msg = _arg_raw
            if not _smiles_in_msg and not st.session_state.get("current_smiles", ""):
                return _NEED_SMILES_FOR_ACTION

        # Dedicated compare handler — handles short SMILES (< 6 chars) not caught
        # by the router's tier-2 pattern, and detects canonical identity before
        # running the expensive SHAP pipeline.
        _cmp = re.match(r'compare\s+(.+?)\s+(?:vs\.?|versus)\s+(.+)', prompt, re.IGNORECASE)
        if _cmp:
            _raw1 = _cmp.group(1).strip().strip("\"'")
            _raw2 = _cmp.group(2).strip().strip("\"'")
            _v1, _ = MoleculeParser.validate(_raw1)
            _v2, _ = MoleculeParser.validate(_raw2)
            if _v1 and _v2:
                from rdkit import Chem as _Chem
                _can1 = _Chem.MolToSmiles(_Chem.MolFromSmiles(_raw1))
                _can2 = _Chem.MolToSmiles(_Chem.MolFromSmiles(_raw2))
                if _can1 == _can2:
                    return self._identical_molecules_response(_can1)
                # Different valid molecules — route to SHAP comparison if model loaded
                if (st.session_state.get("rf_model") is not None
                        and st.session_state.get("shap_explainer") is not None):
                    return self._compare_molecules(_raw1, _raw2, prompt)
                else:
                    return _NEED_MODEL_LOADED
            elif not _v1 or not _v2:
                # At least one side is not a valid SMILES — let LLM handle it
                pass

        # Explicit descriptor calculation: "calculate <desc> for <SMILES>"
        # Must run BEFORE the model router so "calculate X for <SMILES>" is not
        # misclassified as a molecule_query by classify_query.
        calc_match = re.match(
            r"(?:calculate|calc)\s+(\S+)\s+for\s+(.+)",
            prompt_lower,
        )
        if calc_match:
            desc_name = calc_match.group(1)
            orig_split = re.split(r"\s+for\s+", prompt, maxsplit=1, flags=re.IGNORECASE)
            smiles_str = orig_split[1].strip() if len(orig_split) == 2 else calc_match.group(2).strip()
            return self._calculate_descriptor(desc_name, smiles_str)

        # SMILES validation — must run before model routing; a valid SMILES in the
        # prompt would otherwise be misclassified as molecule_query.
        if prompt_lower.startswith("validate "):
            return self._validate_smiles(prompt[9:].strip().strip("\"'"))

        # ── Molecule prediction pipeline ──────────────────────────────────
        # Triggered when model+explainer are loaded AND user either:
        #  a) uses an explicit predict/interpret/analyze command, OR
        #  b) pastes a SMILES (detected by the pattern above)
        model = st.session_state.get("rf_model")
        explainer = st.session_state.get("shap_explainer")

        print(f"[ROUTER] model={'loaded' if model else 'None'}  "
              f"explainer={'loaded' if explainer else 'None'}")

        if model is not None and explainer is not None:
            from core.query_router import classify_query as _cq, extract_smiles as _ex

            _qtype, _params = _cq(prompt)
            print(f"[ROUTER] query_type={_qtype!r}  params={_params}")

            if _qtype == "comparison":
                return self._compare_molecules(
                    _params["smiles1"], _params["smiles2"], prompt
                )

            if _qtype == "ad_check":
                smi = _params.get("smiles") or st.session_state.get("current_smiles", "")
                print(f"[ROUTER] ad_check  smiles={smi!r}")
                if smi and MoleculeParser.validate(smi)[0]:
                    return self._check_applicability_domain(smi, prompt)
                if not _params.get("smiles") and not st.session_state.get("current_smiles"):
                    return _NO_SMILES_HINT

            if _qtype == "mol_edit":
                smi = _params.get("smiles") or st.session_state.get("current_smiles", "")
                print(f"[ROUTER] mol_edit  smiles={smi!r}")
                if smi and MoleculeParser.validate(smi)[0]:
                    return self._apply_mol_edit(smi, prompt)
                if not smi:
                    return _NO_SMILES_HINT

            if _qtype == "design_query":
                smi = _params.get("smiles") or st.session_state.get("current_smiles", "")
                print(f"[ROUTER] design_query  smiles={smi!r}")
                if smi and MoleculeParser.validate(smi)[0]:
                    return self._run_design_suggestions(smi, prompt)
                return (
                    "To run design suggestions I need a SMILES string. "
                    "Example: `design suggestions for \"c1ccccc1\"` — "
                    "or open the **🧪 Design** page from the sidebar for an interactive UI."
                )

            if _qtype == "suggestions":
                smi = _params.get("smiles") or st.session_state.get("current_smiles", "")
                print(f"[ROUTER] suggestions  smiles={smi!r}")
                if smi and MoleculeParser.validate(smi)[0]:
                    return self._suggest_modifications(smi, prompt)
                if not smi:
                    return _NO_SMILES_HINT

            if _qtype == "molecule_query":
                print(f"[ROUTER] molecule_query  smiles={_params['smiles']!r}")
                return self._predict_and_interpret_molecule(_params["smiles"], prompt)

            # Explicit "predict / interpret / analyze" command (overrides router
            # for cases like "predict" with no SMILES in query).
            # Match on the original prompt (not prompt_lower) to preserve SMILES case.
            pred_cmd = re.match(
                r"(?:predict|interpret|analyze)(?:\s+(.+))?$",
                prompt, re.IGNORECASE,
            )
            if pred_cmd:
                arg = (pred_cmd.group(1) or "").strip().strip("\"'")
                target_smiles = arg if arg else st.session_state.get("current_smiles", "")
                if target_smiles and not re.match(r"^(this|that|the|me|my)\b", arg, re.IGNORECASE):
                    if MoleculeParser.validate(target_smiles)[0]:
                        return self._predict_and_interpret_molecule(target_smiles, prompt)

        else:
            # model or explainer not loaded — check whether this query would have
            # needed a model so we can give a useful error instead of falling through
            # to the generic out-of-scope response.
            from core.query_router import classify_query as _cq_nomodel, extract_smiles as _ex_nomodel
            _qtype_nm, _params_nm = _cq_nomodel(prompt)
            _model_qtypes = {"molecule_query", "comparison", "mol_edit", "design_query", "suggestions"}
            if _qtype_nm in _model_qtypes:
                # Only fire when there is actually a SMILES to act on, so we don't
                # swallow genuinely ambiguous queries.
                _smi_nm = (
                    _params_nm.get("smiles")
                    or _params_nm.get("smiles1")
                    or st.session_state.get("current_smiles", "")
                )
                if _smi_nm and MoleculeParser.validate(_smi_nm)[0]:
                    return _NEED_MODEL_LOADED
            # predict/interpret/analyze verb with a valid SMILES but no model
            _pred_cmd_nm = re.match(
                r"(?:predict|interpret|analyze)(?:\s+(.+))?$",
                prompt, re.IGNORECASE,
            )
            if _pred_cmd_nm:
                _arg_nm = (_pred_cmd_nm.group(1) or "").strip().strip("\"'")
                _target_nm = _arg_nm if _arg_nm else st.session_state.get("current_smiles", "")
                if (_target_nm
                        and not re.match(r"^(this|that|the|me|my)\b", _arg_nm, re.IGNORECASE)
                        and MoleculeParser.validate(_target_nm)[0]):
                    return _NEED_MODEL_LOADED

        # ── Bit-DB-only queries (no model required) ───────────────────────
        bit_db = st.session_state.get("bit_database") or {}
        from core.query_router import classify_query as _cq2
        _qtype2, _params2 = _cq2(prompt)
        if bit_db:
            if _qtype2 == "substructure_search":
                return self._search_substructure_activity(prompt)

            if _qtype2 == "aggregate_query":
                return self._answer_aggregate_query(prompt)
        else:
            if _qtype2 in ("substructure_search", "aggregate_query"):
                return (
                    "⚠️ This query requires a training dataset. "
                    "Upload a labelled CSV (SMILES + activity column) in the sidebar "
                    "to enable substructure and dataset statistics analysis."
                )

        # MACCS key lookup: "maccs key 15" / "maccs 15"
        maccs_match = re.match(r"maccs\s*(?:key)?\s*(\d+)", prompt_lower)
        if maccs_match:
            return self._explain_maccs_key(int(maccs_match.group(1)))

        # ── ECFP bit handlers (most specific first) ──────────────────────
        # Pattern shared by both handlers: any explicit ECFP bit reference
        # Matches: ECFP6_1220, ecfp_1220, ecfp6 1220, morgan bit 1220, bit 1220
        _ECFP_BIT_PAT = (
            r"(?:ecfp\d*[_\s]|morgan[_\s](?:bit[_\s])?|(?:^|\s)bit[_\s])(\d+)"
        )

        # 1. ECFP bit + SHAP value: "ECFP6_1024 SHAP value 0.3"
        ecfp_bit_shap = re.search(
            _ECFP_BIT_PAT
            + r"\s+(?:has\s+)?shap(?:\s+value)?(?:\s+(?:of|=|:))?\s*([+-]?\d*\.?\d+)",
            prompt_lower,
        )
        if ecfp_bit_shap:
            return self._explain_ecfp_bit_shap(
                int(ecfp_bit_shap.group(1)), ecfp_bit_shap.group(2)
            )

        # 2. Plain ECFP bit query (no SHAP value): "What does ECFP6_1220 represent?"
        #    Only trigger when a bit database is loaded OR the query is explicitly ECFP-prefixed
        #    (avoids false positives on generic "bit N" in unrelated contexts)
        ecfp_bit_plain = re.search(_ECFP_BIT_PAT, prompt_lower)
        if ecfp_bit_plain:
            # Require explicit ecfp/morgan prefix OR a loaded bit database
            has_explicit_prefix = bool(
                re.search(r"ecfp|morgan\s+bit", prompt_lower)
            )
            has_bit_db = st.session_state.get("bit_database") is not None
            if has_explicit_prefix or has_bit_db:
                return self._explain_ecfp_bit(int(ecfp_bit_plain.group(1)), prompt)

        # SHAP value questions:
        # "MW SHAP value 0.45", "what does MW SHAP value of 0.45 mean", "SHAP value of MW is 0.45"
        shap_match = re.search(
            r"([A-Za-z]\w*)\s+(?:has\s+)?shap(?:\s+value)?(?:\s+(?:of|=|:))?\s*([+-]?\d*\.?\d+)",
            prompt_lower,
        )
        if shap_match:
            return self._explain_shap_value(shap_match.group(1), shap_match.group(2))

        # Alternative: "shap ... descriptor ... value"
        if "shap" in prompt_lower:
            shap_match2 = re.search(
                r"shap[^?]*?([A-Za-z]\w{2,})\D+([+-]?\d+\.?\d*)",
                prompt_lower,
            )
            if shap_match2:
                return self._explain_shap_value(shap_match2.group(1), shap_match2.group(2))

        # Descriptor explanation: "explain MolWt"
        explain_match = re.match(r"explain\s+(\S+)", prompt_lower)
        if explain_match:
            matched = self._find_descriptor(explain_match.group(1))
            if matched:
                return self._explain_descriptor(matched)

        # Natural language descriptor calc on current loaded molecule:
        # "calculate MW", "what is the logp", "show me TPSA"
        current_smiles = st.session_state.get("current_smiles", "")
        if current_smiles:
            nl_calc = re.match(
                r"(?:calculate|calc|what\s+is\s+the?|compute|show\s+me(?:\s+the)?)\s+([A-Za-z]\w*)",
                prompt_lower,
            )
            if nl_calc:
                matched = self._find_descriptor(nl_calc.group(1))
                if matched:
                    return self._calculate_descriptor(matched, current_smiles)

        # Guard: "calculate/calc <desc>" with no molecule → deterministic message
        if re.match(r'^(?:calculate|calc)\s+\S', prompt_lower) and not current_smiles:
            return _NEED_SMILES_FOR_ACTION

        return None

    def _find_descriptor(self, name: str) -> Optional[str]:
        """Find descriptor name, supporting case-insensitive lookup and synonyms."""
        # Direct match (case-sensitive)
        if DescriptorRegistry.is_valid_descriptor(name):
            return name
        # Case-insensitive match against registry
        for d in DescriptorRegistry.get_all_names():
            if d.lower() == name.lower():
                return d
        # Synonym lookup
        synonym_key = name.lower().strip()
        canonical = self.DESCRIPTOR_SYNONYMS.get(synonym_key)
        if canonical:
            # Verify the canonical name exists in registry
            if DescriptorRegistry.is_valid_descriptor(canonical):
                return canonical
            for d in DescriptorRegistry.get_all_names():
                if d.lower() == canonical.lower():
                    return d
        return None

    def _explain_maccs_key(self, key_number: int) -> str:
        if not MACCSKeys.is_valid_key(key_number):
            return f"Invalid MACCS key number: {key_number}. Valid range: 1–166."
        interp = MACCSInterpreter.interpret_key(key_number)
        if interp is None:
            return f"Could not interpret MACCS key {key_number}."

        response = (
            f"## MACCS Key {key_number}\n\n"
            f"**Description:** {interp.description}\n\n"
            f"**SMARTS pattern:** `{interp.smarts}`\n\n"
            f"**Category:** {interp.category}\n\n"
            f"{interp.explanation}\n"
        )
        current_smiles = st.session_state.get("current_smiles", "")
        if current_smiles:
            mol_interp = MACCSInterpreter.check_key_in_molecule(key_number, current_smiles)
            if mol_interp and mol_interp.is_present is not None:
                status = "**present**" if mol_interp.is_present else "**not present**"
                matches = len(mol_interp.matches) if mol_interp.matches else 0
                response += f"\n---\n**Current molecule:** This key is {status}"
                if matches > 0:
                    response += f" ({matches} match(es) found)"
        return response

    def _explain_descriptor(self, descriptor_name: str) -> str:
        current_smiles = st.session_state.get("current_smiles", "")
        if current_smiles:
            return self.descriptor_explainer.explain_with_value(descriptor_name, current_smiles)
        return self.descriptor_explainer.explain(descriptor_name)

    def _validate_smiles(self, smiles: str) -> str:
        is_valid, message = MoleculeParser.validate(smiles)
        if is_valid:
            mol_info = MoleculeParser.get_info(smiles)
            return (
                f"✅ SMILES is **valid**.\n\n"
                f"**Canonical SMILES:** `{mol_info.canonical_smiles}`\n"
                f"**Formula:** {mol_info.molecular_formula}\n"
                f"**Molecular weight:** {mol_info.molecular_weight:.2f} Da\n"
                f"**Atoms:** {mol_info.num_atoms}\n"
                f"**Heavy atoms:** {mol_info.num_heavy_atoms}\n"
            )
        return f"❌ SMILES is **invalid**: {message}"

    def _calculate_descriptor(self, desc_name: str, smiles: str) -> str:
        from core.descriptor_calculator import DescriptorCalculator
        calculator = DescriptorCalculator()

        smiles = smiles.strip().strip('"').strip("'")
        if not MoleculeParser.validate(smiles)[0]:
            return f"❌ Invalid SMILES: `{smiles}`"

        matched_name = self._find_descriptor(desc_name)
        if matched_name is None:
            return f"❌ Unknown descriptor: `{desc_name}`"

        value, status = calculator.get_descriptor_value(smiles, matched_name)
        if value is not None:
            mol_info = MoleculeParser.get_info(smiles)
            info = DescriptorRegistry.get_info(matched_name)
            unit = info.unit if info and info.unit else ""
            brief = self.descriptor_explainer.get_brief_explanation(matched_name)
            return (
                f"## {matched_name}\n\n"
                f"**Molecule:** `{mol_info.canonical_smiles}`\n\n"
                f"**Value:** {value:.4f} {unit}\n\n"
                f"{brief}\n"
            )
        return f"❌ Could not calculate {matched_name}: {status}"

    def _predict_and_interpret_molecule(self, smiles: str, original_query: str) -> str:
        """Run the full prediction pipeline and build a grounded LLM response.

        Uses the model + SHAP explainer from session state.
        Falls back to a structured static display if no LLM is configured.
        """
        from core.model_pipeline import predict_and_interpret, format_interpretation_context

        model = st.session_state.get("rf_model")
        explainer = st.session_state.get("shap_explainer")
        bit_db = st.session_state.get("bit_database") or {}
        meta = st.session_state.get("bit_database_meta", {})

        # Use fingerprint params from bit_db meta if available (authoritative),
        # otherwise fall back to sidebar settings
        radius = meta.get("radius") or st.session_state.get("fp_radius", 3)
        n_bits = meta.get("n_bits") or st.session_state.get("fp_nbits", 2048)

        print(f"[PIPELINE] predict_and_interpret  smiles={smiles!r}  "
              f"radius={radius}  n_bits={n_bits}  bit_db_size={len(bit_db)}")
        try:
            result = predict_and_interpret(
                smiles, model, explainer, bit_db,
                radius=radius, n_bits=n_bits, top_n=10,
            )
        except Exception as _exc:
            import traceback
            print(f"[PIPELINE] predict_and_interpret CRASHED: {_exc}")
            traceback.print_exc()
            return f"❌ Prediction pipeline crashed: {_exc}"

        print(f"[PIPELINE] result keys={list(result.keys())}")
        if "error" in result:
            print(f"[PIPELINE] pipeline error: {result['error']}")
            return f"❌ Prediction failed: {result['error']}"

        print(f"[PIPELINE] prediction={result['prediction']}  "
              f"P(active)={result['probability_active']:.4f}")

        context = format_interpretation_context(result)
        print(f"[PIPELINE] context length={len(context)} chars")

        # Populate right-panel structures: query mol + top SHAP substructures
        structures = [{
            "smiles": smiles,
            "label": f"Query · {result['prediction']}",
            "sublabel": f"P(active) = {result['probability_active']:.4f}",
            "type": "active" if result["prediction"] == "Active" else "inactive",
        }]
        for bit_info in result.get("top_bits", []):
            direction = "→ Active" if bit_info["shap_value"] > 0 else "→ Inactive"
            shap_str = f"SHAP={bit_info['shap_value']:+.4f}"
            if bit_info["bit_on"] == 1:
                mol_subs = bit_info.get("molecule_substructures") or []
                sub_smiles = mol_subs[0].get("smiles") if mol_subs else None
                if not sub_smiles:
                    db = bit_info.get("training_info")
                    sub_smiles = db.get("dominant_substructure") if db else None
                if sub_smiles:
                    card_type = "active" if bit_info["shap_value"] > 0 else "inactive"
                    structures.append({
                        "smiles": sub_smiles,
                        "label": f"{bit_info['bit']}  {shap_str}",
                        "sublabel": direction,
                        "type": card_type,
                    })
            else:
                db = bit_info.get("training_info")
                if db and db.get("dominant_substructure"):
                    structures.append({
                        "smiles": db["dominant_substructure"],
                        "label": f"{bit_info['bit']} (ABSENT)  {shap_str}",
                        "sublabel": f"{direction} · act={db['active_ratio']:.0%}",
                        "type": "absent",
                    })
        st.session_state["current_structures"] = structures[:12]
        self._pending_visuals = {
            "prediction": {
                "label": result["prediction"],
                "p_active": result["probability_active"],
                "p_inactive": result["probability_inactive"],
            },
        }

        # LLM path — grounded prompt prevents hallucination
        if self.chat_handler is not None:
            user_prompt = PromptTemplates.format_molecule_prediction_prompt(
                context=context,
                user_query=original_query,
            )
            print(f"[LLM] sending grounded prompt ({len(user_prompt)} chars) "
                  f"with MOLECULE_PREDICTION_SYSTEM_PROMPT")
            try:
                response = self.chat_handler.simple_query(
                    user_prompt,
                    system_override=PromptTemplates.MOLECULE_PREDICTION_SYSTEM_PROMPT,
                )
                print(f"[LLM] response received ({len(response)} chars)")
                return response
            except Exception as _exc:
                print(f"[LLM] simple_query failed: {_exc}")
                import traceback
                traceback.print_exc()
                # fall through to static

        # Static fallback — show the raw context as a well-formatted markdown block
        pred = result["prediction"]
        prob = result["probability_active"]
        conf_icon = "🟢" if pred == "Active" else "🔴"
        return (
            f"## Prediction: {conf_icon} {pred}\n\n"
            f"**P(active) = {prob:.4f}** · "
            f"P(inactive) = {result['probability_inactive']:.4f}\n\n"
            f"**Model baseline:** {result['expected_value']:.4f}\n\n"
            f"```\n{context}\n```\n\n"
            f"> Configure an LLM API key for a full natural-language interpretation."
        )

    def _explain_ecfp_bit(self, bit_index: int, original_query: str) -> str:
        """Answer any query about a specific ECFP bit, grounded in the bit database.

        This handles plain queries like "What does ECFP6_1220 represent?" or
        "Is bit 512 ambiguous?" — i.e., when no SHAP value is present.
        The LLM is forced to use ONLY the training-set data, not prior knowledge.
        """
        from core.bit_database import get_bit_context

        bit_db = st.session_state.get("bit_database")
        meta = st.session_state.get("bit_database_meta", {})

        bit_context = get_bit_context(bit_index, bit_db) if bit_db else (
            f"No training dataset loaded. Cannot retrieve data for ECFP6_{bit_index}."
        )

        # Populate right-panel structures: all substructures mapping to this bit
        if bit_db and bit_index in bit_db:
            entry = bit_db[bit_index]
            subs_dict = entry.get("substructures", {})
            total_sub_counts = max(sum(subs_dict.values()), 1)
            structures = []
            for sub_smi, count in list(subs_dict.items())[:10]:
                pct = count / total_sub_counts * 100
                structures.append({
                    "smiles": sub_smi,
                    "label": f"ECFP6_{bit_index}",
                    "sublabel": f"n={count} ({pct:.0f}%) · act={entry['active_ratio']:.0%}",
                    "type": "neutral",
                })
            if structures:
                st.session_state["current_structures"] = structures
                print(f"[STRUCTURES] Populated {len(structures)} structures for bit {bit_index}")

        # LLM path: use the grounded system prompt to prevent hallucination
        if self.chat_handler is not None:
            prompt = PromptTemplates.format_ecfp_bit_query_prompt(
                bit_context=bit_context,
                user_query=original_query,
            )
            try:
                # Override system prompt temporarily with the grounded one
                response = self.chat_handler.simple_query(
                    prompt,
                    system_override=PromptTemplates.ECFP_BIT_GROUNDED_SYSTEM_PROMPT,
                )
                return response
            except TypeError:
                # simple_query may not support system_override yet — fall back
                # to prepending the system prompt in the user message
                prompt_with_sys = (
                    PromptTemplates.ECFP_BIT_GROUNDED_SYSTEM_PROMPT
                    + "\n\n"
                    + prompt
                )
                try:
                    return self.chat_handler.simple_query(prompt_with_sys)
                except Exception:
                    pass

        # Static fallback: return the raw bit context formatted as markdown
        if bit_db and bit_index in bit_db:
            entry = bit_db[bit_index]
            n_sub = entry["n_unique_substructures"]
            dom = entry["dominance"]
            conf = (
                "✅ NONE (unambiguous)" if n_sub == 1 else
                f"⚠️ LOW ({dom:.0f}% dominant)" if dom > 80 else
                f"⚠️ MODERATE ({dom:.0f}% dominant)" if dom > 50 else
                f"🔴 HIGH (top substructure only {dom:.0f}%)"
            )
            lines = [
                f"## ECFP6 Bit {bit_index}\n",
                f"**From training set ({meta.get('n_molecules', '?')} molecules):**\n",
                f"```\n{bit_context}\n```\n",
                f"**Ambiguity:** {conf}\n",
                f"**Active ratio:** {entry['active_ratio']:.0%} of molecules with "
                f"this bit ON are active (label=1)\n",
            ]
            if n_sub > 1:
                lines.append(
                    "\n> ⚠️ This bit has hash collisions. Any SHAP value assigned "
                    "to it is a **mixed signal** from multiple substructures."
                )
            return "".join(lines)

        return (
            f"## ECFP6 Bit {bit_index}\n\n"
            f"{bit_context}\n\n"
            f"> Upload a training CSV in the sidebar to get data-driven analysis for this bit.\n"
            f"> Configure an LLM API key for a natural-language interpretation."
        )

    def _explain_ecfp_bit_shap(self, bit_index: int, value_str: str) -> str:
        """Explain a SHAP value for an ECFP bit with collision-aware context."""
        try:
            shap_val = float(value_str)
        except ValueError:
            shap_val = 0.0

        bit_db = st.session_state.get("bit_database")
        meta = st.session_state.get("bit_database_meta", {})

        # No database or bit not in database → graceful fallback
        if bit_db is None or bit_index not in bit_db:
            fallback = self._explain_shap_value(f"ECFP6 bit {bit_index}", value_str)
            if bit_db is None:
                fallback += (
                    "\n\n---\n> 💡 **Tip:** Upload a training CSV in the sidebar to get "
                    "collision-aware interpretation showing which substructure(s) actually "
                    "activate this bit."
                )
            else:
                fallback += (
                    f"\n\n---\n> Bit {bit_index} was not active in any training molecule "
                    "of the loaded dataset."
                )
            return fallback

        db_entry = bit_db[bit_index]
        n_molecules = meta.get("n_molecules", "?")
        radius = meta.get("radius", 3)
        n_bits = meta.get("n_bits", 2048)

        # Per-molecule bit info for current SMILES
        current_smiles = st.session_state.get("current_smiles", "")
        mol_bits = None
        if current_smiles and MoleculeParser.validate(current_smiles)[0]:
            from core.bit_database import get_molecule_bit_info
            mol_bits = get_molecule_bit_info(current_smiles, radius=radius, n_bits=n_bits)

        from core.bit_database import format_bit_context_for_llm
        collision_context = format_bit_context_for_llm(
            bit_index, shap_val, db_entry, mol_bits
        )

        # LLM path
        if self.chat_handler is not None:
            prompt = PromptTemplates.format_ecfp_bit_shap_prompt(
                bit_index=bit_index,
                shap_value=shap_val,
                n_molecules=n_molecules if isinstance(n_molecules, int) else 0,
                collision_context=collision_context,
            )
            try:
                return self.chat_handler.simple_query(prompt)
            except Exception:
                pass  # fall through to static response

        # Static fallback with full collision context
        conf_icon = "✅" if not db_entry["is_ambiguous"] else (
            "⚠️" if db_entry["dominance"] >= 50 else "🔴"
        )
        direction = "positive ↑" if shap_val > 0 else "negative ↓" if shap_val < 0 else "neutral"
        return (
            f"## ECFP6 Bit {bit_index} — SHAP {shap_val:+.4f}\n\n"
            f"**Direction:** {direction}\n\n"
            f"**Training set prevalence:** "
            f"{db_entry['total_activations']} molecules with this bit ON "
            f"({db_entry['active_ratio']:.0%} active)\n\n"
            f"**Collision status:** {conf_icon} "
            f"{db_entry['n_unique_substructures']} distinct substructure(s) map to this bit\n\n"
            f"```\n{collision_context}\n```\n\n"
            f"> Configure an LLM API key for a full natural-language interpretation."
        )

    def _explain_shap_value(self, descriptor: str, value_str: str) -> str:
        """Explain what a SHAP value means for a given descriptor."""
        try:
            shap_val = float(value_str)
        except ValueError:
            shap_val = None

        if self.chat_handler is not None:
            direction = (
                "positive" if (shap_val is not None and shap_val > 0)
                else "negative" if (shap_val is not None and shap_val < 0)
                else "neutral"
            )
            prompt = (
                f'Explain clearly and in detail what it means that the molecular descriptor '
                f'"{descriptor}" has a SHAP value of {value_str} in a predictive model '
                f'(e.g. QSAR or drug-likeness classification).\n\n'
                f'The SHAP value is {direction}. '
                f'SHAP (SHapley Additive exPlanations) measures each feature\'s contribution to the '
                f'model prediction: positive = pushes toward positive class, negative = toward negative '
                f'class, magnitude = strength of the contribution.\n\n'
                f'Please explain:\n'
                f'1. What the descriptor "{descriptor}" measures\n'
                f'2. What a SHAP value of {value_str} means for this descriptor\n'
                f'3. How to interpret this in the context of drug discovery or QSAR\n'
                f'4. Any practical implications'
            )
            try:
                return self.chat_handler.simple_query(prompt)
            except Exception:
                pass

        # Static fallback
        if shap_val is not None:
            if shap_val > 0:
                direction_text = (
                    f"A **positive** SHAP value ({value_str}) means that **{descriptor}** "
                    f"**increases** the model's prediction for this molecule."
                )
            elif shap_val < 0:
                direction_text = (
                    f"A **negative** SHAP value ({value_str}) means that **{descriptor}** "
                    f"**decreases** the model's prediction for this molecule."
                )
            else:
                direction_text = (
                    f"A **neutral** SHAP value (0) means that **{descriptor}** "
                    f"has no significant influence on the model's prediction."
                )
        else:
            direction_text = f"SHAP value for **{descriptor}**: {value_str}"

        return (
            f"## SHAP Interpretation: {descriptor}\n\n"
            f"**SHAP value:** {value_str}\n\n"
            f"{direction_text}\n\n"
            f"### What is a SHAP value?\n"
            f"SHAP (SHapley Additive exPlanations) measures each feature's (descriptor's) contribution "
            f"to the model prediction for a specific molecule.\n\n"
            f"- **SHAP > 0**: pushes prediction toward the positive class\n"
            f"- **SHAP < 0**: pushes prediction toward the negative class\n"
            f"- **|SHAP| large**: strong impact on the prediction\n"
            f"- **|SHAP| ≈ 0**: descriptor has little effect for this molecule\n\n"
            f"> 💡 For more detail: go to the **📖 SHAP** tab or ask: *\"explain {descriptor}\"*"
        )

    # ── Helper: common session-state params ──────────────────────────────
    def _get_pipeline_params(self) -> dict:
        """Return model, explainer, bit_db, radius, n_bits from session state."""
        meta = st.session_state.get("bit_database_meta", {})
        radius = meta.get("radius") or st.session_state.get("fp_radius", 3)
        n_bits = meta.get("n_bits") or st.session_state.get("fp_nbits", 2048)
        return {
            "model": st.session_state.get("rf_model"),
            "explainer": st.session_state.get("shap_explainer"),
            "bit_db": st.session_state.get("bit_database") or {},
            "radius": radius,
            "n_bits": n_bits,
        }

    def _llm_query(self, system: str, user: str) -> Optional[str]:
        """Send a grounded prompt to the LLM; return None if unavailable.

        The system string is passed as the actual system message (not prepended
        to the user message), so the LLM uses the grounded system prompt and not
        the default code-generation one.
        """
        if self.chat_handler is None:
            return None
        try:
            return self.chat_handler.simple_query(user, system_override=system)
        except Exception:
            return None

    # ── Handler methods for the 6 new query categories ───────────────────

    def _identical_molecules_response(self, canonical_smiles: str) -> str:
        """Deterministic response when both molecules are structurally identical."""
        pred_line = ""
        model = st.session_state.get("rf_model")
        explainer = st.session_state.get("shap_explainer")
        if model is not None and explainer is not None:
            from core.model_pipeline import predict_and_interpret
            p = self._get_pipeline_params()
            result = predict_and_interpret(
                canonical_smiles, p["model"], p["explainer"], p["bit_db"],
                radius=p["radius"], n_bits=p["n_bits"], top_n=0,
            )
            if "error" not in result:
                pred = result["prediction"]
                p_active = result["probability_active"]
                self._pending_visuals = {
                    "prediction": {
                        "label": pred,
                        "p_active": p_active,
                        "p_inactive": result["probability_inactive"],
                    },
                }
                icon = "🟢" if pred == "Active" else "🔴"
                pred_line = (
                    f"\n\n**Prediction:** {icon} {pred} "
                    f"(P(active) = {p_active:.4f})"
                )
        return (
            f"The two molecules are structurally identical "
            f"(canonical SMILES: `{canonical_smiles}`).\n\n"
            f"**Tanimoto = 1.000 · ΔP(active) = 0.0000**\n\n"
            f"No differential fingerprint or SHAP analysis to run."
            f"{pred_line}"
        )

    def _compare_molecules(self, smiles1: str, smiles2: str, prompt: str) -> str:
        """Compare two molecules via fingerprint diff + SHAP diff."""
        from core.comparison_pipeline import compare_molecules, format_comparison_context

        p = self._get_pipeline_params()
        result = compare_molecules(
            smiles1, smiles2,
            p["model"], p["explainer"], p["bit_db"],
            radius=p["radius"], n_bits=p["n_bits"],
        )
        if "error" in result:
            return f"❌ Comparison failed: {result['error']}"

        if result.get("identical"):
            return self._identical_molecules_response(result["canonical_smiles"])

        # Populate right-panel structures: both molecules + differentiating bits
        structures = [
            {
                "smiles": smiles1,
                "label": f"Mol A · {result['mol1']['prediction']}",
                "sublabel": f"P(active) = {result['mol1']['probability_active']:.4f}",
                "type": "active" if result["mol1"]["prediction"] == "Active" else "inactive",
            },
            {
                "smiles": smiles2,
                "label": f"Mol B · {result['mol2']['prediction']}",
                "sublabel": f"P(active) = {result['mol2']['probability_active']:.4f}",
                "type": "active" if result["mol2"]["prediction"] == "Active" else "inactive",
            },
        ]
        for diff in result.get("top_differentiating_bits", [])[:8]:
            mol_subs = diff.get("mol_subs") or []
            sub_smiles = mol_subs[0].get("smiles") if mol_subs else None
            if not sub_smiles:
                db = diff.get("db")
                sub_smiles = db.get("dominant_substructure") if db else None
            if sub_smiles:
                bit_name = diff["bit"]
                shap_diff = diff["shap_mol1"] - diff["shap_mol2"]
                in_which = "Only in A" if diff.get("in_mol1") and not diff.get("in_mol2") else \
                           "Only in B" if diff.get("in_mol2") and not diff.get("in_mol1") else "Both"
                structures.append({
                    "smiles": sub_smiles,
                    "label": f"{bit_name} — {in_which}",
                    "sublabel": f"ΔSHAP = {shap_diff:+.4f}",
                    "type": "active" if shap_diff > 0 else "inactive",
                })
        st.session_state["current_structures"] = structures
        self._pending_visuals = {
            "comparison": {
                "p1": result["mol1"]["probability_active"],
                "p2": result["mol2"]["probability_active"],
                "tanimoto": result["tanimoto"],
            }
        }

        context = format_comparison_context(result)
        system = (
            "You are a molecular comparison assistant inside RAGMODEX.\n"
            "Rules: use ONLY the provided data; ECFP6 = diameter 6 = radius 3; "
            "never generate code; respond in the user's language; maximum 180 words.\n"
            "Structure: one sentence on ΔP(active) and Tanimoto, then the top 3 differentiating "
            "bits by |SHAP diff| — one sentence each naming substructure and activity impact. "
            "No repetitive template. No filler phrases."
        )
        user = (
            f"--- COMPARISON DATA ---\n{context}\n\n"
            f"--- USER QUERY ---\n{prompt}\n\n"
            "ΔP summary + top-3 differentiating bits (1 sentence each). Max 180 words."
        )
        llm_response = self._llm_query(system, user)
        if llm_response:
            return llm_response

        # Static fallback
        mol1 = result["mol1"]
        mol2 = result["mol2"]
        delta = result["delta_probability"]
        icon = "⬆️" if delta > 0 else "⬇️" if delta < 0 else "➡️"
        return (
            f"## Molecule Comparison\n\n"
            f"**Mol 1:** `{mol1['canonical_smiles']}` → "
            f"{mol1['prediction']} (P={mol1['probability_active']:.3f})\n\n"
            f"**Mol 2:** `{mol2['canonical_smiles']}` → "
            f"{mol2['prediction']} (P={mol2['probability_active']:.3f})\n\n"
            f"**{icon} Delta P(active):** {delta:+.4f} · "
            f"Tanimoto: {result['tanimoto']:.3f}\n\n"
            f"```\n{context}\n```\n\n"
            "> Configure an LLM API key for a natural-language interpretation."
        )

    def _check_applicability_domain(self, smiles: str, prompt: str) -> str:
        """Check whether a molecule falls within the training AD."""
        ad_tuple = st.session_state.get("ad_model")
        if ad_tuple is None:
            return (
                "⚠️ No applicability domain model available. "
                "Upload a training CSV in the sidebar and build the bit database first "
                "(the AD model is built automatically alongside it)."
            )

        from core.applicability_domain import check_applicability_domain, format_ad_context

        p = self._get_pipeline_params()
        result = check_applicability_domain(
            smiles, ad_tuple,
            p["model"], p["explainer"], p["bit_db"],
            radius=p["radius"], n_bits=p["n_bits"],
        )
        if "error" in result:
            return f"❌ AD check failed: {result['error']}"

        # Show query molecule in right panel
        st.session_state["current_structures"] = [{
            "smiles": smiles,
            "label": "Query Molecule",
            "sublabel": f"{'INSIDE' if result['inside_ad'] else 'OUTSIDE'} AD · "
                        f"distance={result['mean_knn_distance']:.3f}",
            "type": "active" if result["inside_ad"] else "inactive",
        }]
        self._pending_visuals = {
            "ad_result": {
                "inside_ad": result["inside_ad"],
                "distance": result["mean_knn_distance"],
                "threshold": result["ad_threshold"],
            },
        }

        context = format_ad_context(result)
        system = (
            "You are an applicability domain assessment assistant inside RAGMODEX.\n"
            "Rules: use ONLY the provided kNN distance data; never generate code; "
            "respond in the user's language; maximum 150 words.\n"
            "Structure: one sentence on INSIDE/OUTSIDE status with distance vs threshold, "
            "one sentence on prediction reliability, one sentence on recommended action."
        )
        user = (
            f"--- AD DATA ---\n{context}\n\n"
            f"--- USER QUERY ---\n{prompt}\n\n"
            "3 sentences: status, reliability, recommended action. Max 150 words."
        )
        llm_response = self._llm_query(system, user)
        if llm_response:
            return llm_response

        # Static fallback
        inside = result["inside_ad"]
        conf = result["ad_confidence"]
        icon = "✅" if inside else "⚠️"
        pred = result.get("prediction", {})
        p_active = pred.get("probability_active", None)
        return (
            f"## Applicability Domain Assessment\n\n"
            f"**{icon} Status:** {'INSIDE' if inside else 'OUTSIDE'} AD · "
            f"Confidence: {conf}\n\n"
            f"**kNN distance:** {result['mean_knn_distance']:.4f} "
            f"(threshold: {result['ad_threshold']:.4f})\n\n"
            + (f"**Prediction:** {pred.get('prediction', '?')} "
               f"(P(active) = {p_active:.4f})\n\n" if p_active is not None else "")
            + f"```\n{context}\n```\n\n"
            + ("> ⚠️ Prediction outside training chemical space — treat with caution."
               if not inside else
               "> Prediction is within training chemical space.")
        )

    def _apply_mol_edit(self, smiles: str, prompt: str) -> str:
        """Apply a rule-based molecular edit and compare before/after predictions."""
        from core.molecular_editor import apply_edit_rdkit, format_edit_context
        from core.model_pipeline import predict_and_interpret
        from core.comparison_pipeline import compare_molecules

        modified_smiles = apply_edit_rdkit(smiles, prompt)
        if modified_smiles is None:
            return (
                "⚠️ Could not apply the requested edit automatically.\n\n"
                "Supported edits include: replace Cl with F, remove nitro group, "
                "add methyl, dehalogenation, O↔S swaps, and similar simple substitutions.\n\n"
                "Please describe the modification more specifically, e.g.: "
                "*\"replace Cl with F\"*, *\"remove nitro group\"*, *\"add methyl\"*."
            )

        p = self._get_pipeline_params()

        original_result = predict_and_interpret(
            smiles, p["model"], p["explainer"], p["bit_db"],
            radius=p["radius"], n_bits=p["n_bits"], top_n=5,
        )
        modified_result = predict_and_interpret(
            modified_smiles, p["model"], p["explainer"], p["bit_db"],
            radius=p["radius"], n_bits=p["n_bits"], top_n=5,
        )

        if "error" in original_result:
            return f"❌ Original molecule pipeline failed: {original_result['error']}"
        if "error" in modified_result:
            return f"❌ Modified molecule pipeline failed: {modified_result['error']}"

        comparison = compare_molecules(
            smiles, modified_smiles,
            p["model"], p["explainer"], p["bit_db"],
            radius=p["radius"], n_bits=p["n_bits"],
        )
        if "error" in comparison:
            return f"❌ Comparison failed: {comparison['error']}"

        # Populate right-panel structures: original, modified + changed bits
        structures = [
            {
                "smiles": smiles,
                "label": f"Original · {original_result['prediction']}",
                "sublabel": f"P(active) = {original_result['probability_active']:.4f}",
                "type": "inactive",
            },
            {
                "smiles": modified_smiles,
                "label": f"Modified · {modified_result['prediction']}",
                "sublabel": f"P(active) = {modified_result['probability_active']:.4f}",
                "type": "active" if modified_result["probability_active"] > original_result["probability_active"] else "inactive",
            },
        ]
        for diff in comparison.get("top_differentiating_bits", [])[:6]:
            mol_subs = diff.get("mol_subs") or []
            sub_smiles = mol_subs[0].get("smiles") if mol_subs else None
            if not sub_smiles:
                db = diff.get("db")
                sub_smiles = db.get("dominant_substructure") if db else None
            if sub_smiles:
                bit_name = diff["bit"]
                if diff.get("in_mol1") and not diff.get("in_mol2"):
                    structures.append({
                        "smiles": sub_smiles,
                        "label": f"{bit_name} (LOST)",
                        "sublabel": f"SHAP was {diff['shap_mol1']:+.4f}",
                        "type": "inactive",
                    })
                elif diff.get("in_mol2") and not diff.get("in_mol1"):
                    structures.append({
                        "smiles": sub_smiles,
                        "label": f"{bit_name} (GAINED)",
                        "sublabel": f"SHAP now {diff['shap_mol2']:+.4f}",
                        "type": "active",
                    })
        st.session_state["current_structures"] = structures
        self._pending_visuals = {
            "edit_result": {
                "p_orig": original_result["probability_active"],
                "p_mod": modified_result["probability_active"],
            }
        }

        context = format_edit_context(original_result, modified_result, comparison)
        delta = comparison["delta_probability"]
        system = (
            "You are a what-if molecular editor assistant inside RAGMODEX.\n"
            "Rules: use ONLY the provided data; ECFP6 = diameter 6 = radius 3; "
            "never generate code; respond in the user's language; maximum 180 words.\n"
            "Structure: one sentence on what changed structurally, one on ΔP(active) and direction, "
            "then top-2 bits gained/lost with their SHAP impact (1 sentence each). No filler."
        )
        user = (
            f"--- EDIT DATA ---\n{context}\n\n"
            f"--- USER QUERY ---\n{prompt}\n\n"
            "Structural change + ΔP + top-2 bit changes. Max 180 words."
        )
        llm_response = self._llm_query(system, user)
        if llm_response:
            return llm_response

        icon = "⬆️" if delta > 0.01 else "⬇️" if delta < -0.01 else "➡️"
        return (
            f"## What-If Analysis\n\n"
            f"**Original:** `{original_result['canonical_smiles']}` → "
            f"{original_result['prediction']} (P={original_result['probability_active']:.3f})\n\n"
            f"**Modified:** `{modified_result['canonical_smiles']}` → "
            f"{modified_result['prediction']} (P={modified_result['probability_active']:.3f})\n\n"
            f"**{icon} Delta P(active):** {delta:+.4f}\n\n"
            f"```\n{context}\n```\n\n"
            "> Configure an LLM API key for a natural-language interpretation."
        )

    def _run_design_suggestions(self, smiles: str, prompt: str) -> str:
        """Run the BRICS-based design pipeline and return a formatted response."""
        from core.design_engine import run_design_pipeline, format_design_context

        p = self._get_pipeline_params()
        n_variants = st.session_state.get("design_n_variants", 200)

        with st.spinner(f"Generating {n_variants} variants…"):
            result = run_design_pipeline(
                smiles=smiles,
                model=p["model"],
                radius=p["radius"],
                n_bits=p["n_bits"],
                n_variants=n_variants,
                top_k=10,
            )

        if "error" in result:
            return f"❌ Design engine error: {result['error']}"

        context = format_design_context(result, top_n=8)

        # Cache for the panel as well
        st.session_state["_design_cache"] = {"smiles": smiles, "result": result}

        system = (
            "You are a molecular design assistant inside RAGMODEX.\n"
            "Rules: use ONLY the provided variant data; never invent candidates; "
            "never generate code; respond in the user's language; maximum 180 words.\n"
            "Structure: best candidate with ΔP and transformation type, then 1-sentence "
            "summary of the trend across the top variants. No bullet list for every variant."
        )
        user = (
            f"--- DESIGN OUTPUT ---\n{context}\n\n"
            f"--- USER QUERY ---\n{prompt}\n\n"
            "Best candidate + transformation type + trend summary. Max 180 words."
        )
        llm_response = self._llm_query(system, user)
        if llm_response:
            return llm_response

        # Static fallback when no LLM is available
        improvers = result.get("top_improvers", [])
        n_better = len(improvers)
        best = improvers[0] if improvers else None
        lines = [
            f"## 🧪 Design Suggestions for `{result['base_smiles']}`",
            f"",
            f"**Base P(active):** {result['base_prob']:.4f}",
            f"**Variants generated:** {result['n_generated']}",
            f"**With improvement (ΔP > 0):** {n_better}",
            f"",
        ]
        if best:
            lines += [
                f"**Best candidate:** `{best.smiles}`",
                f"P(active) = {best.probability:.4f}  ·  Δ = {best.delta:+.4f}",
                f"Transformation: {best.transformation}",
                f"",
            ]
        lines.append("```")
        lines.append(context)
        lines.append("```")
        lines.append("")
        lines.append(
            "> Open the **🧪 Design** page in the sidebar for an interactive visual view."
        )
        return "\n".join(lines)

    def _suggest_modifications(self, smiles: str, prompt: str) -> str:
        """Suggest SHAP-guided structural modifications to improve predicted activity."""
        from core.suggestion_pipeline import suggest_modifications, format_suggestions_context

        p = self._get_pipeline_params()
        aggregate_stats = st.session_state.get("aggregate_stats")

        result = suggest_modifications(
            smiles, p["model"], p["explainer"], p["bit_db"],
            aggregate_stats=aggregate_stats,
            radius=p["radius"], n_bits=p["n_bits"],
        )
        if "error" in result:
            return f"❌ Suggestion pipeline failed: {result['error']}"

        context = format_suggestions_context(result)
        system = (
            "You are a structural optimization assistant inside RAGMODEX.\n"
            "Rules: use ONLY the SHAP-based suggestion data; never generate code; "
            "respond in the user's language; maximum 180 words.\n"
            "Give 2-3 prioritized actionable recommendations, each in 1-2 sentences: "
            "what to change and why (SHAP evidence). No filler. No repetitive template."
        )
        user = (
            f"--- SUGGESTION DATA ---\n{context}\n\n"
            f"--- USER QUERY ---\n{prompt}\n\n"
            "2-3 prioritized recommendations (1-2 sentences each). Max 180 words."
        )
        llm_response = self._llm_query(system, user)
        if llm_response:
            return llm_response

        # Static fallback
        pred = result.get("prediction", {})
        p_active = pred.get("probability_active", None)
        n_remove = len(result.get("remove", []))
        n_add = len(result.get("add", []))
        n_keep = len(result.get("keep", []))
        return (
            f"## Structural Modification Suggestions\n\n"
            f"**Molecule:** `{pred.get('canonical_smiles', smiles)}`\n"
            + (f"**P(active):** {p_active:.4f}\n\n" if p_active is not None else "\n")
            + f"**Recommendations:** {n_remove} to remove · {n_add} to add · {n_keep} to keep\n\n"
            f"```\n{context}\n```\n\n"
            "> Configure an LLM API key for a natural-language interpretation."
        )

    def _search_substructure_activity(self, prompt: str) -> str:
        """Search bit database for substructures matching a query term."""
        from core.suggestion_pipeline import (
            search_substructure_activity,
            format_substructure_context,
        )

        bit_db = st.session_state.get("bit_database") or {}
        result = search_substructure_activity(prompt, bit_db)

        if not result.get("matches"):
            query_term = result.get("query", result.get("query_term", prompt))
            return (
                f"No substructure matches found for **\"{query_term}\"** in the training dataset.\n\n"
                "Try a more general term (e.g., *chloro*, *piperazine*, *carbonyl*, *phenyl*)."
            )

        # Populate right-panel structures: top matching substructures
        structures = []
        for match in result.get("matches", [])[:10]:
            sub_smi = match.get("substructure")
            if sub_smi:
                structures.append({
                    "smiles": sub_smi,
                    "label": f"ECFP6_{match['bit']}",
                    "sublabel": f"act={match['active_ratio']:.0%} · n={match.get('total', '?')}",
                    "type": "active" if match["active_ratio"] > 0.5 else "inactive",
                })
        if structures:
            st.session_state["current_structures"] = structures

        context = format_substructure_context(result)
        system = (
            "You are a substructure activity interpreter inside RAGMODEX.\n"
            "Rules: use ONLY the provided active_ratio and count data; never generate code; "
            "respond in the user's language; maximum 150 words.\n"
            "Name the top-2 most active and top-1 most inactive substructure matches "
            "with their active_ratio. One sentence on the design implication."
        )
        user = (
            f"--- SUBSTRUCTURE DATA ---\n{context}\n\n"
            f"--- USER QUERY ---\n{prompt}\n\n"
            "Top active/inactive hits + 1-sentence design implication. Max 150 words."
        )
        llm_response = self._llm_query(system, user)
        if llm_response:
            return llm_response

        # Static fallback
        n_matches = len(result.get("matches", []))
        query_term = result.get("query", result.get("query_term", "?"))
        top_match = result["matches"][0] if result["matches"] else {}
        return (
            f"## Substructure Activity Search: \"{query_term}\"\n\n"
            f"**{n_matches} bit(s) matched** in the training dataset.\n\n"
            + (f"**Top match:** `{top_match.get('substructure', '?')}` — "
               f"active ratio: {top_match.get('active_ratio', 0):.0%}\n\n"
               if top_match else "")
            + f"```\n{context}\n```\n\n"
            "> Configure an LLM API key for a natural-language interpretation."
        )

    def _answer_aggregate_query(self, prompt: str) -> str:
        """Answer a dataset-level aggregate statistics query."""
        from core.aggregate_stats import select_aggregate_context

        aggregate_stats = st.session_state.get("aggregate_stats")
        if aggregate_stats is None:
            return (
                "⚠️ No aggregate statistics available. "
                "Upload a training CSV in the sidebar and build the bit database first."
            )

        context = select_aggregate_context(prompt, aggregate_stats)
        system = (
            "You are a dataset statistics interpreter inside RAGMODEX.\n"
            "Rules: use ONLY the provided aggregate statistics; never generate code; "
            "respond in the user's language; maximum 150 words.\n"
            "Direct answer with exact numbers from the data, one sentence on the main pattern, "
            "one sentence on its QSAR implication."
        )
        user = (
            f"--- AGGREGATE STATS ---\n{context}\n\n"
            f"--- USER QUERY ---\n{prompt}\n\n"
            "Direct answer with numbers + main pattern + QSAR implication. Max 150 words."
        )
        llm_response = self._llm_query(system, user)
        if llm_response:
            return llm_response

        return (
            f"## Dataset Aggregate Statistics\n\n"
            f"```\n{context}\n```\n\n"
            "> Configure an LLM API key for a natural-language interpretation."
        )

    def _generate_response(self, prompt: str) -> str:
        """Generate LLM response with optional molecule context."""
        if self.chat_handler is None:
            return "⚠️ LLM not configured. Please add an API key in the settings."

        # Scope guard: if no chemistry/RAGMODEX keyword is present, the query is
        # almost certainly off-topic. Return a deterministic redirect — no LLM call.
        if not _SCOPE_KEYWORDS.search(prompt):
            return _OUT_OF_SCOPE_IT if _ITALIAN_WORDS.search(prompt) else _OUT_OF_SCOPE_EN

        try:
            current_smiles = st.session_state.get("current_smiles", "")
            enriched_prompt = prompt
            if current_smiles and MoleculeParser.validate(current_smiles)[0]:
                mol_info = MoleculeParser.get_info(current_smiles)
                mol_context = (
                    f"\n\n[Currently loaded molecule: SMILES={mol_info.canonical_smiles}, "
                    f"Formula={mol_info.molecular_formula}, MW={mol_info.molecular_weight:.2f} Da]"
                )
                enriched_prompt = prompt + mol_context

            if self.retriever and not self.retriever.is_empty():
                context = self.retriever.format_context(prompt)
                if context:
                    return self.chat_handler.query_with_context(enriched_prompt, context)

            return self.chat_handler.chat(enriched_prompt)
        except Exception as e:
            return f"❌ Error generating response: {str(e)}"

    def clear_history(self):
        st.session_state.messages = []
        if self.chat_handler:
            self.chat_handler.clear_history()
