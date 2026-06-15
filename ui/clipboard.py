"""clipboard.py — Reusable browser clipboard widget for Streamlit.

Uses the browser-native Clipboard API with execCommand fallback.
Each widget renders in its own iframe via st.components.v1.html so there
are no JS name-collision issues between multiple instances.
"""
from __future__ import annotations

import html as _html_lib

import streamlit.components.v1 as components


def smiles_clipboard_widget(smiles: str, uid: str = "") -> None:
    """Render a compact inline clipboard copy widget.

    Shows the SMILES string (truncated at 40 chars) with a 📋 icon button.
    On click, copies the full SMILES to the clipboard via the browser API and
    briefly flashes a green ✓ for 1.5 s.

    Args:
        smiles: Full SMILES string to copy.
        uid:    Optional unique suffix for JS identifiers. Auto-derived from
                the SMILES hash if omitted.
    """
    if not uid:
        uid = str(abs(hash(smiles)) % 9_999_999)

    display = smiles if len(smiles) <= 40 else smiles[:37] + "…"
    # Store the SMILES in an HTML data attribute to avoid any JS quoting issues
    safe_attr = _html_lib.escape(smiles, quote=True)
    safe_display = _html_lib.escape(display)

    html = f"""
<div id="cw_{uid}"
     data-smi="{safe_attr}"
     style="display:flex;align-items:center;gap:4px;
            font-family:var(--font-main,'Space Grotesk',sans-serif);font-size:0.75rem;color:#8890c4;
            background:rgba(255,255,255,0.03);border:1px solid #1c2040;
            border-radius:6px;padding:3px 6px;box-sizing:border-box;
            max-width:100%;overflow:hidden;">
  <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
               flex:1;min-width:0;" title="{safe_attr}">{safe_display}</span>
  <button id="cb_{uid}"
          onclick="doCopy_{uid}()"
          style="background:none;border:none;cursor:pointer;font-size:0.9rem;
                 padding:0 1px;color:#8890c4;flex-shrink:0;line-height:1;"
          title="Copy SMILES to clipboard">&#128203;</button>
</div>
<script>
(function() {{
  function doCopy_{uid}() {{
    var s   = document.getElementById('cw_{uid}').getAttribute('data-smi');
    var btn = document.getElementById('cb_{uid}');
    function flash() {{
      btn.innerHTML = '&#10003;';
      btn.style.color = '#50c896';
      setTimeout(function() {{
        btn.innerHTML = '&#128203;';
        btn.style.color = '#8890c4';
      }}, 1500);
    }}
    if (navigator.clipboard && navigator.clipboard.writeText) {{
      navigator.clipboard.writeText(s).then(flash, function() {{ _fb_{uid}(s, flash); }});
    }} else {{
      _fb_{uid}(s, flash);
    }}
  }}
  function _fb_{uid}(s, cb) {{
    var ta = document.createElement('textarea');
    ta.value = s;
    ta.style.cssText = 'position:fixed;opacity:0;top:0;left:0;width:1px;height:1px;';
    document.body.appendChild(ta);
    ta.focus(); ta.select();
    try {{ document.execCommand('copy'); cb(); }} catch(e) {{}}
    document.body.removeChild(ta);
  }}
  window['doCopy_{uid}'] = doCopy_{uid};
}})();
</script>
"""
    components.html(html, height=28, scrolling=False)
