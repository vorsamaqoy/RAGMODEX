"""CSS styling for the Streamlit app — Light Lab Theme."""


class Styles:
    """CSS styles for the application."""

    MAIN_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=DM+Serif+Display:ital@0;1&display=swap');

/* ===== DESIGN TOKENS — Lab Parchment + Warm Amber ===== */
:root {
    /* Backgrounds — neutral grey lab */
    --color-bg:           #f0f0f0;
    --color-surface:      #fafafa;
    --color-surface-deep: #f4f4f4;
    --color-card:         #ffffff;

    /* Borders — cool grey */
    --color-border:        #e0e0e0;
    --color-border-subtle: #cccccc;

    /* Text — deep cool ink */
    --color-text:       #1e1c24;
    --color-text-muted: #65656f;
    --color-text-dim:   #a8a8b0;
    --color-text-dark:  #8c8c98;

    /* Accent — teal blue */
    --color-accent:     #2a7d9e;
    --color-accent-a10: color-mix(in srgb, var(--color-accent) 10%, transparent);
    --color-accent-a15: color-mix(in srgb, var(--color-accent) 15%, transparent);
    --color-accent-a25: color-mix(in srgb, var(--color-accent) 25%, transparent);
    --color-accent-a30: color-mix(in srgb, var(--color-accent) 30%, transparent);
    --color-accent-a40: color-mix(in srgb, var(--color-accent) 40%, transparent);
    --color-accent-a45: color-mix(in srgb, var(--color-accent) 45%, transparent);
    --color-accent-a50: color-mix(in srgb, var(--color-accent) 50%, transparent);
    --color-accent-light: #d8eef7;    /* tinted bg for accent surfaces */

    /* Semantic */
    --color-success:     #23775a;
    --color-success-a08: rgba(35, 119, 90, 0.08);
    --color-success-a12: rgba(35, 119, 90, 0.12);
    --color-danger:      #b83245;
    --color-danger-a08:  rgba(184, 50, 69, 0.08);
    --color-danger-a12:  rgba(184, 50, 69, 0.12);
    --color-warning:     #b86020;
    --color-warning-alt: #9a5018;

    /* Utility */
    --color-black-a06: rgba(0, 0, 0, 0.06);
    --color-black-a12: rgba(0, 0, 0, 0.12);

    /* Shadows */
    --shadow-sm: 0 1px 3px rgba(0,0,0,0.07), 0 1px 2px rgba(0,0,0,0.04);
    --shadow-md: 0 4px 12px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.04);

    /* Typography */
    --font-main:    'Space Grotesk', sans-serif;
    --font-display: 'DM Serif Display', Georgia, serif;

    /* Type scale */
    --text-2xs:  0.625rem;
    --text-xs:   0.6875rem;
    --text-sm:   0.75rem;
    --text-md:   0.875rem;
    --text-base: 1rem;
    --text-lg:   1.125rem;
    --text-xl:   1.5rem;

    /* Weights */
    --weight-light:   300;
    --weight-regular: 400;
    --weight-medium:  500;
    --weight-semi:    600;
    --weight-bold:    700;

    /* Line heights */
    --lh-tight:  1.2;
    --lh-snug:   1.4;
    --lh-normal: 1.55;

    /* Letter spacing */
    --ls-tight: -0.01em;
    --ls-caps:   0.08em;

    /* Spacing */
    --space-1: 0.25rem;
    --space-2: 0.5rem;
    --space-3: 0.75rem;
    --space-4: 1rem;
    --space-5: 1.5rem;
    --space-6: 2rem;
    --space-7: 3rem;
}

/* ===== GLOBAL ===== */
.stApp {
    background-color: var(--color-bg);
    color: var(--color-text);
    font-family: var(--font-main);
    font-size: var(--text-md);
    line-height: var(--lh-normal);
    overflow: hidden;
    height: 100vh;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-rendering: optimizeLegibility;
    font-kerning: normal;
    font-synthesis: none;
}

header[data-testid="stHeader"] {
    background-color: transparent;
}

/* ===== TEXT ===== */
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3,
[data-testid="stMarkdownContainer"] h4,
[data-testid="stMarkdownContainer"] h5,
[data-testid="stMarkdownContainer"] h6,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] span,
[data-testid="stMarkdownContainer"] strong,
[data-testid="stMarkdownContainer"] em,
[data-testid="stMarkdownContainer"] a,
[data-testid="stText"],
[data-testid="stMetricValue"],
[data-testid="stMetricLabel"],
[data-testid="stMetricDelta"],
[data-testid="stWidgetLabel"] p,
[data-testid="stCaptionContainer"] p,
.streamlit-expanderHeader,
[data-testid="stExpander"] p,
[data-testid="stExpander"] span,
[data-testid="stDataFrameResizable"] {
    color: var(--color-text) !important;
}

/* Code blocks */
[data-testid="stMarkdownContainer"] pre {
    background-color: var(--color-surface-deep) !important;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    border: 1px solid var(--color-border);
    overflow-x: auto;
    box-shadow: var(--shadow-sm);
}
[data-testid="stMarkdownContainer"] pre code,
[data-testid="stMarkdownContainer"] pre code span,
[data-testid="stMarkdownContainer"] pre code * {
    color: var(--color-text-muted) !important;
    background-color: transparent !important;
}
/* Inline code */
[data-testid="stMarkdownContainer"] code:not(pre code) {
    background-color: var(--color-surface-deep) !important;
    color: var(--color-success) !important;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: var(--font-main);
    font-size: 0.85em;
    border: 1px solid var(--color-border);
}

/* Tabs: active keeps dark text on accent background */
.stTabs [aria-selected="true"],
.stTabs [aria-selected="true"] * {
    color: var(--color-card) !important;
}

/* ===== MAIN CONTENT AREA ===== */
.main .block-container {
    background-color: var(--color-surface);
    border-radius: 16px;
    padding: 0.75rem 1.5rem 0.75rem 1.5rem !important;
    margin: 0.3rem 0.5rem 0 0;
    max-width: 100%;
    max-height: calc(100vh - 62px);
    overflow: hidden;
    border: 1px solid var(--color-border);
    box-shadow: var(--shadow-md);
}

/* ===== SIDEBAR ===== */
[data-testid="stSidebar"] {
    background-color: var(--color-bg) !important;
}
[data-testid="stSidebar"] > div:first-child {
    background-color: var(--color-bg) !important;
}
[data-testid="stSidebarContent"] {
    background-color: var(--color-surface-deep);
    border-radius: 12px;
    margin: 0.5rem 0.75rem 0.75rem 0.25rem;
    padding: 0.5rem;
    border: 1px solid var(--color-border);
    box-shadow: var(--shadow-sm);
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
[data-testid="stSidebar"] [data-testid="stMetricValue"],
[data-testid="stSidebar"] [data-testid="stMetricLabel"] {
    color: var(--color-text) !important;
}

/* ===== SIDEBAR SECTION LABELS ===== */
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p:has(> strong) {
    margin: var(--space-3) 0 var(--space-1) 0 !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p strong {
    display: block;
    color: var(--color-text-muted) !important;
    font-size: var(--text-xs) !important;
    font-weight: var(--weight-semi) !important;
    text-transform: uppercase !important;
    letter-spacing: var(--ls-caps) !important;
    padding: 0 !important;
}
[data-testid="stSidebar"] hr {
    margin: var(--space-2) 0 !important;
    border-color: var(--color-border) !important;
    opacity: 0.7;
}

/* ===== MOLECULE CARDS ===== */
div[data-testid="stHorizontalBlock"] div[data-testid="stColumn"] {
    background-color: var(--color-card);
    border-radius: 12px;
    padding: 1rem !important;
    margin: 0 0.2rem;
    border: 1px solid var(--color-border);
    box-shadow: var(--shadow-sm);
}

/* ===== COLUMN HEIGHT ===== */
[data-testid="stColumn"] {
    overflow-y: auto !important;
    max-height: calc(100vh - 100px);
}
[data-testid="stColumn"] > div:first-child {
    padding-bottom: 1.5rem !important;
}

/* ===== STRUCTURE PANEL ===== */
[data-testid="stColumn"]:last-child {
    border-left: 1px solid var(--color-border);
    padding-left: 0.75rem !important;
}

/* ===== TAB PANELS ===== */
[data-baseweb="tab-panel"] {
    overflow-y: auto !important;
    max-height: calc(100vh - 200px);
    min-height: 0;
}

/* ===== SECTION SELECTBOX ===== */
[data-testid="stColumn"]:last-child [data-testid="stSelectbox"]:first-child > div > div {
    background-color: var(--color-surface-deep) !important;
    color: var(--color-text) !important;
    border-radius: 8px;
    font-weight: 600;
    border: 1px solid var(--color-border-subtle) !important;
}

/* ===== DOWNLOAD BUTTONS ===== */
[data-testid="stDownloadButton"] > button {
    background-color: var(--color-surface-deep) !important;
    color: var(--color-accent) !important;
    border: 1px solid var(--color-border-subtle) !important;
    border-radius: 20px !important;
    padding: 0.35rem 1.5rem !important;
    font-weight: 500;
    display: block;
    margin: 0.5rem auto 0 auto;
    width: auto !important;
    box-shadow: var(--shadow-sm);
}
[data-testid="stDownloadButton"] > button:hover {
    background-color: var(--color-accent) !important;
    color: var(--color-card) !important;
    border-color: var(--color-accent) !important;
}

/* ===== CHAT INPUT ===== */
[data-testid="stChatInputContainer"] {
    background-color: var(--color-card) !important;
    border-radius: 24px !important;
    border: 1px solid var(--color-border-subtle) !important;
    box-shadow: var(--shadow-sm);
}
[data-testid="stChatInputContainer"]:focus-within {
    border-color: var(--color-accent) !important;
    box-shadow: 0 0 0 3px var(--color-accent-a15) !important;
}

/* ===== CHAT MESSAGES ===== */
[data-testid="stChatMessage"] {
    background-color: var(--color-card);
    border: 1px solid var(--color-border);
    border-radius: 12px;
    margin-bottom: var(--space-2);
    padding: var(--space-2) var(--space-3);
    box-shadow: var(--shadow-sm);
}

/* ===== CHAT CONTAINER ===== */
[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 12px !important;
    border: 1px solid var(--color-border) !important;
    background-color: var(--color-surface-deep) !important;
    height: calc(100vh - 250px) !important;
    max-height: calc(100vh - 250px) !important;
    overflow-y: auto !important;
}

/* ===== DIVIDER ===== */
hr {
    border-color: var(--color-border);
    border-style: solid;
}

/* ===== SIDEBAR BUTTONS ===== */
[data-testid="stSidebar"] .stButton > button {
    border-radius: 8px;
    border: 1px solid var(--color-border);
    background-color: var(--color-card);
    color: var(--color-text-muted);
    box-shadow: var(--shadow-sm);
}
[data-testid="stSidebar"] .stButton > button:hover {
    border-color: var(--color-accent);
    background-color: var(--color-accent-light);
    color: var(--color-accent);
}

/* ===== MAIN BUTTONS ===== */
.stButton > button {
    background-color: var(--color-card);
    color: var(--color-accent);
    border: 1px solid var(--color-border);
    border-radius: 8px;
    font-family: var(--font-main);
    font-weight: 500;
    box-shadow: var(--shadow-sm);
    transition: background-color 0.15s ease, color 0.15s ease,
                border-color 0.15s ease, box-shadow 0.15s ease;
}
.stButton > button:hover {
    background-color: var(--color-accent-light);
    color: var(--color-accent);
    border-color: var(--color-accent);
    box-shadow: var(--shadow-md);
}

/* ===== FOCUS VISIBLE ===== */
.stButton > button:focus-visible,
[data-testid="stSelectbox"] > div:focus-visible,
[data-testid="stTextInput"] input:focus-visible,
[data-testid="stCheckbox"] input:focus-visible + div,
[data-baseweb="slider"] [role="slider"]:focus-visible,
[data-testid="stFileUploader"]:focus-within,
[data-testid="stSegmentedControl"] button:focus-visible,
[data-baseweb="tab"]:focus-visible,
[data-testid="stNumberInput"] input:focus-visible,
[data-testid="stPills"] button:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 2px;
}

/* ===== INPUTS ===== */
.stTextInput > div > div > input {
    border-radius: 10px;
    background-color: var(--color-card);
    border-color: var(--color-border-subtle);
    color: var(--color-text) !important;
    box-shadow: var(--shadow-sm);
}
.stTextInput > div > div > input::placeholder {
    color: var(--color-text-dim);
}
.stTextInput > div > div > input:focus {
    border-color: var(--color-accent) !important;
    box-shadow: 0 0 0 3px var(--color-accent-a15) !important;
}

/* ===== SELECTBOX ===== */
.stSelectbox > div > div {
    border-radius: 10px;
    background-color: var(--color-card);
    border-color: var(--color-border-subtle);
    color: var(--color-text) !important;
    box-shadow: var(--shadow-sm);
}

/* ===== METRICS ===== */
[data-testid="stMetric"] {
    background-color: var(--color-card);
    padding: var(--space-3) var(--space-3) var(--space-2);
    border-radius: 10px;
    border: 1px solid var(--color-border);
    margin-top: var(--space-1);
    box-shadow: var(--shadow-sm);
}

/* ===== TABS ===== */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.5rem;
    background-color: transparent;
}
.stTabs [data-baseweb="tab"] {
    padding: 0.4rem 1rem;
    border-radius: 8px 8px 0 0;
    background-color: var(--color-surface-deep);
    color: var(--color-text-muted);
    font-weight: var(--weight-medium);
    font-size: var(--text-md);
    line-height: var(--lh-tight);
    letter-spacing: 0.01em;
    border: 1px solid var(--color-border);
    border-bottom: none;
}
.stTabs [aria-selected="true"] {
    background-color: var(--color-accent) !important;
    color: var(--color-card) !important;
    font-weight: var(--weight-semi) !important;
    border-color: var(--color-accent) !important;
}

/* ===== EXPANDER ===== */
.streamlit-expanderHeader {
    color: var(--color-text-muted);
    font-weight: 500;
    background-color: var(--color-surface-deep);
    border-radius: 8px;
}

/* ===== HIDE STREAMLIT BRANDING ===== */
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }

/* ===== FINGERPRINT BADGES ===== */
.fp-badge-active {
    background: var(--color-accent);
    color: var(--color-card);
    padding: 2px 6px;
    margin: 1px;
    border-radius: 3px;
    font-size: var(--text-xs);
    font-weight: var(--weight-medium);
    line-height: var(--lh-tight);
    display: inline-block;
}
.fp-badge-inactive {
    background: var(--color-surface-deep);
    color: var(--color-text);
    padding: 2px 6px;
    margin: 1px;
    border-radius: 3px;
    font-size: var(--text-xs);
    font-weight: var(--weight-medium);
    line-height: var(--lh-tight);
    display: inline-block;
    border: 1px solid var(--color-border-subtle);
}

/* ===== SHAP SECTION ===== */
.shap-section {
    background-color: var(--color-card);
    border-radius: 12px;
    padding: var(--space-5) var(--space-5) var(--space-3);
    margin-bottom: var(--space-4);
    border: 1px solid var(--color-border);
    border-top: 3px solid var(--color-success);
    box-shadow: var(--shadow-sm);
}

/* ===== PREDICTION CARD ===== */
.prediction-card {
    border-radius: 12px;
    padding: var(--space-3) var(--space-4);
    border: 1px solid var(--color-border);
    margin: var(--space-2) 0 var(--space-3);
    box-shadow: var(--shadow-sm);
}
.prediction-active {
    background-color: var(--color-success-a08);
    border-color: rgba(35, 119, 90, 0.25);
}
.prediction-inactive {
    background-color: var(--color-danger-a08);
    border-color: rgba(184, 50, 69, 0.25);
}

/* ===== PROBABILITY BAR ===== */
.prob-bar {
    height: 8px;
    border-radius: 4px;
    background-color: var(--color-border);
    margin-top: 0.5rem;
}
.prob-bar-fill       { height: 100%; border-radius: 4px; }
.prob-bar-active     { background: linear-gradient(90deg, var(--color-success), var(--color-accent)); }
.prob-bar-inactive   { background: linear-gradient(90deg, var(--color-danger), var(--color-warning)); }

/* ===== AD BADGE ===== */
.ad-badge {
    display: inline-block;
    padding: 0.3rem 0.8rem;
    border-radius: 20px;
    font-size: var(--text-md);
    font-weight: var(--weight-semi);
    font-family: var(--font-main);
    line-height: var(--lh-tight);
    margin: 0.4rem 0 0.6rem 0;
}
.ad-inside  {
    background-color: var(--color-success-a12);
    color: var(--color-success);
    border: 1px solid rgba(35, 119, 90, 0.35);
}
.ad-outside {
    background-color: var(--color-danger-a12);
    color: var(--color-danger);
    border: 1px solid rgba(184, 50, 69, 0.35);
}

/* ===== SECTION HEADER ===== */
.section-header {
    font-family: var(--font-main);
    font-size: var(--text-xs);
    font-weight: var(--weight-semi);
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: var(--ls-caps);
    line-height: var(--lh-tight);
    margin: 1rem 0 0.4rem 0;
    padding-bottom: 0.25rem;
    border-bottom: 1px solid var(--color-border);
}

/* ===== UTILITY CLASSES ===== */
.panel-title {
    font-family: var(--font-main);
    color: var(--color-text);
    font-size: var(--text-base);
    font-weight: var(--weight-medium);
    line-height: var(--lh-tight);
    margin-bottom: 0.5rem;
}

.app-brand-name {
    font-family: var(--font-display);
    color: var(--color-accent);
    font-size: var(--text-xl);
    font-weight: var(--weight-regular);
    letter-spacing: var(--ls-tight);
    line-height: var(--lh-tight);
    margin: 0;
}

.app-brand-subtitle {
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    margin-top: 0.2rem;
    font-family: var(--font-main);
    font-weight: var(--weight-light);
    line-height: var(--lh-snug);
    letter-spacing: 0.02em;
}

.mol-card-label {
    font-family: var(--font-main);
    font-size: var(--text-xs);
    font-weight: var(--weight-medium);
    line-height: var(--lh-snug);
    margin-top: 0.4rem;
    padding-left: 0.4rem;
    color: var(--color-text);
}

/* ===== CUSTOM SCROLLBARS ===== */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: var(--color-accent-a25);
    border-radius: 10px;
}
::-webkit-scrollbar-thumb:hover { background: var(--color-accent-a45); }

[data-testid="stVerticalBlockBorderWrapper"]::-webkit-scrollbar-track,
[data-testid="stColumn"]:first-child::-webkit-scrollbar-track {
    margin-top: 8px;
    margin-bottom: 8px;
}
[data-testid="stSidebarContent"]::-webkit-scrollbar { width: 5px; }
[data-testid="stSidebarContent"]::-webkit-scrollbar-track {
    background: transparent;
    margin: 8px 0;
}
[data-testid="stSidebarContent"]::-webkit-scrollbar-thumb {
    background: var(--color-accent-a25);
    border-radius: 10px;
}
[data-testid="stSidebarContent"]::-webkit-scrollbar-thumb:hover {
    background: var(--color-accent-a40);
}

/* ===== HIDE STREAMLIT STATUS WIDGETS ===== */
div[data-testid="stStatusWidget"],
div[data-testid="stNotification"],
div[data-testid="stToolbar"],
div[data-testid="stDecoration"] {
    display: none !important;
    visibility: hidden !important;
}

/* ===== COMPACT HEIGHT MODE ===== */
@media (max-height: 650px) {
    .main .block-container {
        padding: 0.3rem 1rem 0.3rem 1rem !important;
    }
    [data-baseweb="tab-panel"] {
        max-height: calc(100vh - 130px);
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        height: calc(100vh - 200px) !important;
        max-height: calc(100vh - 200px) !important;
    }
}

/* ===== SIDEBAR SEMPRE VISIBILE (≥1100px) ===== */
@media (min-width: 1100px) {
    section[data-testid="stSidebar"] {
        transform: none !important;
        width: 21rem !important;
        min-width: 21rem !important;
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        left: 0 !important;
        position: relative !important;
    }
    [data-testid="stSidebarCollapseButton"],
    [data-testid="collapsedControl"] {
        display: none !important;
        visibility: hidden !important;
    }
}

/* ===== NARROW VIEWPORT FALLBACK (<1100px) ===== */
@media (max-width: 1099px) {
    .stApp {
        overflow-y: auto !important;
        height: auto !important;
    }
    .main .block-container {
        max-height: none !important;
        overflow-y: auto !important;
        margin-right: 0.25rem !important;
    }
    [data-testid="stColumn"] {
        max-height: none !important;
        overflow-y: visible !important;
    }
    [data-baseweb="tab-panel"] {
        max-height: none !important;
        overflow-y: visible !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        height: auto !important;
        max-height: 70vh !important;
    }
    [data-testid="stSidebarCollapseButton"] {
        display: flex !important;
        visibility: visible !important;
    }
}

/* ===== MOBILE (<768px) ===== */
@media (max-width: 768px) {
    [data-testid="stColumn"]:last-child {
        display: none !important;
    }
    [data-testid="stColumn"]:first-child {
        border-left: none !important;
        padding-left: 0 !important;
        max-width: 100% !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        height: auto !important;
        max-height: 60vh !important;
    }
    div[data-testid="stHorizontalBlock"] div[data-testid="stColumn"] {
        min-width: calc(50% - 0.4rem) !important;
        flex: 0 0 calc(50% - 0.4rem) !important;
    }
    .stButton > button { min-height: 44px !important; }
    [data-baseweb="tab"]  { min-height: 44px !important; }
}

/* ===== SIDEBAR RESIZE HANDLE ===== */
[data-testid="stSidebarResizeHandle"] {
    background-color: var(--color-accent-a30) !important;
}
[data-testid="stSidebarResizeHandle"]:hover,
[data-testid="stSidebarResizeHandle"]:active {
    background-color: var(--color-accent-a50) !important;
}
[data-testid="stSidebarResizeHandle"] > div {
    background-color: transparent !important;
}

/* ===== BUTTON TEXT ===== */
[data-testid="stButton"] button [data-testid="stMarkdownContainer"] p,
[data-testid="stButton"] button [data-testid="stMarkdownContainer"] span,
[data-testid="stButton"] button p {
    color: var(--color-accent) !important;
}
[data-testid="stButton"] button:hover [data-testid="stMarkdownContainer"] p,
[data-testid="stButton"] button:hover [data-testid="stMarkdownContainer"] span,
[data-testid="stButton"] button:hover p {
    color: var(--color-accent) !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] button [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stButton"] button p {
    color: var(--color-text-muted) !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] button:hover [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stButton"] button:hover p {
    color: var(--color-accent) !important;
}

/* ===== MOLECULE IMAGES ===== */
[data-testid="stImage"] img {
    background: #f5f3ee;
    border-radius: 6px;
    border: 1px solid var(--color-border);
}
[data-testid="stColumn"]:last-child [data-testid="stImage"] {
    margin-bottom: 0.5rem;
    border-radius: 6px;
    overflow: hidden;
}
[data-testid="stColumn"]:last-child [data-testid="stImage"] img {
    border-radius: 6px;
}

/* ===== METRICS — compact ===== */
[data-testid="stMetricValue"] {
    font-size: var(--text-lg) !important;
    font-weight: var(--weight-semi) !important;
    line-height: var(--lh-tight) !important;
    font-variant-numeric: tabular-nums;
    letter-spacing: var(--ls-tight) !important;
    color: var(--color-text) !important;
}
[data-testid="stMetricLabel"] {
    font-size: var(--text-sm) !important;
    font-weight: var(--weight-medium) !important;
    line-height: var(--lh-snug) !important;
    color: var(--color-text-muted) !important;
}
[data-testid="stMetricDelta"] {
    font-size: var(--text-sm) !important;
    font-variant-numeric: tabular-nums;
}

/* ===== FILE UPLOADER ===== */
[data-testid="stFileUploader"] {
    border: 1px dashed var(--color-border-subtle);
    border-radius: 8px;
    padding: 0.3rem;
    background: var(--color-card);
}

/* ===== LONG TEXT / SMILES OVERFLOW ===== */
.mol-card-label {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 100%;
}
.mol-card-label span {
    white-space: normal;
    word-break: break-word;
}
[data-testid="stImage"] figcaption {
    font-size: var(--text-xs);
    color: var(--color-text-muted);
    word-break: break-all;
    line-height: var(--lh-snug);
}

/* ===== NAV PILLS — light active state ===== */
[data-testid="stPills"] button[aria-selected="true"] {
    background-color: var(--color-accent-light) !important;
    color: var(--color-accent) !important;
    border-color: var(--color-accent-a30) !important;
    font-weight: var(--weight-semi) !important;
}
[data-testid="stPills"] button {
    color: var(--color-text-muted) !important;
}
[data-testid="stPills"] button:hover:not([aria-selected="true"]) {
    background-color: var(--color-border) !important;
    color: var(--color-text) !important;
}

/* ===== SEGMENTED CONTROL ===== */
[data-testid="stSegmentedControl"] button[aria-selected="true"] {
    background-color: var(--color-card) !important;
    color: var(--color-accent) !important;
    font-weight: var(--weight-semi) !important;
    box-shadow: var(--shadow-sm) !important;
}
[data-testid="stSegmentedControl"] {
    background-color: var(--color-border) !important;
    border-radius: 10px !important;
}

/* ===== SUCCESS / INFO / WARNING / ERROR ALERTS ===== */
[data-testid="stAlert"][kind="success"] {
    background-color: var(--color-success-a08) !important;
    border-color: rgba(35, 119, 90, 0.25) !important;
    color: var(--color-success) !important;
    border-radius: 10px;
}
[data-testid="stAlert"][kind="error"] {
    background-color: var(--color-danger-a08) !important;
    border-color: rgba(184, 50, 69, 0.25) !important;
    border-radius: 10px;
}

/* ===== SCREEN READER ONLY ===== */
.sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
}

/* ===== REDUCED MOTION ===== */
@media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
        scroll-behavior: auto !important;
    }
    .stButton > button { transition: none !important; }
}
</style>
"""

    @staticmethod
    def get_css() -> str:
        """Get the main CSS styles."""
        return Styles.MAIN_CSS

    @staticmethod
    def maccs_badge(key_number: int, active: bool = True) -> str:
        """Create a MACCS key badge."""
        if active:
            bg, color = "var(--color-accent)", "var(--color-card)"
        else:
            bg, color = "var(--color-surface-deep)", "var(--color-text-muted)"
        border = "" if active else "border:1px solid var(--color-border);"
        return (
            f'<span style="background:{bg};color:{color};padding:2px 6px;'
            f"border-radius:4px;font-family:var(--font-main);font-size:var(--text-md);"
            f"font-weight:var(--weight-medium);line-height:var(--lh-tight);"
            f'{border}margin:2px;display:inline-block;">{key_number}</span>'
        )

    @staticmethod
    def descriptor_value(value: float, unit: str = "") -> str:
        """Format a descriptor value for display."""
        unit_str = f" {unit}" if unit else ""
        return (
            f'<span style="font-size:var(--text-xl);font-weight:var(--weight-bold);'
            f"font-variant-numeric:tabular-nums;letter-spacing:var(--ls-tight);"
            f'color:var(--color-accent);">'
            f"{value:.4f}{unit_str}</span>"
        )
