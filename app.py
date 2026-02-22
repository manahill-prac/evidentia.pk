"""
app.py — CourtReady AI
=======================
PURPOSE  : Main Streamlit application. Connects all 4 modules into a
           complete, working, demo-ready application.

MODULES USED:
    seal.py          → seal_evidence(), verify_hash()
    vision.py        → analyze_image()
    rag.py           → generate_fir()
    pdf_generator.py → create_pdf(), get_download_filename()

RUN LOCALLY:
    streamlit run app.py

DEPLOY ON HF SPACES:
    1. Push all files to GitHub
    2. Create HF Space (SDK: Streamlit)
    3. Add Secrets: GROQ_API_KEY, SUPABASE_URL, SUPABASE_KEY
    4. Link repo → auto-deploys
"""

import streamlit as st
import datetime
import json
import time
import os
from PIL import Image
import io

# ── Import team modules ──────────────────────────
from seal           import seal_evidence, verify_hash
from vision         import analyze_image
from rag            import generate_fir
from pdf_generator  import create_pdf, get_download_filename


# ═══════════════════════════════════════════════════
# PAGE CONFIG & GLOBAL STYLES
# ═══════════════════════════════════════════════════

st.set_page_config(
    page_title="CourtReady AI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
/* ── Google Font ── */
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Mono:wght@400;500&family=Fraunces:ital,opsz,wght@0,9..144,300;1,9..144,300&display=swap');

/* ── Root palette ── */
:root {
    --bg:       #0b0f1a;
    --surface:  #111827;
    --border:   #1f2937;
    --accent:   #dc2626;
    --blue:     #3b82f6;
    --green:    #22c55e;
    --yellow:   #f59e0b;
    --text:     #f1f5f9;
    --muted:    #64748b;
}

/* ── Global ── */
html, body, [class*="css"] {
    background-color: #0b0f1a !important;
    color: #f1f5f9 !important;
    font-family: 'DM Mono', monospace !important;
}

.stApp { background-color: #0b0f1a !important; }

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem !important; max-width: 1100px !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #111827;
    border-bottom: 1px solid #1f2937;
    gap: 0;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #64748b !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 11px !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    padding: 12px 20px !important;
    border-bottom: 2px solid transparent !important;
}
.stTabs [aria-selected="true"] {
    color: #dc2626 !important;
    border-bottom: 2px solid #dc2626 !important;
    background: transparent !important;
}
.stTabs [data-baseweb="tab-panel"] { background: transparent !important; padding-top: 24px !important; }

/* ── Buttons ── */
.stButton > button {
    background: #dc2626 !important;
    color: white !important;
    border: none !important;
    border-radius: 0 !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 12px !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    padding: 12px 28px !important;
    width: 100% !important;
    font-weight: 500 !important;
    transition: background 0.2s !important;
}
.stButton > button:hover { background: #b91c1c !important; }

/* ── Download button ── */
.stDownloadButton > button {
    background: #16a34a !important;
    color: white !important;
    border: none !important;
    border-radius: 0 !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 12px !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    padding: 12px 28px !important;
    width: 100% !important;
}
.stDownloadButton > button:hover { background: #15803d !important; }

/* ── File uploader ── */
[data-testid="stFileUploaderDropzone"] {
    background: #111827 !important;
    border: 1px dashed #1f2937 !important;
    border-radius: 0 !important;
}
[data-testid="stFileUploaderDropzone"]:hover { border-color: #dc2626 !important; }

/* ── Text inputs ── */
.stTextInput > div > div > input {
    background: #111827 !important;
    border: 1px solid #1f2937 !important;
    border-radius: 0 !important;
    color: #f1f5f9 !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 12px !important;
}
.stTextInput > div > div > input:focus { border-color: #dc2626 !important; box-shadow: none !important; }

/* ── Success / Error / Warning ── */
.stSuccess { background: rgba(34,197,94,.1) !important; border-left: 3px solid #22c55e !important; border-radius: 0 !important; }
.stError   { background: rgba(220,38,38,.1) !important; border-left: 3px solid #dc2626 !important; border-radius: 0 !important; }
.stWarning { background: rgba(245,158,11,.1) !important; border-left: 3px solid #f59e0b !important; border-radius: 0 !important; }
.stInfo    { background: rgba(59,130,246,.1) !important; border-left: 3px solid #3b82f6 !important; border-radius: 0 !important; }

/* ── Metrics ── */
[data-testid="metric-container"] {
    background: #111827 !important;
    border: 1px solid #1f2937 !important;
    border-radius: 0 !important;
    padding: 16px !important;
}
[data-testid="metric-container"] label { color: #64748b !important; font-size: 10px !important; letter-spacing: 2px !important; text-transform: uppercase !important; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { color: #f1f5f9 !important; font-size: 20px !important; }

/* ── Expander ── */
.streamlit-expanderHeader {
    background: #111827 !important;
    border: 1px solid #1f2937 !important;
    border-radius: 0 !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 11px !important;
    letter-spacing: 1px !important;
}
.streamlit-expanderContent { background: #0f172a !important; border: 1px solid #1f2937 !important; border-top: none !important; }

/* ── Spinner ── */
.stSpinner > div { border-top-color: #dc2626 !important; }

/* ── Code blocks ── */
code { background: #1f2937 !important; color: #f97316 !important; border-radius: 0 !important; }

/* ── Dividers ── */
hr { border-color: #1f2937 !important; }

/* ── Custom classes ── */
.verdict-ok   { background:rgba(34,197,94,.08); border:1px solid rgba(34,197,94,.3); border-left:4px solid #22c55e; padding:16px 20px; }
.verdict-tamper { background:rgba(220,38,38,.08); border:1px solid rgba(220,38,38,.3); border-left:4px solid #dc2626; padding:16px 20px; }
.verdict-unknown { background:rgba(245,158,11,.08); border:1px solid rgba(245,158,11,.3); border-left:4px solid #f59e0b; padding:16px 20px; }

.info-card  { background:#111827; border:1px solid #1f2937; padding:16px 20px; margin-bottom:12px; }
.seal-card  { background:#0f172a; border:1px solid #1f2937; border-left:3px solid #3b82f6; padding:16px 20px; }
.hash-block { background:#0a0d14; border:1px solid #1f2937; padding:12px 16px; font-family:'DM Mono',monospace; font-size:11px; color:#f97316; word-break:break-all; }
.step-badge { display:inline-block; background:#dc2626; color:white; font-family:'Bebas Neue',sans-serif; font-size:18px; width:28px; height:28px; text-align:center; line-height:28px; margin-right:8px; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════

def render_header():
    st.markdown("""
    <div style="background:#111827; border-bottom:1px solid #1f2937; padding:20px 0 16px; margin-bottom:28px;">
        <div style="display:flex; align-items:center; gap:16px; flex-wrap:wrap;">
            <span style="font-size:36px;">⚖️</span>
            <div>
                <div style="font-family:'Bebas Neue',sans-serif; font-size:clamp(28px,5vw,44px);
                            line-height:0.95; letter-spacing:1px; color:#f1f5f9;">
                    COURTREADY <span style="color:#dc2626;">AI</span>
                </div>
                <div style="font-family:'Fraunces',serif; font-style:italic; font-size:13px;
                            color:#64748b; margin-top:4px;">
                    Seal. Analyze. Verify. Evidence you can trust.
                </div>
            </div>
            <div style="margin-left:auto; display:flex; gap:8px; flex-wrap:wrap;">
                <span style="background:rgba(34,197,94,.1); border:1px solid rgba(34,197,94,.3);
                            color:#22c55e; font-size:10px; letter-spacing:1.5px;
                            text-transform:uppercase; padding:4px 10px;">
                    ✓ SHA-256 Sealed
                </span>
                <span style="background:rgba(59,130,246,.1); border:1px solid rgba(59,130,246,.3);
                            color:#60a5fa; font-size:10px; letter-spacing:1.5px;
                            text-transform:uppercase; padding:4px 10px;">
                    ✓ AI Powered
                </span>
                <span style="background:rgba(220,38,38,.1); border:1px solid rgba(220,38,38,.3);
                            color:#f87171; font-size:10px; letter-spacing:1.5px;
                            text-transform:uppercase; padding:4px 10px;">
                    ✓ FIR Ready
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════
# SESSION STATE INIT
# ═══════════════════════════════════════════════════

def init_session():
    defaults = {
        "seal_data"   : None,
        "vision_data" : None,
        "fir_text"    : None,
        "pdf_bytes"   : None,
        "processing"  : False,
        "step"        : 0,        # 0=idle, 1=sealed, 2=analyzed, 3=fir_done, 4=pdf_done
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ═══════════════════════════════════════════════════
# TAB 1 — SUBMIT EVIDENCE
# ═══════════════════════════════════════════════════

def tab_submit():
    st.markdown("""
    <div style="font-size:10px; letter-spacing:3px; text-transform:uppercase;
                color:#64748b; margin-bottom:16px;">
        SUBMIT EVIDENCE — Upload or capture · Seal cryptographically · Generate legal documents
    </div>
    """, unsafe_allow_html=True)

    # ── HOW IT WORKS ────────────────────────────────
    with st.expander("ℹ  How CourtReady AI works — read before uploading", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        steps = [
            ("1", "UPLOAD", "Upload your photo, video, or document as evidence."),
            ("2", "SEAL",   "System generates a SHA-256 cryptographic hash + timestamp immediately."),
            ("3", "ANALYZE","AI analyzes the content and describes the scene formally."),
            ("4", "GENERATE","FIR complaint drafted automatically in Urdu + English. Download PDF."),
        ]
        for col, (num, title, desc) in zip([col1, col2, col3, col4], steps):
            with col:
                st.markdown(f"""
                <div class="info-card">
                    <div style="font-family:'Bebas Neue',sans-serif; font-size:32px; color:#dc2626;">{num}</div>
                    <div style="font-size:11px; font-weight:600; letter-spacing:1px; color:#f1f5f9; margin-bottom:4px;">{title}</div>
                    <div style="font-size:11px; color:#64748b; line-height:1.6;">{desc}</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── UPLOAD SECTION ───────────────────────────────
    col_upload, col_meta = st.columns([3, 2], gap="large")

    with col_upload:
        st.markdown("""
        <div style="font-size:10px; letter-spacing:2px; text-transform:uppercase;
                    color:#64748b; margin-bottom:10px;">EVIDENCE FILE</div>
        """, unsafe_allow_html=True)

        uploaded_file = st.file_uploader(
            "Upload evidence (photo, video, PDF, document)",
            type=["jpg", "jpeg", "png", "webp", "mp4", "mov", "pdf"],
            label_visibility="collapsed"
        )

        if uploaded_file:
            # Preview for images
            if uploaded_file.type.startswith("image/"):
                img = Image.open(uploaded_file)
                st.image(img, caption=f"📎 {uploaded_file.name}", use_container_width=True)
                uploaded_file.seek(0)
            else:
                st.markdown(f"""
                <div class="info-card" style="text-align:center; padding:24px;">
                    <div style="font-size:32px; margin-bottom:8px;">📄</div>
                    <div style="color:#f1f5f9; font-size:13px;">{uploaded_file.name}</div>
                    <div style="color:#64748b; font-size:11px;">{uploaded_file.type} · {uploaded_file.size:,} bytes</div>
                </div>
                """, unsafe_allow_html=True)

    with col_meta:
        st.markdown("""
        <div style="font-size:10px; letter-spacing:2px; text-transform:uppercase;
                    color:#64748b; margin-bottom:10px;">EVIDENCE METADATA</div>
        """, unsafe_allow_html=True)

        # Capture timestamp — auto-set to NOW (key authenticity feature)
        capture_ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
        st.markdown(f"""
        <div class="seal-card" style="margin-bottom:12px;">
            <div style="font-size:9px; letter-spacing:2px; text-transform:uppercase;
                        color:#60a5fa; margin-bottom:6px;">CAPTURE TIMESTAMP</div>
            <div style="font-size:12px; color:#f1f5f9;">{capture_ts}</div>
            <div style="font-size:10px; color:#64748b; margin-top:4px;">
                Auto-set to NOW · UTC · Prevents backdating
            </div>
        </div>
        """, unsafe_allow_html=True)

        your_name = st.text_input(
            "Your name (optional — appears in legal document)",
            placeholder="e.g. Muhammad Ali or leave blank",
            label_visibility="visible"
        )

        incident_hint = st.selectbox(
            "Incident type (helps AI — optional)",
            ["Let AI decide", "Traffic accident", "Physical assault",
            "Theft / Snatching", "Property damage", "Harassment", "Other"],
            label_visibility="visible"
        )

        # GPS note
        st.markdown("""
        <div style="background:rgba(59,130,246,.06); border:1px solid rgba(59,130,246,.2);
                    padding:10px 12px; font-size:11px; color:#94a3b8; line-height:1.6; margin-top:8px;">
            📍 For best results, enable GPS on your device before uploading.
            Location metadata extracted automatically from photo EXIF if available.
        </div>
        """, unsafe_allow_html=True)

    # ── PROCESS BUTTON ───────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)

    if uploaded_file:
        if st.button("🔒  SEAL & ANALYZE EVIDENCE", type="primary"):
            file_bytes = uploaded_file.read()
            _run_pipeline(
                file_bytes       = file_bytes,
                file_name        = uploaded_file.name,
                file_type        = uploaded_file.type,
                capture_timestamp= capture_ts,
                submitted_by     = your_name.strip() or "anonymous"
            )
    else:
        st.markdown("""
        <div style="text-align:center; padding:20px; color:#64748b; font-size:12px;
                    border:1px dashed #1f2937; margin-top:8px;">
            ↑ Upload an evidence file above to begin
        </div>
        """, unsafe_allow_html=True)

    # ── RESULTS ─────────────────────────────────────
    if st.session_state.step >= 1:
        _render_results()


# ═══════════════════════════════════════════════════
# PIPELINE RUNNER
# ═══════════════════════════════════════════════════

def _run_pipeline(file_bytes, file_name, file_type, capture_timestamp, submitted_by):
    """Run all 4 modules sequentially with progress feedback."""

    progress = st.progress(0, text="Starting...")
    status   = st.empty()

    # ── STEP 1: SEAL ────────────────────────────────
    status.markdown("**🔒 Step 1/4** — Sealing evidence with SHA-256...")
    progress.progress(10, text="Sealing evidence...")

    try:
        seal_data = seal_evidence(
            file_bytes        = file_bytes,
            file_name         = file_name,
            file_type         = file_type.split("/")[-1],
            capture_timestamp = capture_timestamp,
            submitted_by      = submitted_by
        )
        st.session_state.seal_data = seal_data
        st.session_state.step = 1
    except Exception as e:
        st.error(f"❌ Seal failed: {e}")
        progress.empty(); status.empty()
        return

    progress.progress(25, text="Evidence sealed ✓")

    # ── STEP 2: VISION (images only) ─────────────────
    vision_data = None
    if file_type.startswith("image/"):
        status.markdown("**🔍 Step 2/4** — AI analyzing image content...")
        progress.progress(35, text="Analyzing image...")
        try:
            vision_data = analyze_image(file_bytes)
            st.session_state.vision_data = vision_data
            st.session_state.step = 2
        except Exception as e:
            st.warning(f"⚠ Vision analysis failed: {e}. Continuing with basic FIR.")
            vision_data = {
                "incident_type"            : "Unknown",
                "summary"                  : "Vision analysis unavailable.",
                "people_observed"          : [{"description": "Not analyzed", "visible_actions": "Not analyzed"}],
                "objects_observed"         : [],
                "visible_damage_or_injury" : "Not analyzed",
                "location_clues"           : "Not analyzed",
                "confidence_level"         : "Low"
            }
            st.session_state.vision_data = vision_data
    else:
        status.markdown("**🔍 Step 2/4** — Skipping vision (non-image file)...")
        vision_data = {
            "incident_type"            : "Unknown",
            "summary"                  : f"Non-image evidence file: {file_name}",
            "people_observed"          : [{"description": "N/A", "visible_actions": "N/A"}],
            "objects_observed"         : [file_name],
            "visible_damage_or_injury" : "Not applicable",
            "location_clues"           : "Not applicable",
            "confidence_level"         : "N/A"
        }
        st.session_state.vision_data = vision_data
        st.session_state.step = 2

    progress.progress(50, text="Image analyzed ✓")

    # ── STEP 3: FIR GENERATION ───────────────────────
    status.markdown("**📜 Step 3/4** — Generating FIR complaint via RAG...")
    progress.progress(60, text="Generating FIR draft...")

    try:
        fir_text = generate_fir(vision_data)
        st.session_state.fir_text = fir_text
        st.session_state.step = 3
    except Exception as e:
        fir_text = f"FIR generation failed: {e}\n\nPlease run data_builder.py to build the legal knowledge base."
        st.session_state.fir_text = fir_text
        st.warning(f"⚠ FIR generation issue: {e}")

    progress.progress(75, text="FIR generated ✓")

    # ── STEP 4: PDF ──────────────────────────────────
    status.markdown("**📄 Step 4/4** — Generating legal PDF document...")
    progress.progress(85, text="Building PDF...")

    try:
        pdf_bytes = create_pdf(
            seal_data = seal_data,
            vision_data = vision_data,
            fir_text  = fir_text
        )
        st.session_state.pdf_bytes = pdf_bytes
        st.session_state.step = 4
    except Exception as e:
        st.error(f"❌ PDF generation failed: {e}")

    progress.progress(100, text="Complete ✓")
    time.sleep(0.5)
    progress.empty()
    status.empty()
    st.success("✅ Evidence sealed, analyzed, and legal documents generated.")
    st.rerun()


# ═══════════════════════════════════════════════════
# RESULTS RENDERER
# ═══════════════════════════════════════════════════

def _render_results():
    """Render all results after pipeline completes."""

    seal_data   = st.session_state.seal_data
    vision_data = st.session_state.vision_data
    fir_text    = st.session_state.fir_text
    pdf_bytes   = st.session_state.pdf_bytes

    if not seal_data:
        return

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:10px; letter-spacing:3px; text-transform:uppercase;
                color:#64748b; margin-bottom:20px;">EVIDENCE RESULTS</div>
    """, unsafe_allow_html=True)

    # ── SEAL RESULT ──────────────────────────────────
    r1, r2, r3 = st.columns(3)
    with r1:
        st.metric("Evidence ID", seal_data.get("evidence_id", "—"))
    with r2:
        st.metric("Status", "🔒 SEALED")
    with r3:
        gap = seal_data.get("capture_seal_gap", {})
        flag_emoji = {"OK": "✅", "CAUTION": "⚠️", "UNKNOWN": "❓"}.get(gap.get("flag", "UNKNOWN"), "❓")
        st.metric("Authenticity", f"{flag_emoji} {gap.get('flag', 'UNKNOWN')}")

    # Hash display
    st.markdown(f"""
    <div style="margin:16px 0;">
        <div style="font-size:9px; letter-spacing:2px; text-transform:uppercase;
                    color:#64748b; margin-bottom:6px;">SHA-256 HASH</div>
        <div class="hash-block">{seal_data.get('hash', '—')}</div>
        <div style="font-size:10px; color:#64748b; margin-top:4px;">
            Sealed: {seal_data.get('seal_timestamp', '—')} UTC
        </div>
    </div>
    """, unsafe_allow_html=True)

    gap_info = seal_data.get("capture_seal_gap", {})
    if gap_info.get("flag") == "CAUTION":
        st.warning(f"⚠ {gap_info.get('message', '')}")
    elif gap_info.get("flag") == "OK":
        st.success(f"✓ {gap_info.get('message', '')}")

    # ── VISION RESULT ────────────────────────────────
    if vision_data and vision_data.get("incident_type") not in ("Unknown", "N/A"):
        st.markdown("<br>", unsafe_allow_html=True)

        v1, v2 = st.columns([1, 2])
        with v1:
            incident = vision_data.get("incident_type", "Unknown")
            conf     = vision_data.get("confidence_level", "Unknown")
            st.markdown(f"""
            <div class="info-card" style="text-align:center; padding:24px;">
                <div style="font-size:10px; letter-spacing:2px; text-transform:uppercase;
                            color:#64748b; margin-bottom:8px;">INCIDENT TYPE</div>
                <div style="font-family:'Bebas Neue',sans-serif; font-size:24px;
                            color:#dc2626; line-height:1.1;">{incident.upper()}</div>
                <div style="font-size:10px; color:#64748b; margin-top:6px;">Confidence: {conf}</div>
            </div>
            """, unsafe_allow_html=True)

        with v2:
            with st.expander("🔍 Full AI Scene Analysis", expanded=True):
                st.markdown(f"**Scene Summary:**  \n{vision_data.get('summary', '—')}")
                if vision_data.get("visible_damage_or_injury") not in ("Not clearly visible", "Not analyzed", "N/A"):
                    st.markdown(f"**Damage/Injury:**  \n{vision_data.get('visible_damage_or_injury')}")
                if vision_data.get("location_clues") not in ("Not clearly visible", "Not analyzed", "N/A"):
                    st.markdown(f"**Location Clues:**  \n{vision_data.get('location_clues')}")
                people = vision_data.get("people_observed", [])
                if people and people[0].get("description") not in ("Not clearly visible", "Not analyzed", "N/A"):
                    st.markdown("**Persons Observed:**")
                    for i, p in enumerate(people, 1):
                        st.markdown(f"- Person {i}: {p.get('description')}. Actions: {p.get('visible_actions')}")

    # ── FIR RESULT ───────────────────────────────────
    if fir_text:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("📜 Generated FIR Complaint Draft", expanded=True):
            st.markdown("""
            <div style="background:rgba(245,158,11,.06); border:1px solid rgba(245,158,11,.2);
                        padding:10px 14px; font-size:11px; color:#d97706; margin-bottom:12px;">
                ⚠ AI-generated draft. Review with a qualified lawyer before filing.
            </div>
            """, unsafe_allow_html=True)
            st.markdown(fir_text)

    # ── PDF DOWNLOAD ─────────────────────────────────
    if pdf_bytes:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size:10px; letter-spacing:2px; text-transform:uppercase;
                    color:#64748b; margin-bottom:10px;">LEGAL DOCUMENT</div>
        """, unsafe_allow_html=True)

        filename = get_download_filename(seal_data)
        st.download_button(
            label    = "📄  DOWNLOAD OFFICIAL LEGAL PDF",
            data     = pdf_bytes,
            file_name= filename,
            mime     = "application/pdf"
        )
        st.markdown("""
        <div style="font-size:11px; color:#64748b; margin-top:8px;">
            PDF contains: Evidence ID · SHA-256 hash · Seal timestamp · AI scene analysis ·
            FIR draft (English + Urdu) · QR verification code
        </div>
        """, unsafe_allow_html=True)

    # ── RESET ────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄  SEAL NEW EVIDENCE"):
        for k in ["seal_data", "vision_data", "fir_text", "pdf_bytes", "step"]:
            st.session_state[k] = None if k != "step" else 0
        st.rerun()


# ═══════════════════════════════════════════════════
# TAB 2 — VERIFY EVIDENCE
# ═══════════════════════════════════════════════════

def tab_verify():
    st.markdown("""
    <div style="font-size:10px; letter-spacing:3px; text-transform:uppercase;
                color:#64748b; margin-bottom:20px;">
        VERIFY EVIDENCE — Upload a file + enter Evidence ID to check if it has been tampered with
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="info-card" style="margin-bottom:24px;">
        <div style="font-size:12px; color:#94a3b8; line-height:1.8;">
            This portal allows <strong style="color:#f1f5f9;">any person</strong> — a lawyer,
            judge, journalist, or police officer — to verify whether an evidence file has been
            modified since it was sealed by CourtReady AI. Upload the file and enter its
            Evidence ID. The system re-computes the SHA-256 hash and compares it to the
            original sealed record in milliseconds.
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_v1, col_v2 = st.columns([2, 1], gap="large")

    with col_v1:
        evidence_id = st.text_input(
            "Evidence ID",
            placeholder="CR-XXXXXXXX-XXXXXXXX",
            help="The Evidence ID issued when the file was originally sealed"
        )

        verify_file = st.file_uploader(
            "Upload file to verify",
            type=["jpg", "jpeg", "png", "webp", "mp4", "mov", "pdf"],
            key="verify_uploader",
            label_visibility="collapsed"
        )

        if verify_file:
            st.markdown(f"""
            <div class="info-card">
                📎 {verify_file.name} · {verify_file.size:,} bytes
            </div>
            """, unsafe_allow_html=True)

    with col_v2:
        st.markdown("""
        <div class="info-card">
            <div style="font-size:10px; letter-spacing:2px; text-transform:uppercase;
                        color:#64748b; margin-bottom:10px;">HOW VERIFICATION WORKS</div>
            <div style="font-size:11px; color:#94a3b8; line-height:1.8;">
                1. Upload the file<br>
                2. Enter its Evidence ID<br>
                3. System re-hashes the file<br>
                4. Compares to stored record<br>
                5. Shows: Original or Tampered
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if evidence_id and verify_file:
        if st.button("🔍  VERIFY EVIDENCE INTEGRITY"):
            with st.spinner("Verifying hash against sealed record..."):
                file_bytes = verify_file.read()
                result     = verify_hash(evidence_id.strip(), file_bytes)

            _render_verdict(result)

    elif not evidence_id and not verify_file:
        st.markdown("""
        <div style="text-align:center; padding:40px; color:#64748b; font-size:12px;
                    border:1px dashed #1f2937;">
            Enter Evidence ID and upload the file above to verify
        </div>
        """, unsafe_allow_html=True)


def _render_verdict(result: dict):
    """Render tamper verification result."""

    verdict = result.get("verdict", "ERROR")
    st.markdown("<br>", unsafe_allow_html=True)

    if verdict == "VERIFIED_ORIGINAL":
        st.markdown(f"""
        <div class="verdict-ok">
            <div style="font-family:'Bebas Neue',sans-serif; font-size:28px;
                        color:#22c55e; margin-bottom:8px;">
                ✓ VERIFIED ORIGINAL
            </div>
            <div style="font-size:13px; color:#86efac; line-height:1.8;">
                {result.get("message", "")}
            </div>
        </div>
        """, unsafe_allow_html=True)

    elif verdict == "TAMPERED":
        st.markdown(f"""
        <div class="verdict-tamper">
            <div style="font-family:'Bebas Neue',sans-serif; font-size:28px;
                        color:#dc2626; margin-bottom:8px;">
                ✗ TAMPER DETECTED
            </div>
            <div style="font-size:13px; color:#fca5a5; line-height:1.8;">
                {result.get("message", "")}
            </div>
        </div>
        """, unsafe_allow_html=True)

    elif verdict == "NOT_FOUND":
        st.markdown(f"""
        <div class="verdict-unknown">
            <div style="font-family:'Bebas Neue',sans-serif; font-size:28px;
                        color:#f59e0b; margin-bottom:8px;">
                ? EVIDENCE ID NOT FOUND
            </div>
            <div style="font-size:13px; color:#fde68a; line-height:1.8;">
                {result.get("message", "")}
            </div>
        </div>
        """, unsafe_allow_html=True)

    else:
        st.error(f"Verification error: {result.get('message', 'Unknown error')}")
        return

    # Technical details
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("🔬 Technical Verification Details", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Evidence ID:** `{result.get('evidence_id', '—')}`")
            st.markdown(f"**Sealed On:** {result.get('seal_timestamp', '—')}")
            st.markdown(f"**Capture Time:** {result.get('capture_timestamp', '—')}")
            st.markdown(f"**Gap Flag:** {result.get('gap_flag', '—')}")
        with col2:
            st.markdown(f"**Stored Hash:**")
            st.code(result.get("stored_hash", "—"), language="text")
            st.markdown(f"**Submitted Hash:**")
            st.code(result.get("submitted_hash", "—"), language="text")
            st.markdown(f"**Verified At:** {result.get('verified_at', '—')}")


# ═══════════════════════════════════════════════════
# TAB 3 — HOW IT WORKS
# ═══════════════════════════════════════════════════

def tab_about():
    st.markdown("""
    <div style="font-size:10px; letter-spacing:3px; text-transform:uppercase;
                color:#64748b; margin-bottom:20px;">ABOUT COURTREADY AI</div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([3, 2], gap="large")

    with col1:
        st.markdown("""
        <div class="info-card" style="margin-bottom:16px;">
            <div style="font-size:10px; letter-spacing:2px; text-transform:uppercase;
                        color:#dc2626; margin-bottom:10px;">THE PROBLEM</div>
            <div style="font-size:13px; color:#94a3b8; line-height:1.9;">
                Every day in Pakistan, citizens capture evidence of crimes, accidents, and
                harassment on their phones — but that evidence is legally worthless by the
                time it reaches a police station. WhatsApp compresses files and strips metadata.
                Screenshots can be faked. There is no chain of custody for citizen digital evidence.
                <br><br>
                Cases collapse — not because the truth was not captured, but because it cannot
                be <strong style="color:#f1f5f9;">proven unaltered</strong>.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="info-card" style="margin-bottom:16px;">
            <div style="font-size:10px; letter-spacing:2px; text-transform:uppercase;
                        color:#3b82f6; margin-bottom:10px;">HOW COURTREADY AI SOLVES IT</div>
            <div style="font-size:12px; color:#94a3b8; line-height:1.9;">
                <strong style="color:#f1f5f9;">1. Cryptographic Seal</strong> — SHA-256 hash generated from raw file bytes the
                moment of upload. Mathematically proves file integrity.<br><br>
                <strong style="color:#f1f5f9;">2. AI Witness Analysis</strong> — Groq Llama 3.2 Vision analyzes the evidence
                as a neutral forensic observer, producing a formal scene description.<br><br>
                <strong style="color:#f1f5f9;">3. RAG Legal Generator</strong> — LangChain + FAISS retrieves relevant Pakistan
                Penal Code sections and auto-generates a bilingual FIR complaint.<br><br>
                <strong style="color:#f1f5f9;">4. Tamper Verification</strong> — Anyone can upload a file and verify in
                seconds if it matches the original sealed evidence.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="info-card" style="margin-bottom:16px;">
            <div style="font-size:10px; letter-spacing:2px; text-transform:uppercase;
                        color:#22c55e; margin-bottom:12px;">TECH STACK</div>
        """, unsafe_allow_html=True)

        stack = [
            ("UI",          "Streamlit"),
            ("LLM",         "Groq Llama 3.1 70B"),
            ("Vision",      "Groq Llama 3.2 Vision"),
            ("RAG",         "LangChain + FAISS"),
            ("Embeddings",  "sentence-transformers"),
            ("Hashing",     "Python hashlib SHA-256"),
            ("Database",    "Supabase"),
            ("PDF",         "ReportLab"),
            ("Deployment",  "Hugging Face Spaces"),
        ]
        for layer, tool in stack:
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; padding:8px 0;
                        border-bottom:1px solid #1f2937; font-size:11px;">
                <span style="color:#64748b; text-transform:uppercase; letter-spacing:1px;">{layer}</span>
                <span style="color:#f1f5f9;">{tool}</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("""
        <div class="info-card" style="margin-top:16px;">
            <div style="font-size:10px; letter-spacing:2px; text-transform:uppercase;
                        color:#64748b; margin-bottom:8px;">COST TO USER</div>
            <div style="font-family:'Bebas Neue',sans-serif; font-size:36px; color:#22c55e;">PKR 0.00</div>
            <div style="font-size:11px; color:#64748b; margin-top:4px;">
                Free for all Pakistani citizens.<br>All AI APIs on free tier.
            </div>
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════

def main():
    init_session()
    render_header()

    tab1, tab2, tab3 = st.tabs([
        "📸  Submit Evidence",
        "🔍  Verify Evidence",
        "ℹ   About"
    ])

    with tab1:
        tab_submit()

    with tab2:
        tab_verify()

    with tab3:
        tab_about()


if __name__ == "__main__":
    main()

