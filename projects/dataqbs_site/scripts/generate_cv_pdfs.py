#!/usr/bin/env python3
"""
generate_cv_pdfs.py — Generate CV PDFs in EN, ES, and DE from cv.ts data.

Reads structured data from src/data/cv.ts and src/data/certs.ts,
generates clean professional PDFs for each language with full translations.

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
PRIMARY = HexColor("#1e40af")
DARK = HexColor("#1e293b")
GRAY = HexColor("#64748b")
LIGHT_GRAY = HexColor("#e2e8f0")

# ══════════════════════════════════════════════════════════════
#  TRANSLATIONS — Labels, headers, metadata
# ══════════════════════════════════════════════════════════════
LABELS = {
    "en": {
        "summary": "Summary",
        "experience": "Experience",
        "education": "Education",
        "skills": "Skills",
        "certifications": "Certifications",
        "present": "Present",
        "technologies": "Technologies",
        "languages": "Languages",
        "spanish": "Spanish (Native)",
        "english": "English (Professional Working)",
        "open_to_work": "Open to Work",
        "availability": "Availability: Remote Only (Worldwide)",
        "remote": "Remote",
        "expired": "Expired",
        "active": "Active",
        "degree_in_process": "Degree in process",
        "generated": "Generated from dataqbs.com",
    },
    "es": {
        "summary": "Resumen",
        "experience": "Experiencia",
        "education": "Educacion",
        "skills": "Habilidades",
        "certifications": "Certificaciones",
        "present": "Actual",
        "technologies": "Tecnologias",
        "languages": "Idiomas",
        "spanish": "Espanol (Nativo)",
        "english": "Ingles (Profesional)",
        "open_to_work": "Abierto a trabajar",
        "availability": "Disponibilidad: Solo Remoto (Mundial)",
        "remote": "Remoto",
        "expired": "Expirado",
        "active": "Activo",
        "degree_in_process": "Titulo en proceso",
        "generated": "Generado desde dataqbs.com",
    },
    "de": {
        "summary": "Zusammenfassung",
        "experience": "Erfahrung",
        "education": "Ausbildung",
        "skills": "Faehigkeiten",
        "certifications": "Zertifizierungen",
        "present": "Aktuell",
        "technologies": "Technologien",
        "languages": "Sprachen",
        "spanish": "Spanisch (Muttersprache)",
        "english": "Englisch (Beruflich)",
        "open_to_work": "Offen fuer Arbeit",
        "availability": "Verfuegbarkeit: Nur Remote (Weltweit)",
        "remote": "Remote",
        "expired": "Abgelaufen",
        "active": "Aktiv",
        "degree_in_process": "Studium laeuft",
        "generated": "Erstellt von dataqbs.com",
    },
}

# ══════════════════════════════════════════════════════════════
#  SUMMARIES — Full professional summary per language
# ══════════════════════════════════════════════════════════════
SUMMARIES = {
    "en": (
        "Senior Data Engineer and Cloud Data Consultant with 20+ years of experience "
        "modernizing analytics ecosystems with Snowflake, Microsoft Fabric, Azure SQL, "
        "and SQL Server. I build automated, scalable pipelines and resilient data models "
        "that turn raw data into reliable, actionable insight -- especially in high-volume, "
        "mission-critical environments. My toolkit is deep SQL + Python, paired with "
        "AI-assisted development (GitHub Copilot, ChatGPT, Claude) to deliver solutions "
        "that are cloud-native, operationally practical, and designed to evolve."
    ),
    "es": (
        "Ingeniero de Datos Senior y Consultor Cloud con mas de 20 anos de experiencia "
        "modernizando ecosistemas analiticos con Snowflake, Microsoft Fabric, Azure SQL "
        "y SQL Server. Construyo pipelines automatizados y escalables, y modelos de datos "
        "resilientes que convierten datos crudos en informacion confiable y accionable -- "
        "especialmente en entornos de alto volumen y mision critica. Mi toolkit es SQL "
        "profundo + Python, combinado con desarrollo asistido por IA (GitHub Copilot, "
        "ChatGPT, Claude) para entregar soluciones cloud-native, practicas y disenadas para evolucionar."
    ),
    "de": (
        "Senior Data Engineer und Cloud-Datenberater mit ueber 20 Jahren Erfahrung "
        "in der Modernisierung analytischer Oekosysteme mit Snowflake, Microsoft Fabric, "
        "Azure SQL und SQL Server. Ich baue automatisierte, skalierbare Pipelines und "
        "belastbare Datenmodelle, die Rohdaten in zuverlaessige, umsetzbare Erkenntnisse "
        "verwandeln -- besonders in hochvolumigen, missionskritischen Umgebungen. "
        "Mein Toolkit ist tiefes SQL + Python, gepaart mit KI-gestuetzter Entwicklung "
        "(GitHub Copilot, ChatGPT, Claude) fuer cloud-native, praktische Loesungen."
    ),
}

# ══════════════════════════════════════════════════════════════
#  ACHIEVEMENT TRANSLATIONS — indexed by experience order
#  Only top 3 achievements per role are shown in the PDF.
# ══════════════════════════════════════════════════════════════
ACH_ES = [
    # 0: Hexaware Technologies
    [
        "Lidere la integracion Snowflake -> Azure SQL; despliegue pipeline de sincronizacion incremental de 14 tablas con procedimientos MERGE, programacion cada 15 min, deteccion delta con HASH, verificacion E2E (~590K filas) en DEV->TEST->PROD",
        "Disene cargas incrementales basadas en marca de agua usando timestamps de negocio y respaldos DW_MODIFY_TS para dashboards de Connected Operations",
        "Construi snowrefactor, CLI en Python para pruebas de regresion de vistas Snowflake: extraccion automatica de DDL, despliegue, comparacion de esquemas y benchmarking en flujos CTE estilo dbt",
    ],
    # 1: FussionHit
    [
        "Construi framework de auditoria PostgreSQL con exportaciones DDL templadas por objeto (Nunjucks/Jinja)",
        "Entregue 20+ tickets de base de datos (optimizacion de indices, remediacion de FK, renombramientos de esquema, normalizacion de timestamps)",
        "Redacte Documentos de Diseno Tecnico para las bases de datos Student Concierge, Relief Vet, VWR, Appointment Waitlist y Feature Flags",
    ],
    # 2: dataqbs
    [
        "Entregue ingenieria de datos para VCA Animal Hospitals, C&amp;A Mexico, BCG, Moviro, Svitla, Quesos Navarro",
        "Construi MEMO-GRID: bot avanzado de grid trading con HPO Optuna (50K pruebas), multiplicador 23x BTC, analisis de atribucion (95.7% alfa)",
        "Disene escaner de arbitraje cripto triangular con Bellman-Ford a traves de 9 exchanges con ejecucion de swaps en vivo",
    ],
    # 3: SVAM International
    [
        "Lidere migracion de SQL Server on-prem y SSIS a Snowflake, disenando nuevos modelos fact/dimension para analitica de certificaciones estudiantiles",
        "Automatice ingestion de JSON desde APIs de Salesforce hacia Snowflake usando Python",
        "Construi pruebas de validacion y reconciliacion de datos, asegurando precision de carga end-to-end",
    ],
    # 4: Svitla Systems
    [
        "Disene y despliegue el primer data warehouse en Azure SQL de la empresa para analitica de ventas en la nube",
        "Desarrolle paquetes SSIS para extracciones on-prem y orqueste actualizaciones con Azure Data Factory",
        "Construi modelos de datos star-schema flexibles para escalar segun crecian las necesidades de reporteo",
    ],
    # 5: Epikso Mexico
    [
        "Administre seguridad de Snowflake, acceso basado en roles y ajuste de rendimiento",
        "Implemente Infrastructure-as-Code para configuracion automatizada de ambientes",
        "Monitoree rendimiento de consultas y optimize almacenamiento/micro-particionamiento",
    ],
    # 6: Jabil (Data Technical Lead)
    [
        "Dirigi migracion de Hadoop + Impala + SQL Server PDW a Snowflake en AWS, habilitando analitica mas rapida",
        "Construi orquestacion streaming y basada en tareas usando funciones nativas de automatizacion de Snowflake",
        "Disene zonas de landing, staging y refinadas para ingestion y transformacion escalable",
    ],
    # 7: 3Pillar Global
    [
        "Desarrolle integraciones de datos EDI y capas de reporteo con SQL Server, SSIS y SSRS",
        "Mantuve sincronizacion confiable de datos entre multiples socios externos",
    ],
    # 8: HCL Technologies
    [
        "Migre y optimize reportes Actuate hacia SSRS y SharePoint",
        "Desarrolle logica SQL de alto rendimiento para reportes empresariales",
    ],
    # 9: Jabil (Database Analyst II)
    [
        "Cree y mantuve flujos ETL usando SSIS, integrando sistemas Oracle, SAP y MySQL",
        "Asegure confiabilidad 24/7 de bases de datos y optimizacion de rendimiento",
    ],
    # 10: C&A Mexico
    [
        "Disene cubos OLAP (SSAS) y reportes interactivos SSRS para analitica retail",
        "Construi flujos ETL desde mainframes y tiendas regionales hacia data warehouse centralizado",
        "Mantuve ambientes SQL de alto rendimiento a traves de unidades de negocio",
    ],
    # 11: FIRMEPLUS
    [
        "Desarrollo de software y bases de datos (PHP, SQL Server, MySQL)",
    ],
    # 12: Jabil Circuit de Mexico
    [
        "Apoye desarrollo de bases de datos y aplicaciones web",
    ],
]

ACH_DE = [
    # 0: Hexaware Technologies
    [
        "Leitete die Snowflake -> Azure SQL Integration; bereitete inkrementelle Sync-Pipeline fuer 14 Tabellen mit MERGE-Prozeduren, 15-Min-Planung, HASH-Delta-Erkennung, E2E-Verifizierung (~590K Zeilen) in DEV->TEST->PROD",
        "Entwarf wasserzeichenbasierte inkrementelle Ladevorgaenge mit Business-Timestamps und DW_MODIFY_TS-Fallbacks fuer Connected Operations Dashboards",
        "Entwickelte snowrefactor, Python-CLI fuer Snowflake-View-Regressionstests: automatisierter DDL-Pull, Deployment, Schema-Vergleich und Benchmarking in dbt-Style CTE-Workflows",
    ],
    # 1: FussionHit
    [
        "Entwickelte PostgreSQL-Audit-Framework mit objektbezogenen Template-DDL-Exporten (Nunjucks/Jinja)",
        "Lieferte 20+ Datenbank-Tickets (Index-Optimierung, FK-Bereinigung, Schema-Umbenennungen, Timestamp-Normalisierung)",
        "Verfasste Technische Design-Dokumente fuer die Datenbanken Student Concierge, Relief Vet, VWR, Appointment Waitlist und Feature Flags",
    ],
    # 2: dataqbs
    [
        "Lieferte Data Engineering fuer VCA Animal Hospitals, C&amp;A Mexico, BCG, Moviro, Svitla, Quesos Navarro",
        "Entwickelte MEMO-GRID: fortgeschrittenen Grid-Trading-Bot mit Optuna HPO (50K Versuche), 23x BTC-Multiplikator, Attributionsanalyse (95,7% Alpha)",
        "Entwarf Bellman-Ford &amp; triangulaeren Krypto-Arbitrage-Scanner ueber 9 Boersen mit Live-Swap-Ausfuehrung",
    ],
    # 3: SVAM International
    [
        "Leitete Migration von On-Prem SQL Server und SSIS zu Snowflake, Entwurf neuer Fact/Dimension-Modelle fuer Studentenzertifizierungs-Analytik",
        "Automatisierte JSON-Aufnahme von Salesforce-APIs in Snowflake mit Python",
        "Entwickelte Datenvalidierungs- und Abgleichtests zur Sicherstellung der End-to-End-Ladegenauigkeit",
    ],
    # 4: Svitla Systems
    [
        "Entwarf und implementierte das erste Azure SQL Data Warehouse des Unternehmens fuer Cloud-basierte Vertriebsanalytik",
        "Entwickelte SSIS-Pakete fuer On-Prem-Extraktionen und orchestrierte Updates mit Azure Data Factory",
        "Erstellte flexible Star-Schema-Datenmodelle zur Skalierung nach wachsenden Reporting-Anforderungen",
    ],
    # 5: Epikso Mexico
    [
        "Verwaltete Snowflake-Sicherheit, rollenbasierten Zugriff und Performance-Tuning",
        "Implementierte Infrastructure-as-Code fuer automatisierte Umgebungseinrichtung",
        "Ueberwachte Abfrageleistung und optimierte Speicher/Micro-Partitioning",
    ],
    # 6: Jabil (Data Technical Lead)
    [
        "Leitete Migration von Hadoop + Impala + SQL Server PDW zu Snowflake auf AWS fuer schnellere Analytik",
        "Entwickelte Streaming- und aufgabenbasierte Orchestrierung mit nativen Snowflake-Automatisierungsfunktionen",
        "Entwarf Landing-, Staging- und Refined-Zonen fuer skalierbare Aufnahme und Transformation",
    ],
    # 7: 3Pillar Global
    [
        "Entwickelte EDI-Datenintegrationen und Reporting-Schichten mit SQL Server, SSIS und SSRS",
        "Sicherstellte zuverlaessige Datensynchronisation mit mehreren externen Partnern",
    ],
    # 8: HCL Technologies
    [
        "Migrierte und optimierte Actuate-Berichte in SSRS und SharePoint",
        "Entwickelte performante SQL-Logik fuer Unternehmensreporting",
    ],
    # 9: Jabil (Database Analyst II)
    [
        "Erstellte und wartete ETL-Workflows mit SSIS zur Integration von Oracle-, SAP- und MySQL-Systemen",
        "Sicherstellte 24/7-Datenbankzuverlaessigkeit und Leistungsoptimierung",
    ],
    # 10: C&A Mexico
    [
        "Entwarf OLAP-Cubes (SSAS) und interaktive SSRS-Berichte fuer Einzelhandelsanalytik",
        "Erstellte ETL-Workflows von Mainframes und regionalen Filialen zum zentralen Data Warehouse",
        "Wartete Hochleistungs-SQL-Umgebungen ueber Geschaeftsbereiche hinweg",
    ],
    # 11: FIRMEPLUS
    [
        "Software- und Datenbankentwicklung (PHP, SQL Server, MySQL)",
    ],
    # 12: Jabil Circuit de Mexico
    [
        "Unterstuetzte Datenbank- und Webanwendungsentwicklung",
    ],
]

ACH_TRANSLATIONS = {"es": ACH_ES, "de": ACH_DE}

# ══════════════════════════════════════════════════════════════
#  SKILL CATEGORY TRANSLATIONS
# ══════════════════════════════════════════════════════════════
SKILL_CAT = {
    "es": {
        "Languages": "Lenguajes",
        "Data & Cloud": "Datos y Cloud",
        "AI & ML": "IA y ML",
        "Libraries & Frameworks": "Librerias y Frameworks",
        "DevOps & Tools": "DevOps y Herramientas",
        "Databases": "Bases de Datos",
    },
    "de": {
        "Languages": "Programmiersprachen",
        "Data & Cloud": "Daten &amp; Cloud",
        "AI & ML": "KI &amp; ML",
        "Libraries & Frameworks": "Bibliotheken &amp; Frameworks",
        "DevOps & Tools": "DevOps &amp; Werkzeuge",
        "Databases": "Datenbanken",
    },
}

# ══════════════════════════════════════════════════════════════
#  EDUCATION TRANSLATIONS
# ══════════════════════════════════════════════════════════════
EDU_TRANSLATIONS = {
    "es": {
        "Master": "Maestria",
        "Bachelor Degree": "Licenciatura",
        "Business Administration (MBA)": "Administracion de Empresas (MBA)",
        "Computing Science": "Ciencias de la Computacion",
        "in": "en",
    },
    "de": {
        "Master": "Master",
        "Bachelor Degree": "Bachelor",
        "Business Administration (MBA)": "Betriebswirtschaftslehre (MBA)",
        "Computing Science": "Informatik",
        "in": "in",
    },
}


# ══════════════════════════════════════════════════════════════
#  DATA EXTRACTION from cv.ts / certs.ts
# ══════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════
#  PDF GENERATION
# ══════════════════════════════════════════════════════════════

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
    tr = LABELS[lang]
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
        "AI-Driven Engineer | Data - Developer - DBA | "
        "Snowflake - Azure SQL - ADX/KQL - Python | Remote (EN/ES)",
        styles["CVHeadline"],
    ))
    story.append(Spacer(1, 2))

    # Contact info
    contact_text = (
        '<font color="#0369a1">carlos.carrillo@dataqbs.com</font> - '
        '<font color="#0369a1">dataqbs.com</font> - '
        '<font color="#0369a1">linkedin.com/in/carlosalbertocarrillo</font> - '
        '<font color="#0369a1">github.com/CarlosCaPe</font>'
    )
    story.append(Paragraph(contact_text, styles["CVSmall"]))
    story.append(Paragraph(
        f"Mexico - {tr['remote']} | {tr['availability']}",
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

    for idx, exp in enumerate(experiences):
        end_text = tr["present"] if not exp["end"] else exp["end"]
        period = f"{exp['start']} -- {end_text}"

        header = f"<b>{exp['role']}</b> - {exp['company']}"
        meta = f"{period} | {exp['location']}"

        block = [
            Paragraph(header, styles["CVSubsection"]),
            Paragraph(meta, styles["CVSmall"]),
        ]

        # Get translated achievements (top 3)
        if lang != "en" and lang in ACH_TRANSLATIONS and idx < len(ACH_TRANSLATIONS[lang]):
            translated_achs = ACH_TRANSLATIONS[lang][idx]
        else:
            translated_achs = exp["achievements"]

        for ach in translated_achs[:3]:
            ach_text = ach if len(ach) <= 250 else ach[:247] + "..."
            block.append(Paragraph(f"- {ach_text}", styles["CVBullet"]))

        if exp["technologies"]:
            techs_text = ", ".join(exp["technologies"][:12])
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
        cat_name = group["category"]
        if lang != "en" and lang in SKILL_CAT:
            cat_name = SKILL_CAT[lang].get(cat_name, cat_name)
        skills_text = ", ".join(group["skills"])
        story.append(Paragraph(
            f"<b>{cat_name}:</b> {skills_text}",
            styles["CVBullet"],
        ))
    story.append(Spacer(1, 4))

    # ── Education ──
    story.append(Paragraph(f"<b>{tr['education']}</b>", styles["CVSection"]))
    for edu in education:
        degree = edu["degree"]
        field = edu["field"]
        in_word = "in"
        if lang != "en" and lang in EDU_TRANSLATIONS:
            degree = EDU_TRANSLATIONS[lang].get(degree, degree)
            field = EDU_TRANSLATIONS[lang].get(field, field)
            in_word = EDU_TRANSLATIONS[lang].get("in", "in")

        note = ""
        if edu["note"]:
            note_text = tr.get("degree_in_process", edu["note"])
            note = f' <font color="#f59e0b">({note_text})</font>'
        story.append(Paragraph(
            f"<b>{degree}</b> {in_word} {field} -- {edu['institution']} "
            f"({edu['start']}--{edu['end']}){note}",
            styles["CVBullet"],
        ))

    # ── Footer ──
    story.append(Spacer(1, 12))
    story.append(HRFlowable(
        width="100%", thickness=0.3, color=LIGHT_GRAY, spaceAfter=4,
    ))
    story.append(Paragraph(
        f"(c) 2026 Carlos Carrillo - {tr['generated']}",
        styles["CVFooter"],
    ))

    doc.build(story)
    print(f"  OK {output_path.name} ({output_path.stat().st_size / 1024:.1f} KB)")


def main():
    print("=" * 50)
    print("  CV PDF Generator -- EN / ES / DE")
    print("=" * 50 + "\n")

    if not CV_TS.exists():
        print(f"ERROR: {CV_TS} not found")
        sys.exit(1)

    raw = CV_TS.read_text(encoding="utf-8")
    certs_raw = CERTS_TS.read_text(encoding="utf-8") if CERTS_TS.exists() else ""

    print("Extracting data from cv.ts / certs.ts...")
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

    print("Generating PDFs...")
    for lang, path in outputs.items():
        generate_pdf(lang, experiences, education, skills, certs, open_roles, path)

    print("\nDone! All 3 PDFs generated.")


if __name__ == "__main__":
    main()
