"""
Molecular Feature Interpreter - Main Streamlit Application
"""

import streamlit as st
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from rdkit import RDLogger
RDLogger.DisableLog('rdApp.*')   # suppress RDKit parse warnings

from config.settings import Settings, settings
from config.api_config import APIConfig, api_config
from ui.styles import Styles
from ui.sidebar import Sidebar
from ui.chat_interface import ChatInterface
from ui.structure_panel import StructurePanel
from llm.chat_handler import ChatHandler
from llm.client_factory import LLMClientFactory
from rag.retriever import Retriever
from core.session_persistence import session_exists, load_session, delete_session, peek_session_meta


def init_app():
    _logo = Path("assets/logo.png")
    st.set_page_config(
        page_title="MolChat — Molecular AI Interpreter",
        page_icon=str(_logo) if _logo.exists() else "🧬",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(Styles.get_css(), unsafe_allow_html=True)



    if "app_initialized" not in st.session_state:
        settings.ensure_dirs()
        st.session_state.app_initialized = True
        st.session_state.chat_handler = None
        st.session_state.retriever = None


def init_llm(provider: str, model: str, temperature: float):
    try:
        if (
            st.session_state.chat_handler is None
            or st.session_state.get("last_provider") != provider
            or st.session_state.get("last_model") != model
        ):
            chat_handler = ChatHandler(provider=provider, model=model)
            chat_handler.set_temperature(temperature)
            st.session_state.chat_handler = chat_handler
            st.session_state.last_provider = provider
            st.session_state.last_model = model
        else:
            st.session_state.chat_handler.set_temperature(temperature)
    except Exception:
        st.error(
            f"Could not connect to **{provider}**. "
            "Check your API key in `.env` and make sure the service is reachable."
        )


def init_retriever():
    if st.session_state.retriever is None:
        try:
            retriever = Retriever(
                embedding_model=settings.embedding_model,
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
                top_k=settings.top_k_results,
            )
            index_path = settings.rag_index_dir
            if index_path.exists():
                retriever.load(str(index_path))
            st.session_state.retriever = retriever
        except Exception:
            st.session_state.retriever = None


def _show_restore_dialog():
    """Render a full-page restore prompt and call st.stop() until the user decides."""
    meta = peek_session_meta()

    st.markdown(
        "<h2 style='margin-top:2rem;'>Continue where you left off?</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"A saved session from **{meta.get('timestamp', '—')}** was found. "
        "Restore it to reload your training data, model, and bit database — "
        "or discard it and start clean."
    )
    st.markdown("")

    detail_col, btn_col = st.columns([1, 1], gap="large")

    with detail_col:
        parts = []
        if meta.get("has_training"):
            n_mol = meta.get("n_molecules", "—")
            n_bits = meta.get("n_bits", "—")
            parts.append(f"{n_mol} molecules · {n_bits} bits indexed")
        if meta.get("has_model"):
            model_name = meta.get("model_name", "—")
            model_type = meta.get("model_type", "—")
            parts.append(f"{model_type}: {model_name}")
        if parts:
            st.markdown(
                "<br>".join(
                    f"<span style='font-size:0.85rem;color:var(--color-text-muted);'>{p}</span>"
                    for p in parts
                ),
                unsafe_allow_html=True,
            )

    with btn_col:
        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
        if st.button(":material/restore: Restore saved session", type="primary", width="stretch"):
            with st.spinner("Loading your previous session…"):
                load_session(st.session_state)
            st.session_state["_restore_choice"] = "resumed"
            st.rerun()

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        if st.button(":material/delete_sweep: Discard and start fresh", width="stretch"):
            delete_session()
            st.session_state["_restore_choice"] = "fresh"
            st.rerun()

    st.stop()


def main():
    init_app()

    # ── Session restore dialog (shown once per process start) ──────────────
    if session_exists() and not st.session_state.get("_restore_choice"):
        _show_restore_dialog()

    sidebar = Sidebar()
    app_settings = sidebar.render()

    init_llm(app_settings["provider"], app_settings["model"], app_settings["temperature"])
    init_retriever()

    page = app_settings.get("page", "💬 Chat")

    if page == "🧬 ECFP/MACCS Visualizer":
        from ui.visualizer_page import render_visualizer_page
        render_visualizer_page()
        return

    if page == "🔮 Prediction":
        from ui.prediction_page import render_prediction_page
        render_prediction_page()
        return

    if page == "🔍 Substructure Search":
        from ui.substructure_page import render_substructure_search_page
        render_substructure_search_page()
        return

    if page == "🧪 Design":
        from ui.design_panel import render_design_panel
        render_design_panel()
        return

    if page == "📊 Evaluation":
        from ui.evaluation_page import render_evaluation_page
        render_evaluation_page()
        return

    if page == "🔬 Virtual screening":
        from app_pages.virtual_screening import render_virtual_screening
        render_virtual_screening()
        return

    # ── Chat page ──────────────────────────────────────────────────────────
    chat_interface = ChatInterface(
        chat_handler=st.session_state.chat_handler,
        retriever=st.session_state.retriever,
    )
    structure_panel = StructurePanel()

    # Process input BEFORE columns render so current_structures is populated
    # when struct_col renders on the subsequent rerun.
    # Check for programmatic prompt (e.g. from welcome screen example buttons).
    if pending := st.session_state.pop("_pending_prompt", None):
        chat_interface.handle_input(pending)
        st.rerun()

    if prompt := st.chat_input("Ask a question..."):
        chat_interface.handle_input(prompt)

    chat_col, struct_col = st.columns([6.5, 3.5], gap="medium")

    with chat_col:
        # Height is a fallback; CSS calc(100vh - 250px) overrides it on desktop.
        # A large sentinel avoids Streamlit capping the container unexpectedly.
        chat_container = st.container(height=2000)
        with chat_container:
            chat_interface.render_messages()

    with struct_col:
        structure_panel.render()


if __name__ == "__main__":
    main()
