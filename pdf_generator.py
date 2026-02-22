"""
pdf_generator.py — CourtReady AI
==================================
ROLE     : PDF Engineer
ENGINEER : [Your Name]
PURPOSE  : Generate a professional, court-ready legal PDF document combining
           seal data, vision analysis, and FIR draft text.

DESIGN PHILOSOPHY:
  - The PDF must look OFFICIAL and TRUSTWORTHY. A lawyer or judge receiving
    this document should immediately recognise it as structured, serious output.
  - Clear visual hierarchy: header → metadata → AI analysis → legal draft → footer
  - Bilingual: English primary, Urdu secondary where applicable
  - QR code links to online verification portal (so anyone can verify instantly)
  - Every section is clearly labelled with its data source (AI / System / User)
"""

import io
import datetime
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, Image as RLImage
)
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from typing import Optional


# =============================
# COLOUR PALETTE
# =============================

DARK_NAVY   = colors.HexColor("#0D1B2A")
ACCENT_RED  = colors.HexColor("#C0392B")
MID_BLUE    = colors.HexColor("#1A5276")
LIGHT_BLUE  = colors.HexColor("#D6EAF8")
LIGHT_GREY  = colors.HexColor("#F4F6F7")
MED_GREY    = colors.HexColor("#BDC3C7")
TEXT_DARK   = colors.HexColor("#1A1A2E")
TEXT_MID    = colors.HexColor("#4A4A6A")
GREEN_OK    = colors.HexColor("#1E8449")
RED_WARN    = colors.HexColor("#C0392B")
GOLD        = colors.HexColor("#D4AC0D")
WHITE       = colors.white

PAGE_W, PAGE_H = A4    # 595.27 x 841.89 points
MARGIN        = 18 * mm
CONTENT_W     = PAGE_W - 2 * MARGIN


# =============================
# FONTS
# =============================

def _register_fonts():
    """
    Register fonts. Falls back to Helvetica if custom fonts not available.
    For production: place NotoSansUrdu-Regular.ttf in same directory.
    """
    try:
        pdfmetrics.registerFont(TTFont("NotoUrdu", "NotoNastaliqUrdu-Regular.ttf"))
        return True
    except Exception:
        return False


# =============================
# QR CODE GENERATOR
# =============================

def _generate_qr_image(evidence_id: str, base_url: str = "https://courtready.ai/verify") -> io.BytesIO:
    """
    Generates a QR code that links to the online verification portal.
    Anyone scanning this can instantly verify the evidence online.
    """
    verify_url = f"{base_url}?id={evidence_id}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=4,
        border=2
    )
    qr.add_data(verify_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0D1B2A", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


# =============================
# STYLE DEFINITIONS
# =============================

def _build_styles() -> dict:
    base = getSampleStyleSheet()

    styles = {

        "doc_title": ParagraphStyle(
            "doc_title",
            fontName="Helvetica-Bold",
            fontSize=18,
            textColor=WHITE,
            alignment=TA_CENTER,
            spaceAfter=2
        ),

        "doc_subtitle": ParagraphStyle(
            "doc_subtitle",
            fontName="Helvetica-Oblique",
            fontSize=10,
            textColor=colors.HexColor("#AED6F1"),
            alignment=TA_CENTER,
            spaceAfter=2
        ),

        "section_header": ParagraphStyle(
            "section_header",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=WHITE,
            alignment=TA_LEFT,
            spaceBefore=2,
            spaceAfter=2,
            leftIndent=4
        ),

        "field_label": ParagraphStyle(
            "field_label",
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=TEXT_MID,
            alignment=TA_LEFT,
            spaceAfter=1
        ),

        "field_value": ParagraphStyle(
            "field_value",
            fontName="Helvetica",
            fontSize=9,
            textColor=TEXT_DARK,
            alignment=TA_LEFT,
            spaceAfter=4,
            leading=13
        ),

        "mono": ParagraphStyle(
            "mono",
            fontName="Courier",
            fontSize=8,
            textColor=TEXT_DARK,
            alignment=TA_LEFT,
            backColor=LIGHT_GREY,
            borderPadding=(4, 6, 4, 6)
        ),

        "body": ParagraphStyle(
            "body",
            fontName="Helvetica",
            fontSize=9,
            textColor=TEXT_DARK,
            alignment=TA_JUSTIFY,
            leading=14,
            spaceAfter=6
        ),

        "fir_text": ParagraphStyle(
            "fir_text",
            fontName="Helvetica",
            fontSize=9,
            textColor=TEXT_DARK,
            alignment=TA_JUSTIFY,
            leading=15,
            spaceAfter=8,
            leftIndent=6,
            rightIndent=6
        ),

        "caption": ParagraphStyle(
            "caption",
            fontName="Helvetica-Oblique",
            fontSize=7,
            textColor=TEXT_MID,
            alignment=TA_CENTER
        ),

        "verdict_ok": ParagraphStyle(
            "verdict_ok",
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=GREEN_OK,
            alignment=TA_CENTER
        ),

        "verdict_warn": ParagraphStyle(
            "verdict_warn",
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=RED_WARN,
            alignment=TA_CENTER
        ),

        "footer_text": ParagraphStyle(
            "footer_text",
            fontName="Helvetica",
            fontSize=7,
            textColor=MED_GREY,
            alignment=TA_CENTER
        ),

        "disclaimer": ParagraphStyle(
            "disclaimer",
            fontName="Helvetica-Oblique",
            fontSize=7.5,
            textColor=TEXT_MID,
            alignment=TA_JUSTIFY,
            leading=11,
            leftIndent=6,
            rightIndent=6
        )
    }

    return styles


# =============================
# REUSABLE COMPONENTS
# =============================

def _section_banner(title: str, styles: dict, color=None) -> Table:
    """Dark-coloured section header banner."""
    bg = color or DARK_NAVY
    tbl = Table(
        [[Paragraph(f"  {title}", styles["section_header"])]],
        colWidths=[CONTENT_W]
    )
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [bg]),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    return tbl


def _field_row(label: str, value: str, styles: dict, highlight=False) -> Table:
    """Two-column label + value row."""
    bg = colors.HexColor("#FEF9E7") if highlight else WHITE
    tbl = Table(
        [[
            Paragraph(label, styles["field_label"]),
            Paragraph(str(value), styles["field_value"])
        ]],
        colWidths=[CONTENT_W * 0.28, CONTENT_W * 0.72]
    )
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), bg),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("LINEBELOW",     (0, 0), (-1, -1), 0.3, MED_GREY),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    return tbl


def _gap_flag_color(flag: str) -> colors.Color:
    return {
        "OK":      GREEN_OK,
        "CAUTION": colors.HexColor("#E67E22"),
        "UNKNOWN": MED_GREY
    }.get(flag, MED_GREY)


def _gap_flag_label(flag: str) -> str:
    return {
        "OK":      "✓ STRONG AUTHENTICITY — Sealed within minutes of capture",
        "CAUTION": "⚠ CAUTION — Significant gap between capture and seal",
        "UNKNOWN": "? UNKNOWN — No capture timestamp available"
    }.get(flag, "? UNKNOWN")


# =============================
# NUMBERED PAGE CANVAS
# =============================

class _NumberedCanvas(canvas.Canvas):
    """Adds page numbers and a persistent footer to every page."""

    def __init__(self, *args, evidence_id="", **kwargs):
        super().__init__(*args, **kwargs)
        self._pages = []
        self._evidence_id = evidence_id

    def showPage(self):
        self._pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._pages)
        for page in self._pages:
            self.__dict__.update(page)
            self._draw_footer(self._pageNumber, total)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def _draw_footer(self, page_num: int, total: int):
        self.saveState()

        # Footer line
        self.setStrokeColor(MED_GREY)
        self.setLineWidth(0.4)
        self.line(MARGIN, 12 * mm, PAGE_W - MARGIN, 12 * mm)

        # Left: Evidence ID
        self.setFont("Helvetica", 7)
        self.setFillColor(TEXT_MID)
        self.drawString(MARGIN, 9 * mm, f"Evidence ID: {self._evidence_id}")

        # Center: Confidential
        self.drawCentredString(PAGE_W / 2, 9 * mm, "COURTREADY AI — OFFICIAL EVIDENCE DOCUMENT — CONFIDENTIAL")

        # Right: Page number
        self.drawRightString(PAGE_W - MARGIN, 9 * mm, f"Page {page_num} of {total}")

        self.restoreState()


# =============================
# PUBLIC API
# =============================

def create_pdf(
    seal_data: dict,
    vision_data: dict,
    fir_text: str,
    verification_base_url: str = "https://courtready.ai/verify"
) -> bytes:
    """
    Generates a professional, court-ready PDF combining all evidence data.

    Args:
        seal_data   : Output from seal.seal_evidence() — contains hash, timestamps, Evidence ID
        vision_data : Output from vision.analyze_image() — contains scene analysis JSON
        fir_text    : Generated FIR complaint text (from rag_pipeline or fir_generator)
        verification_base_url: Base URL for QR code verification link

    Returns:
        bytes: Complete PDF file as bytes (ready for st.download_button)
    """

    _register_fonts()
    styles = _build_styles()

    buffer = io.BytesIO()
    evidence_id = seal_data.get("evidence_id", "UNKNOWN")

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=18 * mm,
        bottomMargin=22 * mm,
        title=f"CourtReady AI — Evidence Document {evidence_id}",
        author="CourtReady AI",
        subject="Digital Evidence Legal Document",
        creator="CourtReady AI — Generative AI Evidence Platform"
    )

    story = []

    # ══════════════════════════════════════════
    # HEADER BLOCK
    # ══════════════════════════════════════════
    header_table = Table(
        [[
            Paragraph("⚖", ParagraphStyle("icon", fontName="Helvetica-Bold", fontSize=28, textColor=GOLD, alignment=TA_CENTER)),
            Table([
                [Paragraph("COURTREADY AI", styles["doc_title"])],
                [Paragraph("AI-Powered Citizen Evidence & Legal Document Platform", styles["doc_subtitle"])],
                [Paragraph("OFFICIAL DIGITAL EVIDENCE DOCUMENT", ParagraphStyle(
                    "badge", fontName="Helvetica-Bold", fontSize=8,
                    textColor=GOLD, alignment=TA_CENTER))],
            ], colWidths=[CONTENT_W - 30 * mm]),
        ]],
        colWidths=[28 * mm, CONTENT_W - 28 * mm]
    )
    header_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), DARK_NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 8 * mm))

    # ══════════════════════════════════════════
    # SECTION 1 — EVIDENCE IDENTIFICATION
    # ══════════════════════════════════════════
    story.append(KeepTogether([
        _section_banner("SECTION 1 — EVIDENCE IDENTIFICATION", styles, DARK_NAVY),
        _field_row("Evidence ID",       evidence_id, styles, highlight=True),
        _field_row("Status",            "🔒 SEALED — CRYPTOGRAPHICALLY PROTECTED", styles),
        _field_row("File Name",         seal_data.get("file_name", "Not provided"), styles),
        _field_row("File Type",         seal_data.get("file_type", "Not provided").upper(), styles),
        _field_row("File Size",         f"{seal_data.get('file_size_bytes', 0):,} bytes", styles),
        _field_row("Submitted By",      seal_data.get("submitted_by", "Anonymous"), styles),
    ]))
    story.append(Spacer(1, 4 * mm))

    # ══════════════════════════════════════════
    # SECTION 2 — CRYPTOGRAPHIC SEAL
    # ══════════════════════════════════════════
    gap_info = seal_data.get("capture_seal_gap", {})
    gap_flag = gap_info.get("flag", "UNKNOWN")

    story.append(KeepTogether([
        _section_banner("SECTION 2 — CRYPTOGRAPHIC SEAL & TIMESTAMP INTEGRITY", styles, MID_BLUE),
        _field_row("SHA-256 Hash",        seal_data.get("hash", "Not available"), styles),
        _field_row("Seal Timestamp",      seal_data.get("seal_timestamp", "Not recorded") + "  (Server UTC)", styles),
        _field_row("Capture Timestamp",   seal_data.get("capture_timestamp", "Not provided") + "  (Device reported)", styles),
        _field_row("Time Gap Analysis",   f"{_gap_flag_label(gap_flag)}\n{gap_info.get('message', '')}", styles,
                   highlight=(gap_flag == "CAUTION")),
    ]))

    # Hash mono display
    hash_val = seal_data.get("hash", "")
    if hash_val:
        story.append(Spacer(1, 2 * mm))
        hash_tbl = Table(
            [[Paragraph(f"HASH: {hash_val}", styles["mono"])]],
            colWidths=[CONTENT_W]
        )
        hash_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), LIGHT_GREY),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("LINEABOVE",     (0, 0), (-1, -1), 1, MID_BLUE),
            ("LINEBELOW",     (0, 0), (-1, -1), 1, MID_BLUE),
        ]))
        story.append(hash_tbl)

    story.append(Spacer(1, 4 * mm))

    # ══════════════════════════════════════════
    # SECTION 3 — LOCATION DATA
    # ══════════════════════════════════════════
    loc = seal_data.get("location_metadata", {})
    if loc and (loc.get("lat") or loc.get("lon")):
        lat = loc.get("lat", "Not available")
        lon = loc.get("lon", "Not available")
        acc = loc.get("accuracy_meters", "Not available")
        story.append(KeepTogether([
            _section_banner("SECTION 3 — LOCATION METADATA", styles, colors.HexColor("#1A5276")),
            _field_row("Latitude",  str(lat), styles),
            _field_row("Longitude", str(lon), styles),
            _field_row("Accuracy",  f"±{acc} metres" if acc != "Not available" else "Not available", styles),
            _field_row("Note", "GPS coordinates extracted from device at time of capture. "
                               "Accuracy depends on device GPS hardware and signal conditions.", styles),
        ]))
        story.append(Spacer(1, 4 * mm))

    # ══════════════════════════════════════════
    # SECTION 4 — AI WITNESS ANALYSIS
    # ══════════════════════════════════════════
    story.append(_section_banner("SECTION 4 — AI WITNESS ANALYSIS  [Generated by Moondream Vision + Groq LLM]", styles, colors.HexColor("#4A235A")))

    # Incident type badge
    incident = vision_data.get("incident_type", "Unknown")
    confidence = vision_data.get("confidence_level", "Unknown")
    incident_tbl = Table(
        [[
            Paragraph(f"INCIDENT CLASSIFICATION: {incident.upper()}", ParagraphStyle(
                "inc", fontName="Helvetica-Bold", fontSize=10, textColor=WHITE, alignment=TA_CENTER)),
            Paragraph(f"Confidence: {confidence}", ParagraphStyle(
                "conf", fontName="Helvetica", fontSize=9, textColor=LIGHT_BLUE, alignment=TA_CENTER))
        ]],
        colWidths=[CONTENT_W * 0.65, CONTENT_W * 0.35]
    )
    incident_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), ACCENT_RED),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#6C3483")),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(incident_tbl)

    # Summary
    summary = vision_data.get("summary", "No summary available.")
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("<b>Scene Summary:</b>", styles["field_label"]))
    story.append(Paragraph(summary, styles["body"]))

    # People observed
    people = vision_data.get("people_observed", [])
    if people:
        story.append(Paragraph("<b>Persons Observed:</b>", styles["field_label"]))
        for i, person in enumerate(people, 1):
            desc    = person.get("description", "Not clearly visible")
            actions = person.get("visible_actions", "Not clearly visible")
            story.append(Paragraph(f"Person {i}: {desc}. Actions: {actions}", styles["body"]))

    # Objects observed
    objects = vision_data.get("objects_observed", [])
    if objects:
        obj_list = ", ".join(objects) if isinstance(objects, list) else str(objects)
        story.append(Paragraph("<b>Objects / Evidence Items Observed:</b>", styles["field_label"]))
        story.append(Paragraph(obj_list, styles["body"]))

    # Damage / Injury
    damage = vision_data.get("visible_damage_or_injury", "Not clearly visible")
    story.append(Paragraph("<b>Visible Damage or Injury:</b>", styles["field_label"]))
    story.append(Paragraph(damage, styles["body"]))

    # Location clues
    loc_clues = vision_data.get("location_clues", "Not clearly visible")
    story.append(Paragraph("<b>Location Clues from Image:</b>", styles["field_label"]))
    story.append(Paragraph(loc_clues, styles["body"]))

    story.append(Spacer(1, 4 * mm))

    # ══════════════════════════════════════════
    # SECTION 5 — FIR COMPLAINT DRAFT
    # ══════════════════════════════════════════
    story.append(_section_banner("SECTION 5 — FIR COMPLAINT DRAFT  [Generated via RAG over Pakistan Penal Code]", styles, ACCENT_RED))
    story.append(Spacer(1, 3 * mm))

    # FIR disclaimer box
    disclaimer_tbl = Table(
        [[Paragraph(
            "⚠  AI-GENERATED DRAFT. This FIR draft is prepared as a starting point only. "
            "It must be reviewed by a qualified legal professional before filing. "
            "CourtReady AI does not provide legal advice. All PPC section references "
            "should be verified with a lawyer or legal aid service.",
            styles["disclaimer"]
        )]],
        colWidths=[CONTENT_W]
    )
    disclaimer_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#FEF9E7")),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("LINEABOVE",     (0, 0), (-1, -1), 1.5, GOLD),
        ("LINEBELOW",     (0, 0), (-1, -1), 1.5, GOLD),
    ]))
    story.append(disclaimer_tbl)
    story.append(Spacer(1, 4 * mm))

    # FIR text — split on newlines for proper paragraph rendering
    if fir_text:
        for para in fir_text.split("\n"):
            para = para.strip()
            if para:
                story.append(Paragraph(para, styles["fir_text"]))
    else:
        story.append(Paragraph("FIR draft not generated. Please run the RAG pipeline.", styles["fir_text"]))

    story.append(Spacer(1, 6 * mm))

    # ══════════════════════════════════════════
    # SECTION 6 — VERIFICATION
    # ══════════════════════════════════════════
    qr_buffer = _generate_qr_image(evidence_id, verification_base_url)
    qr_img    = RLImage(qr_buffer, width=28 * mm, height=28 * mm)

    verify_url = f"{verification_base_url}?id={evidence_id}"

    verify_content = Table(
        [[
            qr_img,
            Table([
                [Paragraph("SCAN TO VERIFY THIS EVIDENCE", ParagraphStyle(
                    "vt", fontName="Helvetica-Bold", fontSize=9, textColor=DARK_NAVY))],
                [Paragraph(
                    f"Any lawyer, judge, or authorised party may verify whether "
                    f"this file has been tampered with by visiting the URL below "
                    f"and uploading the original file.",
                    styles["body"]
                )],
                [Paragraph(verify_url, styles["mono"])],
            ], colWidths=[CONTENT_W - 36 * mm]),
        ]],
        colWidths=[34 * mm, CONTENT_W - 34 * mm]
    )
    verify_content.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), LIGHT_BLUE),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LINEABOVE",     (0, 0), (-1, -1), 1.5, MID_BLUE),
        ("LINEBELOW",     (0, 0), (-1, -1), 1.5, MID_BLUE),
    ]))

    story.append(KeepTogether([
        _section_banner("SECTION 6 — ONLINE VERIFICATION", styles, GREEN_OK),
        Spacer(1, 2 * mm),
        verify_content,
    ]))

    story.append(Spacer(1, 6 * mm))

    # ══════════════════════════════════════════
    # FINAL DISCLAIMER
    # ══════════════════════════════════════════
    final_disclaimer = Table(
        [[Paragraph(
            "This document was automatically generated by CourtReady AI, a Generative AI platform "
            "for citizen digital evidence preservation. The cryptographic hash recorded in Section 2 "
            "provides mathematical proof of file integrity at the time of sealing. AI-generated analysis "
            "in Sections 4 and 5 is produced by large language models and must be reviewed by a qualified "
            "legal professional before use in formal legal proceedings. CourtReady AI is not a law firm "
            "and this document does not constitute legal advice.",
            styles["disclaimer"]
        )]],
        colWidths=[CONTENT_W]
    )
    final_disclaimer.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), LIGHT_GREY),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("LINEABOVE",     (0, 0), (-1, -1), 0.5, MED_GREY),
        ("LINEBELOW",     (0, 0), (-1, -1), 0.5, MED_GREY),
    ]))
    story.append(final_disclaimer)

    # ══════════════════════════════════════════
    # BUILD
    # ══════════════════════════════════════════
    def make_canvas(*args, **kwargs):
        return _NumberedCanvas(*args, evidence_id=evidence_id, **kwargs)

    doc.build(story, canvasmaker=make_canvas)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# =============================
# STREAMLIT INTEGRATION HELPER
# =============================

def get_download_filename(seal_data: dict) -> str:
    """Returns a clean filename for st.download_button."""
    ev_id = seal_data.get("evidence_id", "UNKNOWN").replace("-", "_")
    date  = datetime.datetime.utcnow().strftime("%Y%m%d")
    return f"CourtReadyAI_Evidence_{ev_id}_{date}.pdf"

