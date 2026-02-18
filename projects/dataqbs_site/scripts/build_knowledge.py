#!/usr/bin/env python3
"""
build_knowledge.py — Knowledge pipeline for dataqbs.com chatbot.

Reads CV data, certifications, project READMEs, and other docs,
chunks them semantically, generates embeddings via Cloudflare Workers AI,
and outputs public/knowledge.json for the chat endpoint.

Usage:
    python scripts/build_knowledge.py

Environment variables (or .env):
    CF_ACCOUNT_ID   — Cloudflare account ID
    CF_API_TOKEN    — Cloudflare API token (Workers AI access)
"""

from __future__ import annotations

import json
import os
import re
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    print("ERROR: 'requests' not installed. Run: pip install requests")
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("ERROR: 'pyyaml' not installed. Run: pip install pyyaml")
    sys.exit(1)

# ── Paths ─────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
MONOREPO_DIR = PROJECT_DIR.parent.parent  # dataqbs_IA/
KNOWLEDGE_DIR = PROJECT_DIR / "knowledge"
OUTPUT_PATH = PROJECT_DIR / "public" / "knowledge.json"
SEMANTIC_MODEL_PATH = KNOWLEDGE_DIR / "semantic_model.yaml"

# ── Config ────────────────────────────────────────────
EMBEDDING_MODEL = "@cf/baai/bge-base-en-v1.5"
EMBEDDING_DIM = 768
CHUNK_SIZE = 512  # approx tokens (chars / 4)
CHUNK_OVERLAP = 64
MAX_CHARS_PER_CHUNK = CHUNK_SIZE * 4  # rough char estimate
OVERLAP_CHARS = CHUNK_OVERLAP * 4
BATCH_SIZE = 20  # embeddings per API call


def load_env() -> None:
    """Load .env from project root if present."""
    env_path = PROJECT_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


def get_cf_credentials() -> tuple[str, str]:
    """Return (account_id, api_token) from environment."""
    account_id = os.environ.get("CF_ACCOUNT_ID", "")
    api_token = os.environ.get("CF_API_TOKEN", "")
    if not account_id or not api_token:
        print("WARNING: CF_ACCOUNT_ID or CF_API_TOKEN not set.")
        print("         Embeddings will be zero vectors (placeholder).")
    return account_id, api_token


# ── Source collection ─────────────────────────────────

def collect_readmes() -> list[dict[str, str]]:
    """Find all README.md files in the monorepo."""
    sources: list[dict[str, str]] = []
    for readme in sorted(MONOREPO_DIR.rglob("README.md")):
        # Skip node_modules, .venv, etc.
        rel = readme.relative_to(MONOREPO_DIR)
        parts = rel.parts
        if any(p.startswith(".") or p in ("node_modules", ".venv", "dist", "__pycache__") for p in parts):
            continue
        text = readme.read_text(encoding="utf-8", errors="replace").strip()
        if len(text) < 50:
            continue
        sources.append({
            "source": "github",
            "file": str(rel),
            "text": text,
        })
    return sources


def collect_knowledge_docs() -> list[dict[str, str]]:
    """Collect markdown files from the knowledge/ directory (external repos, extra docs)."""
    sources: list[dict[str, str]] = []
    for md_file in sorted(KNOWLEDGE_DIR.glob("*.md")):
        text = md_file.read_text(encoding="utf-8", errors="replace").strip()
        if len(text) < 50:
            continue
        sources.append({
            "source": "github",
            "file": f"knowledge/{md_file.name}",
            "text": text,
        })
    return sources


def collect_cv_data() -> list[dict[str, str]]:
    """
    Read structured CV data from src/data/cv.ts.
    Extracts profile info, experience, skills, education as plain text chunks.
    """
    cv_ts = PROJECT_DIR / "src" / "data" / "cv.ts"
    if not cv_ts.exists():
        return []

    raw = cv_ts.read_text(encoding="utf-8")
    chunks: list[dict[str, str]] = []

    # Extract summary
    m = re.search(r"summary:\s*\n?\s*['\"](.+?)['\"]", raw, re.DOTALL)
    if not m:
        m = re.search(r"summary:\s*\n?\s*'([\s\S]+?)'", raw)
    if not m:
        # Multi-line string concatenation: summary:\n    "..." +\n    '...'
        m = re.search(r"summary:\s*\n\s*((?:['\"].+?['\"](?:\s*\+\s*\n?\s*)?)+)", raw, re.DOTALL)
        if m:
            parts = re.findall(r"['\"](.+?)['\"]", m.group(1))
            summary_text = " ".join(parts)
            chunks.append({
                "source": "cv",
                "section": "summary",
                "text": f"Professional Summary: {summary_text.strip()}",
            })
    if m and not chunks:
        chunks.append({
            "source": "cv",
            "section": "summary",
            "text": f"Professional Summary: {m.group(1).strip()}",
        })

    # Extract vision/mission
    vm = re.search(r"vision:\s*\n?\s*['\"](.+?)['\"]", raw, re.DOTALL)
    if not vm:
        vm = re.search(r"vision:\s*\n?\s*'([\s\S]+?)'", raw)
    if not vm:
        vm = re.search(r"vision:\s*\n\s*((?:['\"].+?['\"](?:\s*\+\s*\n?\s*)?)+)", raw, re.DOTALL)
        if vm:
            parts = re.findall(r"['\"](.+?)['\"]", vm.group(1))
            vision_text = " ".join(parts)
            chunks.append({
                "source": "cv",
                "section": "vision",
                "text": f"Carlos's personal vision for dataqbs: {vision_text.strip()} "
                        f"He values simplicity, awareness, and letting technology serve life. "
                        f"His work reflects this: clean architectures, minimal dependencies, purposeful automation.",
            })
    if vm and len([c for c in chunks if c["section"] == "vision"]) == 0:
        chunks.append({
            "source": "cv",
            "section": "vision",
            "text": f"Carlos's personal vision for dataqbs: {vm.group(1).strip()} "
                    f"He values simplicity, awareness, and letting technology serve life. "
                    f"His work reflects this: clean architectures, minimal dependencies, purposeful automation.",
        })

    # ── Extract profile/biographical info ──
    loc = re.search(r"location:\s*['\"](.+?)['\"]", raw)
    headline = re.search(r"headline:\s*['\"](.+?)['\"]", raw)
    connections = re.search(r"connections:\s*['\"](.+?)['\"]", raw)

    # Extract openToWork roles
    otw_match = re.search(r"openToWork:\s*\[([\s\S]*?)\]", raw)
    otw_roles = re.findall(r"['\"](.+?)['\"]", otw_match.group(1)) if otw_match else []

    # Build profile chunk with all biographical info
    profile_parts = ["Carlos Carrillo — Professional Profile"]
    if loc:
        profile_parts.append(f"Location: {loc.group(1)}")
    if headline:
        profile_parts.append(f"Headline: {headline.group(1)}")
    if connections:
        profile_parts.append(f"LinkedIn Connections: {connections.group(1)}")
    if otw_roles:
        profile_parts.append(f"Open to Work — Roles: {', '.join(otw_roles)}")

    # Detect language info from headline
    if headline:
        hl = headline.group(1)
        if "EN/ES" in hl or "EN" in hl:
            profile_parts.append("Languages spoken: English (fluent), Spanish (native)")
        if "Remote" in hl:
            profile_parts.append("Availability: Open to remote and hybrid work arrangements")

    if len(profile_parts) > 1:
        chunks.append({
            "source": "cv",
            "section": "profile",
            "text": "\n".join(profile_parts),
        })

    # ── Extract experience blocks ──
    exp_blocks = re.findall(
        r"\{\s*company:\s*['\"](.+?)['\"].*?role:\s*['\"](.+?)['\"].*?"
        r"description:\s*\n?\s*['\"](.+?)['\"].*?"
        r"achievements:\s*\[([\s\S]*?)\]",
        raw,
        re.DOTALL,
    )
    for company, role, desc, achievements_raw in exp_blocks:
        achs = re.findall(r"['\"](.+?)['\"]", achievements_raw)

        # Also extract period, location, technologies for this block
        # Find the surrounding block for this company
        block_match = re.search(
            rf"\{{\s*company:\s*['\"]({re.escape(company)})['\"][\s\S]*?\}}",
            raw,
        )
        period_text = ""
        exp_loc = ""
        techs = []
        if block_match:
            block = block_match.group(0)
            p_start = re.search(r"start:\s*['\"](.+?)['\"]", block)
            p_end = re.search(r"end:\s*(?:null|['\"](.+?)['\"])", block)
            if p_start:
                start = p_start.group(1)
                end = p_end.group(1) if p_end and p_end.group(1) else "Present"
                period_text = f"Period: {start} to {end}"
            loc_m = re.search(r"location:\s*['\"](.+?)['\"]", block)
            if loc_m:
                exp_loc = f"Location: {loc_m.group(1)}"
            tech_m = re.search(r"technologies:\s*\[([\s\S]*?)\]", block)
            if tech_m:
                techs = re.findall(r"['\"](.+?)['\"]", tech_m.group(1))

        text_parts = [f"Role: {role} at {company}"]
        if period_text:
            text_parts.append(period_text)
        if exp_loc:
            text_parts.append(exp_loc)
        text_parts.append(f"Description: {desc}")
        if achs:
            text_parts.append("Achievements:\n" + "\n".join(f"- {a}" for a in achs))
        if techs:
            text_parts.append(f"Technologies used: {', '.join(techs)}")

        chunks.append({
            "source": "cv",
            "section": "experience",
            "text": "\n".join(text_parts),
        })

    # ── Extract education ──
    edu_blocks = re.findall(
        r"\{\s*institution:\s*['\"](.+?)['\"].*?"
        r"degree:\s*['\"](.+?)['\"].*?"
        r"field:\s*['\"](.+?)['\"]",
        raw,
        re.DOTALL,
    )
    for institution, degree, field in edu_blocks:
        # Extract period from education block
        block_match = re.search(
            rf"\{{\s*institution:\s*['\"]({re.escape(institution)})['\"][\s\S]*?\}}",
            raw,
        )
        edu_period = ""
        edu_loc = ""
        if block_match:
            block = block_match.group(0)
            p_start = re.search(r"start:\s*['\"](.+?)['\"]", block)
            p_end = re.search(r"end:\s*['\"](.+?)['\"]", block)
            if p_start and p_end:
                edu_period = f"Years: {p_start.group(1)} – {p_end.group(1)}"
            loc_m = re.search(r"location:\s*['\"](.+?)['\"]", block)
            if loc_m:
                edu_loc = loc_m.group(1)

        text = f"Education: {degree} in {field} from {institution}."
        if edu_period:
            text += f" {edu_period}."
        if edu_loc:
            text += f" Located in {edu_loc}."

        # Check for note (e.g. "Degree in process")
        if block_match:
            note_m = re.search(r"note:\s*['\"](.+?)['\"]", block_match.group(0))
            if note_m:
                text += f" Note: {note_m.group(1)}."

        text += (
            f"\nCarlos studied at {institution} ({edu_loc or 'Mexico'}), "
            f"earning a {degree} in {field}. This academic foundation "
            f"supports his expertise in data engineering, software development, and AI."
        )

        chunks.append({
            "source": "cv",
            "section": "education",
            "text": text,
        })

    # Extract skills (enhanced with descriptive text)
    skill_blocks = re.findall(
        r"category:\s*['\"](.+?)['\"].*?skills:\s*\[([\s\S]*?)\]",
        raw,
        re.DOTALL,
    )
    for category, skills_raw in skill_blocks:
        names = re.findall(r"name:\s*['\"](.+?)['\"]", skills_raw)
        if names:
            # Create more descriptive text for better embedding matching
            text = f"Skills — {category}: {', '.join(names)}"
            text += f"\nCarlos is proficient in the following {category.lower()}: {', '.join(names)}."
            chunks.append({
                "source": "cv",
                "section": "skills",
                "text": text,
            })

    return chunks


def collect_certifications() -> list[dict[str, str]]:
    """Read certifications from src/data/certs.ts."""
    certs_ts = PROJECT_DIR / "src" / "data" / "certs.ts"
    if not certs_ts.exists():
        return []

    raw = certs_ts.read_text(encoding="utf-8")

    # Parse each certification block individually to capture expired/credential info
    cert_blocks = re.findall(
        r"\{[^{}]*?name:\s*['\"](.+?)['\"][^{}]*?issuer:\s*['\"](.+?)['\"][^{}]*?year:\s*(\d+)[^{}]*?\}",
        raw,
        re.DOTALL,
    )
    chunks: list[dict[str, str]] = []
    for match_text, cert_match in zip(
        re.findall(r"\{[^{}]*?name:\s*['\"].+?['\"][^{}]*?\}", raw, re.DOTALL),
        cert_blocks,
    ):
        name, issuer, year = cert_match
        expired = "expired: true" in match_text or "expired:true" in match_text
        cred_m = re.search(r"credentialId:\s*['\"](.+?)['\"]", match_text)
        expires_m = re.search(r"expiresYear:\s*(\d+)", match_text)

        text = f"Certification: {name}, issued by {issuer} in {year}."
        if cred_m:
            text += f" Credential ID: {cred_m.group(1)}."
        if expires_m:
            text += f" Expires: {expires_m.group(1)}."
        if expired:
            text += " Status: EXPIRED."
        else:
            text += " Status: ACTIVE."

        chunks.append({
            "source": "certification",
            "section": "certification",
            "text": text,
        })
    return chunks


def collect_projects() -> list[dict[str, str]]:
    """Read projects from src/data/projects.ts."""
    proj_ts = PROJECT_DIR / "src" / "data" / "projects.ts"
    if not proj_ts.exists():
        return []

    raw = proj_ts.read_text(encoding="utf-8")
    projects = re.findall(
        r"name:\s*['\"](.+?)['\"].*?description:\s*\n?\s*['\"](.+?)['\"]",
        raw,
        re.DOTALL,
    )
    chunks: list[dict[str, str]] = []
    for name, desc in projects:
        chunks.append({
            "source": "project",
            "section": "project",
            "text": f"Project: {name}. {desc}",
        })
    return chunks


def collect_certification_docs() -> list[dict[str, str]]:
    """Read certification study guides."""
    chunks: list[dict[str, str]] = []
    study_guide = MONOREPO_DIR / "certificaciones" / "snowflakeIA" / "SnowPro_GenAI_Certification_Study_Guide.md"
    if study_guide.exists():
        text = study_guide.read_text(encoding="utf-8", errors="replace")
        chunks.append({
            "source": "certification",
            "section": "snowflake-genai-study",
            "text": text,
        })
    return chunks


# ── Chunking ──────────────────────────────────────────

def chunk_text(text: str, max_chars: int = MAX_CHARS_PER_CHUNK, overlap: int = OVERLAP_CHARS) -> list[str]:
    """Split text into overlapping chunks respecting paragraph boundaries."""
    # Split by double newlines first (paragraphs)
    paragraphs = re.split(r"\n{2,}", text.strip())
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) + 2 <= max_chars:
            current = f"{current}\n\n{para}".strip() if current else para
        else:
            if current:
                chunks.append(current)
            # If single paragraph is too long, split by sentences
            if len(para) > max_chars:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                current = ""
                for sent in sentences:
                    if len(current) + len(sent) + 1 <= max_chars:
                        current = f"{current} {sent}".strip() if current else sent
                    else:
                        if current:
                            chunks.append(current)
                        current = sent
            else:
                current = para

    if current:
        chunks.append(current)

    return chunks


# ── Embeddings via Cloudflare Workers AI ──────────────

def embed_texts(texts: list[str], account_id: str, api_token: str) -> list[list[float]]:
    """Generate embeddings using Cloudflare Workers AI API."""
    if not account_id or not api_token:
        # Return zero vectors as placeholder
        return [[0.0] * EMBEDDING_DIM for _ in texts]

    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{EMBEDDING_MODEL}"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        # Truncate very long texts for embedding
        batch_truncated = [t[:8000] for t in batch]

        resp = requests.post(url, headers=headers, json={"text": batch_truncated}, timeout=30)

        if resp.status_code != 200:
            print(f"  WARNING: Embedding API returned {resp.status_code}: {resp.text[:200]}")
            all_embeddings.extend([[0.0] * EMBEDDING_DIM for _ in batch])
            continue

        data = resp.json()
        if data.get("success"):
            vectors = data["result"]["data"]
            all_embeddings.extend(vectors)
        else:
            print(f"  WARNING: Embedding API error: {data.get('errors', [])}")
            all_embeddings.extend([[0.0] * EMBEDDING_DIM for _ in batch])

        if i + BATCH_SIZE < len(texts):
            import time
            time.sleep(0.2)  # rate limit courtesy

    return all_embeddings


# ── Main ──────────────────────────────────────────────

def main() -> None:
    load_env()
    account_id, api_token = get_cf_credentials()

    print("╔══════════════════════════════════════════╗")
    print("║  dataqbs.com — Knowledge Pipeline        ║")
    print("╚══════════════════════════════════════════╝")
    print()

    # 1. Collect sources
    print("📂 Collecting sources...")
    all_sources: list[dict[str, str]] = []

    cv = collect_cv_data()
    print(f"   CV data:          {len(cv)} entries")
    all_sources.extend(cv)

    certs = collect_certifications()
    print(f"   Certifications:   {len(certs)} entries")
    all_sources.extend(certs)

    projects = collect_projects()
    print(f"   Projects:         {len(projects)} entries")
    all_sources.extend(projects)

    readmes = collect_readmes()
    print(f"   READMEs:          {len(readmes)} files")
    all_sources.extend(readmes)

    knowledge_docs = collect_knowledge_docs()
    print(f"   Knowledge docs:   {len(knowledge_docs)} files")
    all_sources.extend(knowledge_docs)

    cert_docs = collect_certification_docs()
    print(f"   Cert study docs:  {len(cert_docs)} files")
    all_sources.extend(cert_docs)

    print(f"   Total raw:        {len(all_sources)} entries")
    print()

    # 2. Chunk
    print("✂️  Chunking...")
    chunks: list[dict[str, Any]] = []
    for src in all_sources:
        text_chunks = chunk_text(src["text"])
        for ci, chunk_text_str in enumerate(text_chunks):
            chunk_id = f"{src['source']}-{src.get('section', src.get('file', 'unknown'))}-{ci}"
            # Clean ID
            chunk_id = re.sub(r"[^a-zA-Z0-9_-]", "-", chunk_id)[:80]
            chunks.append({
                "id": chunk_id,
                "text": chunk_text_str,
                "metadata": {
                    "source": src["source"],
                    "section": src.get("section", ""),
                    "file": src.get("file", ""),
                },
            })
    print(f"   Total chunks:     {len(chunks)}")
    print()

    # 3. Generate embeddings
    print(f"🧠 Generating embeddings ({EMBEDDING_MODEL})...")
    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(texts, account_id, api_token)
    print(f"   Embeddings:       {len(embeddings)} vectors × {EMBEDDING_DIM} dims")
    print()

    # 4. Assemble output
    for i, chunk in enumerate(chunks):
        chunk["embedding"] = embeddings[i]

    knowledge = {
        "version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": EMBEDDING_MODEL,
        "dimensions": EMBEDDING_DIM,
        "total_chunks": len(chunks),
        "chunks": chunks,
    }

    # 5. Write output
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(knowledge, f, ensure_ascii=False, indent=None)

    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"✅ Written to: {OUTPUT_PATH}")
    print(f"   Size:             {size_kb:.1f} KB")
    print(f"   Chunks:           {len(chunks)}")
    print()
    print("Done!")


if __name__ == "__main__":
    main()
