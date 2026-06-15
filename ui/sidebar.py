"""Sidebar UI component."""

import base64
import streamlit as st
from pathlib import Path
from typing import Optional

from config.api_config import APIConfig
from llm.client_factory import LLMClientFactory


class Sidebar:
    """Sidebar component for app settings and controls."""

    def __init__(self):
        """Initialize sidebar state."""
        self._init_session_state()

    def _init_session_state(self):
        """Initialize session state for sidebar."""
        if "llm_provider" not in st.session_state:
            st.session_state.llm_provider = "groq"
        if "llm_model" not in st.session_state:
            st.session_state.llm_model = "llama-3.3-70b-versatile"
        if "temperature" not in st.session_state:
            st.session_state.temperature = 0.7
        if "current_smiles" not in st.session_state:
            st.session_state.current_smiles = ""
        if "fp_radius" not in st.session_state:
            st.session_state.fp_radius = 3
        if "fp_nbits" not in st.session_state:
            st.session_state.fp_nbits = 2048
        if "fp_use_features" not in st.session_state:
            st.session_state.fp_use_features = False
        if "bit_database" not in st.session_state:
            st.session_state.bit_database = None
        if "bit_database_meta" not in st.session_state:
            st.session_state.bit_database_meta = {}
        if "rf_model" not in st.session_state:
            st.session_state.rf_model = None
        if "shap_explainer" not in st.session_state:
            st.session_state.shap_explainer = None
        if "model_meta" not in st.session_state:
            st.session_state.model_meta = {}
        # Derived caches (built from training data)
        if "aggregate_stats" not in st.session_state:
            st.session_state.aggregate_stats = None
        if "ad_model" not in st.session_state:
            st.session_state.ad_model = None      # tuple: (knn, threshold, mean, std)
        if "X_train" not in st.session_state:
            st.session_state.X_train = None       # np.ndarray (n_mols × n_bits)
        # Design engine
        if "design_n_variants" not in st.session_state:
            st.session_state.design_n_variants = 200
        # Test set (evaluation)
        if "test_df" not in st.session_state:
            st.session_state.test_df = None
        if "test_df_meta" not in st.session_state:
            st.session_state.test_df_meta = {}

    def render(self) -> dict:
        """Render the sidebar and return settings."""
        with st.sidebar:
            # LOGO
            _logo_path = Path("assets/logo.png")
            if _logo_path.exists():
                _logo_b64 = base64.b64encode(_logo_path.read_bytes()).decode()
                st.markdown(
                    f"<div style='text-align:center;padding:1rem 0 1.2rem 0;'>"
                    f"<img src='data:image/png;base64,{_logo_b64}' "
                    f"style='max-width:160px;margin-bottom:0.5rem;'/>"
                    f"<div class='app-brand-name'>MolChat</div>"
                    f"<div class='app-brand-subtitle'>Molecular AI Interpreter</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div style='text-align:center;padding:1rem 0 1.2rem 0;'>"
                    "<div style='font-size:2.2rem;'>🧬</div>"
                    "<div class='app-brand-name'>MolChat</div>"
                    "<div class='app-brand-subtitle'>Molecular AI Interpreter</div>"
                    "</div>",
                    unsafe_allow_html=True,
                )


            # ── Navigation ──
            # Core tools always visible; analysis pages appear once prerequisites are loaded.
            _has_model   = st.session_state.get("rf_model") is not None
            _has_data    = st.session_state.get("bit_database") is not None
            _has_test    = st.session_state.get("test_df") is not None

            _nav_items = [
                ":material/chat: Chat",
                ":material/biotech: Visualizer",
                ":material/analytics: Prediction",
                ":material/search: Search",
            ]
            if _has_model:
                _nav_items.append(":material/science: Design")
            if _has_model and _has_test:
                _nav_items.append(":material/assessment: Evaluation")
            if _has_data:
                _nav_items.append(":material/filter_alt: Virtual screening")

            page = st.pills(
                "Navigation",
                _nav_items,
                default=":material/chat: Chat",
                key="nav_pills",
                label_visibility="collapsed",
            )
            _nav_map = {
                ":material/chat: Chat":                     "💬 Chat",
                ":material/biotech: Visualizer":            "🧬 ECFP/MACCS Visualizer",
                ":material/analytics: Prediction":          "🔮 Prediction",
                ":material/search: Search":                 "🔍 Substructure Search",
                ":material/science: Design":                "🧪 Design",
                ":material/assessment: Evaluation":         "📊 Evaluation",
                ":material/filter_alt: Virtual screening":  "🔬 Virtual screening",
            }
            page = _nav_map.get(page or ":material/chat: Chat", "💬 Chat")
            settings = {"page": page}

            st.divider()

            # ── Training Data — first step: data must be loaded before anything else ──
            st.markdown("**:material/table_chart: Training Data**")
            self._render_training_data_upload()

            st.divider()

            # ── Fingerprint Settings — depends on training data ──
            st.markdown("**:material/fingerprint: Fingerprint**")
            fp_settings = self._render_fingerprint_settings()
            settings.update(fp_settings)

            st.divider()

            # ── Prediction Model — depends on fingerprint settings ──
            st.markdown("**:material/model_training: Model**")
            self._render_model_upload()

            st.divider()

            # ── Test Set — optional, requires model ──
            st.markdown("**:material/lab_research: Test Set**")
            self._render_test_set_upload()

            # ── Design Engine — shown only when model is loaded ──
            if st.session_state.get("rf_model") is not None:
                st.divider()
                st.markdown("**:material/science: Design Engine**")
                self._render_design_settings()

            st.divider()

            # ── LLM — set once and forget, lives at the bottom ──
            _cur_provider = st.session_state.get("llm_provider", "groq")
            _cur_model    = st.session_state.get("llm_model", "")
            _llm_label    = f":material/smart_toy: LLM · {_cur_provider}"
            with st.expander(_llm_label, expanded=False):
                llm_settings = self._render_llm_settings()
            settings.update(llm_settings)

            st.divider()

            self._render_quick_actions()

        return settings

    def _render_llm_settings(self) -> dict:
        """Render LLM settings section."""
        available_providers = LLMClientFactory.get_available_providers()
        if not available_providers:
            st.warning(
                "No API keys found. Add a `.env` file with "
                "`GROQ_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY`."
            )
            available_providers = ["groq"]

        provider = st.selectbox(
            "Provider",
            options=available_providers,
            index=available_providers.index(st.session_state.llm_provider)
            if st.session_state.llm_provider in available_providers
            else 0,
            key="provider_select",
        )
        st.session_state.llm_provider = provider

        provider_info = LLMClientFactory.get_provider_info(provider)
        if provider_info:
            models = provider_info.models
            default_model = provider_info.default_model
        else:
            models = ["llama-3.3-70b-versatile"]
            default_model = "llama-3.3-70b-versatile"

        model = st.selectbox(
            "Model",
            options=models,
            index=models.index(default_model) if default_model in models else 0,
            key="model_select",
        )
        st.session_state.llm_model = model

        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=2.0,
            value=st.session_state.temperature,
            step=0.1,
            key="temp_slider",
        )
        st.session_state.temperature = temperature

        return {"provider": provider, "model": model, "temperature": temperature}

    def _render_fingerprint_settings(self) -> dict:
        """Render fingerprint settings section."""
        radius = st.segmented_control(
            "Morgan Radius",
            options=[1, 2, 3, 4],
            default=st.session_state.fp_radius,
            key="radius_select",
        )
        if radius is None:
            radius = st.session_state.fp_radius
        st.session_state.fp_radius = radius

        nbits = st.segmented_control(
            "Bits",
            options=[512, 1024, 2048, 4096],
            default=st.session_state.fp_nbits,
            key="nbits_select",
        )
        if nbits is None:
            nbits = st.session_state.fp_nbits
        st.session_state.fp_nbits = nbits

        use_features = st.checkbox(
            "Use Features (FCFP)",
            value=st.session_state.fp_use_features,
            key="features_check",
        )
        st.session_state.fp_use_features = use_features

        return {"fp_radius": radius, "fp_nbits": nbits, "fp_use_features": use_features}

    def _render_training_data_upload(self):
        """Render training CSV upload for ECFP6 bit collision analysis."""
        # Warn if fingerprint settings changed after building the database
        meta = st.session_state.get("bit_database_meta", {})
        if st.session_state.get("bit_database") is not None:
            if (meta.get("radius") != st.session_state.fp_radius or
                    meta.get("n_bits") != st.session_state.fp_nbits):
                st.warning("Fingerprint settings changed — rebuild the bit database.")
                st.session_state.bit_database = None

        with st.expander("Upload CSV for bit analysis", expanded=False):
            uploaded = st.file_uploader(
                "CSV with SMILES + binary target",
                type=["csv"],
                key="training_csv_uploader",
                help="Required: one SMILES column and one binary target column (0/1).",
            )

            if uploaded is not None:
                import pandas as pd
                import hashlib
                import io

                csv_bytes = uploaded.read()
                csv_hash = hashlib.md5(csv_bytes).hexdigest()

                # Parse only when a new file is detected
                if st.session_state.get("_bit_db_csv_hash") != csv_hash:
                    df = pd.read_csv(io.BytesIO(csv_bytes))
                    st.session_state["_bit_db_pending_df"] = df
                    st.session_state["_bit_db_csv_hash"] = csv_hash
                    st.session_state["bit_database"] = None  # invalidate old DB

                df = st.session_state.get("_bit_db_pending_df")
                if df is not None:
                    cols = list(df.columns)
                    st.caption(f"{len(df)} rows · {len(cols)} columns")

                    smiles_col = st.selectbox(
                        "SMILES column", cols, key="csv_smiles_col"
                    )
                    label_col = st.selectbox(
                        "Target column",
                        cols,
                        index=min(1, len(cols) - 1),
                        key="csv_label_col",
                    )

                    if len(df) > 5000:
                        st.info(f"Large dataset ({len(df)} rows) — building may take a minute.")

                    if st.button("Build bit database", key="build_bit_db_btn", type="primary"):
                        from core.bit_database import build_bit_database
                        radius = st.session_state.fp_radius
                        nbits = st.session_state.fp_nbits
                        prog = st.progress(0.0, text="Computing fingerprints…")
                        db, n_failed = build_bit_database(
                            df, smiles_col, label_col,
                            radius=radius, n_bits=nbits,
                            progress_bar=prog,
                        )
                        prog.empty()
                        st.session_state["bit_database"] = db
                        st.session_state["bit_database_meta"] = {
                            "n_molecules": len(df) - n_failed,
                            "n_failed": n_failed,
                            "radius": radius,
                            "n_bits": nbits,
                            "smiles_col": smiles_col,
                            "label_col": label_col,
                            "n_bits_indexed": len(db),
                        }
                        if n_failed:
                            st.warning(f"{n_failed} rows skipped (invalid SMILES).")
                        st.success(
                            f"Done! {len(db)} bits indexed across "
                            f"{len(df) - n_failed} molecules."
                        )

                        # ── Compute derived caches from training data ──────────
                        # 1. Aggregate statistics (instant — uses only bit_db)
                        try:
                            from core.aggregate_stats import build_aggregate_stats
                            st.session_state["aggregate_stats"] = build_aggregate_stats(db)
                        except Exception as exc:
                            st.warning(f"Aggregate stats failed: {exc}")

                        # 2. Training fingerprint matrix X_train (for AD check)
                        try:
                            import numpy as np
                            from rdkit import Chem
                            from rdkit.Chem import AllChem, DataStructs
                            X_rows = []
                            train_fps = []
                            smiles_train = []
                            y_train = []
                            raw_smiles = df[smiles_col].dropna().tolist()
                            raw_labels = df[label_col].tolist()
                            with st.spinner("Building AD model…"):
                                for smi, lbl in zip(raw_smiles, raw_labels):
                                    mol = Chem.MolFromSmiles(str(smi).strip())
                                    if mol is not None:
                                        fp = AllChem.GetMorganFingerprintAsBitVect(
                                            mol, radius, nBits=nbits
                                        )
                                        arr = np.zeros(nbits, dtype=np.int32)
                                        DataStructs.ConvertToNumpyArray(fp, arr)
                                        X_rows.append(arr)
                                        train_fps.append(fp)
                                        smiles_train.append(str(smi).strip())
                                        try:
                                            y_train.append(int(lbl))
                                        except (ValueError, TypeError):
                                            y_train.append(0)
                            if X_rows:
                                X_train = np.vstack(X_rows)
                                st.session_state["X_train"] = X_train
                                st.session_state["train_fps"] = train_fps
                                st.session_state["smiles_train"] = smiles_train
                                st.session_state["y_train"] = y_train
                                # 3. AD kNN model
                                from core.applicability_domain import build_ad_model
                                st.session_state["ad_model"] = build_ad_model(X_train)
                        except Exception as exc:
                            st.warning(f"AD model failed: {exc}")

                        # ── Persist session to disk ────────────────────────
                        try:
                            from core.session_persistence import save_session
                            save_session(st.session_state)
                        except Exception:
                            pass

        # Status indicator (always visible, outside expander)
        if st.session_state.get("bit_database"):
            meta = st.session_state.get("bit_database_meta", {})
            n_amb = sum(
                1 for e in st.session_state.bit_database.values()
                if e.get("is_ambiguous")
            )
            col_a, col_b = st.columns(2)
            col_a.metric("Molecules", meta.get("n_molecules", "?"))
            col_b.metric("Bits indexed", meta.get("n_bits_indexed", "?"))
            st.caption(
                f":material/check_circle: ECFP{2 * meta.get('radius', 2)} · "
                f"{n_amb} collision bits"
            )
        else:
            st.caption(":material/upload_file: No training data loaded.")

    def _render_model_upload(self):
        """Render model (pickle/joblib) upload and SHAP explainer initialization."""
        with st.expander("Upload model (.pkl / .joblib)", expanded=False):
            uploaded = st.file_uploader(
                "Scikit-learn model file",
                type=["pkl", "pickle", "joblib"],
                key="model_file_uploader",
                help="Upload a fitted scikit-learn RandomForest (pickle or joblib format).",
            )

            if uploaded is not None:
                import hashlib
                model_bytes = uploaded.read()
                model_hash = hashlib.md5(model_bytes).hexdigest()

                if st.session_state.get("_model_bytes_hash") != model_hash:
                    # New model uploaded — load and create explainer
                    from core.model_pipeline import load_model, create_explainer
                    try:
                        with st.spinner("Loading model…"):
                            model = load_model(model_bytes)
                        st.session_state.rf_model = model
                        st.session_state.shap_explainer = None  # reset, rebuild below
                        st.session_state._model_bytes_hash = model_hash

                        # Infer n_features from model
                        n_feat = getattr(model, "n_features_in_", None)
                        st.session_state.model_meta = {
                            "filename": uploaded.name,
                            "n_features": n_feat,
                            "type": type(model).__name__,
                        }

                        with st.spinner("Creating SHAP explainer (one-time)…"):
                            st.session_state.shap_explainer = create_explainer(model)

                        st.success(
                            f"Model loaded: {type(model).__name__}, "
                            f"{n_feat} features. SHAP ready."
                        )

                        # ── Persist session to disk ────────────────────────
                        try:
                            from core.session_persistence import save_session
                            save_session(st.session_state)
                        except Exception:
                            pass
                    except Exception:
                        st.error(
                            "The model file couldn't be loaded. "
                            "Make sure it's a scikit-learn estimator saved with "
                            "pickle or joblib (`.pkl` / `.joblib`)."
                        )
                        st.session_state.rf_model = None
                        st.session_state.shap_explainer = None

            # Fingerprint mismatch warning
            if st.session_state.rf_model is not None:
                n_feat = st.session_state.model_meta.get("n_features")
                if n_feat is not None and n_feat != st.session_state.fp_nbits:
                    st.warning(
                        f"Model expects {n_feat} features but fingerprint is set "
                        f"to {st.session_state.fp_nbits} bits. "
                        "Adjust **Number of Bits** above to match."
                    )

        # Status indicator (always visible)
        if st.session_state.rf_model is not None:
            meta = st.session_state.model_meta
            shap_status = ":material/check_circle: SHAP ready" if st.session_state.shap_explainer else ":material/hourglass_top: Building…"
            col_a, col_b = st.columns(2)
            col_a.metric("Features", meta.get("n_features", "?"))
            col_b.metric("Type", meta.get("type", "?"))
            st.caption(shap_status)
        else:
            st.caption(":material/upload_file: No model loaded.")

    def _render_design_settings(self):
        """Render design-engine controls (variant count, shown when model is loaded)."""
        n_variants = st.slider(
            "Variants per run",
            min_value=50,
            max_value=500,
            value=st.session_state.design_n_variants,
            step=50,
            key="sidebar_design_n_variants",
            help=(
                "Number of structural variants generated per design run. "
                "Higher values give better coverage but take longer."
            ),
        )
        st.session_state.design_n_variants = n_variants
        st.caption(
            f":material/science: Design engine active · {n_variants} variants per run"
        )

    def _render_test_set_upload(self):
        """Render test set CSV upload for the Evaluation page."""
        model = st.session_state.get("rf_model")
        test_df = st.session_state.get("test_df")

        if model is None:
            st.caption(":material/info: Load a model first to enable test set upload.")
            return

        with st.expander("Upload Test Set (CSV)", expanded=False):
            uploaded = st.file_uploader(
                "CSV with SMILES + binary target",
                type=["csv"],
                key="test_set_upload",
                help="Same format as training CSV: SMILES column + binary label column (0/1).",
            )

            if uploaded is not None:
                import pandas as pd
                import hashlib
                import io as _io

                csv_bytes = uploaded.read()
                csv_hash = hashlib.md5(csv_bytes).hexdigest()

                if st.session_state.get("_test_csv_hash") != csv_hash:
                    df = pd.read_csv(_io.BytesIO(csv_bytes))
                    st.session_state["_test_pending_df"] = df
                    st.session_state["_test_csv_hash"] = csv_hash

                df = st.session_state.get("_test_pending_df")
                if df is not None:
                    cols = list(df.columns)
                    st.caption(f"{len(df)} rows · {len(cols)} columns")

                    smiles_col = st.selectbox(
                        "SMILES column", cols, key="test_smiles_col"
                    )
                    label_col = st.selectbox(
                        "Target column",
                        cols,
                        index=min(1, len(cols) - 1),
                        key="test_label_col",
                    )

                    if st.button("Load test set", key="load_test_btn", type="primary"):
                        self._process_test_set(df, smiles_col, label_col, model)
                        st.rerun()

            if test_df is not None:
                if st.button(
                    ":material/delete: Clear test set",
                    key="clear_test_btn",
                    width="stretch",
                ):
                    for k in ("test_df", "test_df_meta", "_test_csv_hash", "_test_pending_df"):
                        st.session_state.pop(k, None)
                    try:
                        from core.session_persistence import save_session
                        save_session(st.session_state)
                    except Exception:
                        pass
                    st.rerun()

        # Status badge (always visible, outside expander)
        if test_df is not None:
            meta = st.session_state.get("test_df_meta", {})
            n = meta.get("n_molecules", len(test_df))
            st.caption(f":material/check_circle: Test set loaded — {n} molecules")
        else:
            st.caption(":material/info: Upload a test set to enable the Evaluation page")

    def _process_test_set(self, df, smiles_col: str, label_col: str, model) -> None:
        """Compute fingerprints + predictions for the test CSV and store results."""
        import numpy as np
        from rdkit import Chem
        from rdkit.Chem import AllChem, DataStructs

        radius = st.session_state.fp_radius
        nbits = st.session_state.fp_nbits

        # Build fingerprint matrix in one pass, track failures
        rows_valid: list[int] = []
        X_rows: list[np.ndarray] = []
        n_failed = 0

        prog = st.progress(0.0, text="Computing fingerprints…")
        smiles_list = df[smiles_col].tolist()
        total = len(smiles_list)
        for i, smi in enumerate(smiles_list):
            prog.progress((i + 1) / total, text=f"Molecule {i + 1}/{total}…")
            mol = Chem.MolFromSmiles(str(smi).strip())
            if mol is None:
                n_failed += 1
                continue
            fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=nbits)
            arr = np.zeros(nbits, dtype=np.int32)
            DataStructs.ConvertToNumpyArray(fp, arr)
            X_rows.append(arr)
            rows_valid.append(i)
        prog.empty()

        pred_probas: list = [None] * total
        if X_rows:
            X = np.vstack(X_rows)
            probas = model.predict_proba(X)[:, 1]
            for idx, proba in zip(rows_valid, probas):
                pred_probas[idx] = float(proba)

        df = df.copy()
        df["_pred_proba"] = pred_probas
        df_clean = df[df["_pred_proba"].notna()].copy()
        df_clean["_pred_label"] = (df_clean["_pred_proba"] >= 0.5).astype(int)

        st.session_state["test_df"] = df_clean
        st.session_state["test_df_meta"] = {
            "smiles_col": smiles_col,
            "label_col": label_col,
            "n_molecules": len(df_clean),
            "n_failed": n_failed,
        }

        if n_failed:
            st.warning(f"{n_failed} rows skipped (invalid SMILES).")
        st.success(f"Test set loaded — {len(df_clean)} molecules.")

        try:
            from core.session_persistence import save_session
            save_session(st.session_state)
        except Exception:
            pass

    def _render_quick_actions(self):
        """Render quick action buttons."""
        if st.button(":material/delete_sweep: Clear Chat", width="stretch"):
            if "messages" in st.session_state:
                st.session_state.messages = []
            st.rerun()

        if st.session_state.get("_confirm_reset"):
            st.warning("This will clear all settings. Continue?")
            col_y, col_n = st.columns(2)
            with col_y:
                if st.button("Yes, reset", key="_reset_confirm_yes", width="stretch"):
                    st.session_state.llm_provider = "groq"
                    st.session_state.llm_model = "llama-3.3-70b-versatile"
                    st.session_state.temperature = 0.7
                    st.session_state.current_smiles = ""
                    st.session_state._pending_smiles = ""
                    st.session_state.fp_radius = 2
                    st.session_state.fp_nbits = 2048
                    st.session_state.fp_use_features = False
                    st.session_state._confirm_reset = False
                    st.rerun()
            with col_n:
                if st.button("Cancel", key="_reset_confirm_no", width="stretch"):
                    st.session_state._confirm_reset = False
                    st.rerun()
        else:
            if st.button(":material/restart_alt: Reset Settings", width="stretch"):
                st.session_state._confirm_reset = True
                st.rerun()
