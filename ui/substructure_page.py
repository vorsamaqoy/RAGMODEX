"""Substructure Search page — standalone full-width page."""

import streamlit as st


def render_substructure_search_page():
    """Render the Substructure Search page."""
    from rdkit import Chem
    from rdkit.Chem import AllChem
    from rdkit.Chem.Draw import rdMolDraw2D

    st.markdown(":material/search: **Substructure Search**")
    st.caption("Enter a SMILES and optionally a SMARTS pattern to highlight matching substructures.")

    col_input, col_result = st.columns([1, 1])

    with col_input:
        with st.container(border=True):
            smiles_input = st.text_input(
                "SMILES",
                placeholder="O=C(Nc1ccccc1)c1ccncc1",
                key="ss_smiles",
            )
            smarts_input = st.text_input(
                "SMARTS (highlight pattern)",
                placeholder="c1ccncc1 (optional)",
                key="ss_smarts",
            )
            visualize = st.button(":material/search: Visualize", key="ss_btn", width="stretch")

    with col_result:
        if visualize and not smiles_input:
            st.warning("Enter a SMILES string")
        elif visualize and smiles_input:
            mol = Chem.MolFromSmiles(smiles_input)
            if mol is None:
                st.error(":material/cancel: Invalid SMILES")
            else:
                highlight_atoms: list = []
                highlight_bonds: list = []
                pattern = None

                if smarts_input:
                    pattern = Chem.MolFromSmarts(smarts_input)
                    if pattern is not None:
                        matches = mol.GetSubstructMatches(pattern)
                        if matches:
                            highlight_atoms = list(matches[0])
                            for i, ai in enumerate(highlight_atoms):
                                for aj in highlight_atoms[i + 1:]:
                                    bond = mol.GetBondBetweenAtoms(ai, aj)
                                    if bond is not None:
                                        highlight_bonds.append(bond.GetIdx())

                AllChem.Compute2DCoords(mol)

                drawer = rdMolDraw2D.MolDraw2DSVG(400, 350)
                drawer.drawOptions().useBWAtomPalette()

                if highlight_atoms:
                    colors = {a: (0.133, 0.827, 0.933, 0.3) for a in highlight_atoms}
                    bond_colors = {b: (0.133, 0.827, 0.933, 0.5) for b in highlight_bonds}
                    drawer.DrawMolecule(
                        mol,
                        highlightAtoms=highlight_atoms,
                        highlightAtomColors=colors,
                        highlightBonds=highlight_bonds,
                        highlightBondColors=bond_colors,
                    )
                else:
                    drawer.DrawMolecule(mol)

                drawer.FinishDrawing()
                svg = drawer.GetDrawingText()

                st.markdown(
                    f"<div style='background:#f5f3ee;border-radius:8px;"
                    f"padding:0.5rem;'>{svg}</div>",
                    unsafe_allow_html=True,
                )

                if smarts_input and pattern is not None:
                    n_matches = len(mol.GetSubstructMatches(pattern))
                    if n_matches:
                        st.success(f":material/check_circle: Found {n_matches} match(es)")
                    else:
                        st.warning(":material/warning: SMARTS pattern not found in this molecule")
                elif smarts_input and pattern is None:
                    st.error(":material/cancel: Invalid SMARTS pattern")
