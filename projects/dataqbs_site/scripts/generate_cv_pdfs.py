#!/usr/bin/env python3
"""
generate_cv_pdfs.py — Generate CV PDFs in EN, ES, and DE from cv.ts data.

Reads structured data from src/data/cv.ts and src/data/certs.ts,
generates clean professional PDFs for each language.

Usage:
    python scripts/generate_cv_pdfs.py

Output:
    public/Profile.pdf      (English)
    public/Profile_ES.pdf   (Spanish)
    public/Profile_DE.pdf   (German)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, KeepTogether,
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:
    print("ERROR: 'reportlab' not installed. Run: pip install reportlab")
    sys.exit(1)

# ── Paths ──
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
CV_TS = PROJECT_DIR / "src" / "data" / "cv.ts"
CERTS_TS = PROJECT_DIR / "src" / "data" / "certs.ts"
OUTPUT_DIR = PROJECT_DIR / "public"

# ── Colors ──
PRIMARY = HexColor("#1e40af")  # Blue-800
DARK = HexColor("#1e293b")     # Slate-800
GRAY = HexColor("#64748b")     # Slate-500
LIGHT_GRAY = HexColor("#e2e8f0")  # Slate-200
ACCENT = HexColor("#0369a1")   # Sky-700

# ── Translations ──
TRANSLATIONS = {
    "en": {
        "title": "Professional Profile",
        "contact": "Contact",
        "summary": "Summary",
        "experience": "Experience",
        "education": "Education",
        "skills": "Skills",
        "certifications": "Certifications",
        "present": "Present",
        "remote": "Remote",
        "location": "Location",
        "achievements": "Key Achievements",
        "technologies": "Technologies",
        "languages": "Languages",
        "spanish": "Spanish (Native)",
        "english": "English (Professional Working)",
        "open_to_work": "Open to Work",
        "availability": "Availability: Remote Only (Worldwide)",
        "issued_by": "Issued by",
        "expired": "Expired",
        "active": "Active",
        "degree_in_process": "Degree in process",
        "generated": "Generated from dataqbs.com",
    },
    "es": {
        "title": "Perfil Profesional",
        "contact": "Contacto",
        "summary": "Resumen",
        "experience": "Experiencia",
        "education": "Educación",
        "skills": "Habilidades",
        "certifications": "Certificaciones",
        "present": "Actual",
        "remote": "Remoto",
        "location": "Ubicación",
        "achievements": "Logros Clave",
        "technologies": "Tecnologías",
        "languages": "Idiomas",
        "spanish": "Español (Nativo)",
        "english": "Inglés (Profesional)",
        "open_to_work": "Abierto a trabajar",
        "availability": "Disponibilidad: Solo Remoto (Mundial)",
        "issued_by": "Emitido por",
        "expired": "Expirado",
        "active": "Activo",
        "degree_in_process": "Título en proceso",
        "generated": "Generado desde dataqbs.com",
    },
    "de": {
        "title": "Berufliches Profil",
        "contact": "Kontakt",
        "summary": "Zusammenfassung",
        "experience": "Erfahrung",
        "education": "Ausbildung",
        "skills": "Fähigkeiten",
        "certifications": "Zertifizierungen",
        "present": "Aktuell",
        "remote": "Remote",
        "location": "Standort",
        "achievements": "Wichtige Erfolge",
        "technologies": "Technologien",
        "languages": "Sprachen",
        "spanish": "Spanisch (Muttersprache)",
        "english": "Englisch (Beruflich)",
        "open_to_work": "Offen für Arbeit",
        "availability": "Verfügbarkeit: Nur Remote (Weltweit)",
        "issued_by": "Ausgestellt von",
        "expired": "Abgelaufen",
        "active": "Aktiv",
        "degree_in_process": "Studium läuft",
        "generated": "Erstellt von dataqbs.com",
    },
}

# ── Summaries per language ──
SUMMARIES = {
    "en": (
        "Senior Data Engineer and Cloud Data Consultant with 20+ years of experience "
        "modernizing analytics ecosystems with Snowflake, Microsoft Fabric, Azure SQL, "
        "and SQL Server. I build automated, scalable pipelines and resilient data models "
        "that turn raw data into reliable, actionable insight — especially in high-volume, "
        "mission-critical environments. My toolkit is deep SQL + Python, paired with "
        "AI-assisted development (GitHub Copilot, ChatGPT, Claude) to deliver solutions "
        "that are cloud-native, operationally practical, and designed to evolve."
    ),
    "es": (
        "Ingeniero de Datos Senior y Consultor Cloud con más de 20 años de experiencia "
        "modernizando ecosistemas analíticos con Snowflake, Microsoft Fabric, Azure SQL "
        "y SQL Server. Construyo pipelines automatizados y escalables, y modelos de datos "
        "resilientes que convierten datos crudos en información confiable y accionable — "
        "especialmente en entornos de alto volumen y misión crítica. Mi toolkit es SQL "
        "profundo + Python, combinado con desarrollo asistido por IA (GitHub Copilot, "
        "ChatGPT, Claude) para entregar soluciones cloud-native y prácticas."
    ),
    "de": (
        "Senior Data Engineer und Cloud-Datenberater mit über 20 Jahren Erfahrung "
        "in der Modernisierung analytischer Ökosysteme mit Snowflake, Microsoft Fabric, "
        "Azure SQL und SQL Server. Ich baue automatisierte, skalierbare Pipelines und "
        "belastbare Datenmodelle, die Rohdaten in zuverlässige, umsetzbare Erkenntnisse "
        "verwandeln — besonders in hochvolumigen, missionskritischen Umgebungen. "
        "Mein Toolkit ist tiefes SQL + Python, gepaart mit KI-gestützter Entwicklung "
        "(GitHub Copilot, ChatGPT, Claude)."
    ),
}


# ── Data extraction ──

def extract_experiences(raw: str) -> list[dict]:
    """Extract experience blocks from cv.ts."""
    blocks = re.findall(
        r"\{\s*company:\s*['\"](.+?)['\"].*?role:\s*['\"](.+?)['\"].*?"
        r"period:\s*\{[^}]*start:\s*['\"](.+?)['\"][^}]*?(?:end:\s*(?:null|['\"](.+?)['\"]))[^}]*?\}.*?"
        r"location:\s*['\"](.+?)['\"].*?"
        r"description:\s*\n?\s*(?:['\"])(.+?)(?:['\"]).*?"
        r"achievements:\s*\[([\s\S]*?)\].*?"
        r"technologies:\s*\[([\s\S]*?)\]",
        raw, re.DOTALL,
    )
    exps = []
    for company, role, start, end, location, desc, achs_raw, techs_raw in blocks:
        achs = re.findall(r"['\"](.+?)['\"]", achs_raw)
        techs = re.findall(r"['\"](.+?)['\"]", techs_raw)
        exps.append({
            "company": company,
            "role": role,
            "start": start,
            "end": end or None,
            "location": location,
            "description": desc,
            "achievements": achs,
            "technologies": techs,
        })
    return exps


def extract_education(raw: str) -> list[dict]:
    """Extract education blocks from cv.ts."""
    blocks = re.findall(
        r"\{\s*institution:\s*['\"](.+?)['\"].*?"
        r"degree:\s*['\"](.+?)['\"].*?"
        r"field:\s*['\"](.+?)['\"].*?"
        r"period:\s*\{[^}]*start:\s*['\"](.+?)['\"][^}]*?end:\s*['\"](.+?)['\"]",
        raw, re.DOTALL,
    )
    edus = []
    for inst, degree, field, start, end in blocks:
        # Check for note
        block_m = re.search(
            rf"\{{\s*institution:\s*['\"]({re.escape(inst)})['\"][\s\S]*?\}}",
            raw,
        )
        note = ""
        if block_m:
            note_m = re.search(r"note:\s*['\"](.+?)['\"]", block_m.group(0))
            if note_m:
                note = note_m.group(1)
        edus.append({
            "institution": inst,
            "degree": degree,
            "field": field,
            "start": start,
            "end": end,
            "note": note,
        })
    return edus


def extract_skills(raw: str) -> list[dict]:
    """Extract skill groups from cv.ts."""
    blocks = re.findall(
        r"category:\s*['\"](.+?)['\"].*?skills:\s*\[([\s\S]*?)\]",
        raw, re.DOTALL,
    )
    groups = []
    for category, skills_raw in blocks:
        skills = re.findall(r"name:\s*['\"](.+?)['\"]", skills_raw)
        groups.append({"category": category, "skills": skills})
    return groups


def extract_certs(raw: str) -> list[dict]:
    """Extract certifications from certs.ts."""
    cert_blocks = re.findall(
        r"\{[^{}]*?name:\s*['\"](.+?)['\"][^{}]*?issuer:\s*['\"](.+?)['\"][^{}]*?year:\s*(\d+)[^{}]*?\}",
        raw, re.DOTALL,
    )
    certs = []
    for match_text, cert_match in zip(
        re.findall(r"\{[^{}]*?name:\s*['\"].+?['\"][^{}]*?\}", raw, re.DOTALL),
        cert_blocks,
    ):
        name, issuer, year = cert_match
        expired = "expired: true" in match_text or "expired:true" in match_text
        certs.append({
            "name": name,
            "issuer": issuer,
            "year": int(year),
            "expired": expired,
        })
    return certs


def extract_open_to_work(raw: str) -> list[str]:
    """Extract openToWork roles."""
    m = re.search(r"openToWork:\s*\[([\s\S]*?)\]", raw)
    if m:
        return re.findall(r"['\"](.+?)['\"]", m.group(1))
    return []


# ── PDF generation ──

def build_styles():
    """Create custom paragraph styles."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        "CVName", parent=styles["Title"],
        fontSize=22, textColor=PRIMARY, spaceAfter=2,
        alignment=TA_LEFT, leading=26,
    ))
    styles.add(ParagraphStyle(
        "CVHeadline", parent=styles["Normal"],
        fontSize=10, textColor=GRAY, spaceAfter=4,
        alignment=TA_LEFT, leading=13,
    ))
    styles.add(ParagraphStyle(
        "CVSection", parent=styles["Heading2"],
        fontSize=13, textColor=PRIMARY, spaceBefore=14, spaceAfter=6,
        borderWidth=0, leading=16,
    ))
    styles.add(ParagraphStyle(
        "CVSubsection", parent=styles["Heading3"],
        fontSize=10.5, textColor=DARK, spaceBefore=8, spaceAfter=2,
        leading=13,
    ))
    styles.add(ParagraphStyle(
        "CVBody", parent=styles["Normal"],
        fontSize=9, textColor=DARK, spaceAfter=2,
        alignment=TA_JUSTIFY, leading=12,
    ))
    styles.add(ParagraphStyle(
        "CVSmall", parent=styles["Normal"],
        fontSize=8, textColor=GRAY, spaceAfter=1,
        leading=10,
    ))
    styles.add(ParagraphStyle(
        "CVBullet", parent=styles["Normal"],
        fontSize=8.5, textColor=DARK, spaceAfter=1,
        leftIndent=12, bulletIndent=0, leading=11,
    ))
    styles.add(ParagraphStyle(
        "CVFooter", parent=styles["Normal"],
        fontSize=7, textColor=GRAY, alignment=TA_CENTER,
        leading=9,
    ))
    return styles


def generate_pdf(lang: str, experiences: list, education: list, skills: list,
                 certs: list, open_roles: list, output_path: Path):
    """Generate a single-language CV PDF."""
    tr = TRANSLATIONS[lang]
    summary = SUMMARIES[lang]
    styles = build_styles()

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    story = []

    # ── Header ──
    story.append(Paragraph("Carlos Carrillo", styles["CVName"]))
    story.append(Paragraph(
        "AI-Driven Engineer | Data · Developer · DBA | "
        "Snowflake · Azure SQL · ADX/KQL · Python | Remote (EN/ES)",
        styles["CVHeadline"],
    ))
    story.append(Spacer(1, 2))

    # Contact info
    contact_text = (
        '<font color="#0369a1">carlos.carrillo@dataqbs.com</font> · '
        '<font color="#0369a1">dataqbs.com</font> · '
        '<font color="#0369a1">linkedin.com/in/carlosalbertocarrillo</font> · '
        '<font color="#0369a1">github.com/CarlosCaPe</font>'
    )
    story.append(Paragraph(contact_text, styles["CVSmall"]))
    story.append(Paragraph(
        f"México · {tr['remote']} | {tr['availability']}",
        styles["CVSmall"],
    ))

    # Open to work
    if open_roles:
        story.append(Paragraph(
            f"<b>{tr['open_to_work']}:</b> {', '.join(open_roles)}",
            styles["CVSmall"],
        ))
    story.append(Paragraph(
        f"<b>{tr['languages']}:</b> {tr['spanish']}, {tr['english']}",
        styles["CVSmall"],
    ))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(
        width="100%", thickness=0.5, color=LIGHT_GRAY, spaceAfter=6,
    ))

    # ── Summary ──
    story.append(Paragraph(f"<b>{tr['summary']}</b>", styles["CVSection"]))
    story.append(Paragraph(summary, styles["CVBody"]))

    # ── Experience ──
    story.append(Paragraph(f"<b>{tr['experience']}</b>", styles["CVSection"]))
    for exp in experiences:
        end_text = tr["present"] if not exp["end"] else exp["end"]
        period = f"{exp['start']} — {end_text}"

        header = f"<b>{exp['role']}</b> · {exp['company']}"
        meta = f"{period} | {exp['location']}"

        block = [
            Paragraph(header, styles["CVSubsection"]),
            Paragraph(meta, styles["CVSmall"]),
        ]

        # Top 3 achievements to keep PDF concise
        for ach in exp["achievements"][:3]:
            # Truncate very long achievements
            ach_text = ach if len(ach) <= 200 else ach[:197] + "..."
            block.append(Paragraph(f"- {ach_text}", styles["CVBullet"]))

        if exp["technologies"]:
            techs_text = ", ".join(exp["technologies"][:10])
            block.append(Paragraph(
                f'<font color="#64748b"><i>{tr["technologies"]}: {techs_text}</i></font>',
                styles["CVSmall"],
            ))
        block.append(Spacer(1, 4))
        story.append(KeepTogether(block))

    # ── Certifications ──
    if certs:
        story.append(Paragraph(f"<b>{tr['certifications']}</b>", styles["CVSection"]))
        active = [c for c in certs if not c["expired"]]
        expired = [c for c in certs if c["expired"]]

        for cert in active:
            story.append(Paragraph(
                f"- <b>{cert['name']}</b> -- {cert['issuer']} ({cert['year']}) "
                f'<font color="#059669">[{tr["active"]}]</font>',
                styles["CVBullet"],
            ))
        for cert in expired:
            story.append(Paragraph(
                f"- {cert['name']} -- {cert['issuer']} ({cert['year']}) "
                f'<font color="#94a3b8">[{tr["expired"]}]</font>',
                styles["CVBullet"],
            ))
        story.append(Spacer(1, 4))

    # ── Skills ──
    story.append(Paragraph(f"<b>{tr['skills']}</b>", styles["CVSection"]))
    for group in skills:
        skills_text = ", ".join(group["skills"])
        story.append(Paragraph(
            f"<b>{group['category']}:</b> {skills_text}",
            styles["CVBullet"],
        ))
    story.append(Spacer(1, 4))

    # ── Education ──
    story.append(Paragraph(f"<b>{tr['education']}</b>", styles["CVSection"]))
    for edu in education:
        note = ""
        if edu["note"]:
            note_text = tr.get("degree_in_process", edu["note"])
            note = f' <font color="#f59e0b">({note_text})</font>'
        story.append(Paragraph(
            f"<b>{edu['degree']}</b> in {edu['field']} — {edu['institution']} "
            f"({edu['start']}–{edu['end']}){note}",
            styles["CVBullet"],
        ))

    # ── Footer ──
    story.append(Spacer(1, 12))
    story.append(HRFlowable(
        width="100%", thickness=0.3, color=LIGHT_GRAY, spaceAfter=4,
    ))
    story.append(Paragraph(
        f"© 2026 Carlos Carrillo · {tr['generated']}",
        styles["CVFooter"],
    ))

    doc.build(story)
    print(f"  ✅ {output_path.name} ({output_path.stat().st_size / 1024:.1f} KB)")


def main():
    print("╔══════════════════════════════════════════╗")
    print("║  CV PDF Generator — EN / ES / DE          ║")
    print("╚══════════════════════════════════════════╝\n")

    if not CV_TS.exists():
        print(f"ERROR: {CV_TS} not found")
        sys.exit(1)

    raw = CV_TS.read_text(encoding="utf-8")
    certs_raw = CERTS_TS.read_text(encoding="utf-8") if CERTS_TS.exists() else ""

    print("📂 Extracting data from cv.ts / certs.ts...")
    experiences = extract_experiences(raw)
    education = extract_education(raw)
    skills = extract_skills(raw)
    certs = extract_certs(certs_raw)
    open_roles = extract_open_to_work(raw)

    print(f"   Experience:     {len(experiences)} roles")
    print(f"   Education:      {len(education)} entries")
    print(f"   Skills:         {len(skills)} categories")
    print(f"   Certifications: {len(certs)} entries")
    print(f"   Open to Work:   {len(open_roles)} roles\n")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    outputs = {
        "en": OUTPUT_DIR / "Profile.pdf",
        "es": OUTPUT_DIR / "Profile_ES.pdf",
        "de": OUTPUT_DIR / "Profile_DE.pdf",
    }

    print("📝 Generating PDFs...")
    for lang, path in outputs.items():
        generate_pdf(lang, experiences, education, skills, certs, open_roles, path)

    print("\n✅ Done! All 3 PDFs generated.")


if __name__ == "__main__":
    main()
