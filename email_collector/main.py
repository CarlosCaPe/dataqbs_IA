"""
DEPRECATED entrypoint.

This file is intentionally kept to avoid import errors but should not be used.
Use the canonical entrypoint at `email_collector/src/email_collector/main.py`.
"""

import sys

def main():
    msg = (
        "Deprecated module: email_collector/main.py.\n"
        "Please run the tool via Poetry or import from 'email_collector.src.email_collector.main'.\n"
        "Example: poetry run email-collect --precheck --config ..\\config.yaml\n"
    )
    print(msg)
    # Non-zero to discourage accidental use in scripts still pointing here
    raise SystemExit(2)


if __name__ == "__main__":
    main()

- Cuentas múltiples (gmail/hotmail) definidas en config + .env
- Carpetas por proveedor
- Reglas simples de clasificación (spam/scam/suspicious/clean)
- Validación de idioma
- Convención de nombres configurable

Ejemplos:
  poetry run email-collect --precheck --account gmail1
  poetry run email-collect --account hotmail

"""
from __future__ import annotations

import argparse
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from email import message_from_bytes, policy
import shutil

import yaml
from dotenv import load_dotenv
from imap_tools import MailBox, A
from langdetect import detect, detect_langs
import hashlib

def _canonical_text(subject: str, body: str) -> str:
    txt = f"{subject or ''}\n{body or ''}".lower()
    # remove urls
    txt = re.sub(r"https?://\S+", " ", txt)
    # collapse whitespace
    txt = re.sub(r"\s+", " ", txt).strip()
    # remove digits sequences >3
    txt = re.sub(r"\d{3,}", " ", txt)
    return txt

def _text_signature(text: str, shingle_size: int = 4) -> set:
    tokens = [t for t in re.split(r"[^a-z0-9]+", text) if t]
    if len(tokens) < shingle_size:
        return set(tokens)
    return {" ".join(tokens[i:i+shingle_size]) for i in range(len(tokens)-shingle_size+1)}

def is_similar(a: EmailRecord, b_sig: set, threshold: float = 0.85) -> bool:
    sig_a = _text_signature(_canonical_text(a.subject, a.body))
    if not sig_a or not b_sig:
        return False
    inter = len(sig_a & b_sig)
    union = len(sig_a | b_sig)
    if union == 0:
        return False
    return inter / union >= threshold

log = logging.getLogger("email_collector")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@dataclass
class EmailRecord:
    subject: str
    from_addr: str
    to: List[str]
    date: str
    raw_bytes: bytes
    size: int
    body: str
    headers: str
    folder: Optional[str] = None
    category: Optional[str] = None
    valid: Optional[bool] = None
    reason: Optional[str] = None
    provider: Optional[str] = None
    account_name: Optional[str] = None
    message_id: Optional[str] = None
    account_email: Optional[str] = None
    score: Optional[int] = None


def classify_email(cfg: dict, rec: EmailRecord) -> str:
    """Nuevo clasificador por scoring + hard rules.
    Devuelve: Scam | Sus | Spam | Clean | Unknown
    """
    subject = (rec.subject or "").lower()
    body = (rec.body or "").lower()
    headers = (rec.headers or "").lower()
    full_text = f"{subject} {body}".strip()

    rules = cfg.get("rules", {})
    classifier_cfg = cfg.get("classifier", {})
    scoring_cfg = classifier_cfg.get("scoring", {})
    thresholds = classifier_cfg.get("thresholds", {})
    hard = classifier_cfg.get("hard_rules", {})

    def has_any(text_: str, patterns: List[str]) -> bool:
        if not text_ or not patterns:
            return False
        return any(p.lower() in text_ for p in patterns if p)

    def count_matches(text_: str, patterns: List[str]) -> int:
        if not text_ or not patterns:
            return 0
        c = 0
        for p in patterns:
            if p and p.lower() in text_:
                c += 1
        return c

    # Señales base (algunas listas viejas pueden vaciarse)
    spam_keyword_count = count_matches(full_text, rules.get("spam_keywords", []))
    scam_keyword_count = count_matches(full_text, rules.get("scam_keywords", []))
    gambling_term_count = count_matches(full_text, rules.get("gambling_terms", []))
    url_shortener_count = count_matches(full_text, rules.get("url_shorteners", []))
    suspicious_header_count = count_matches(headers, rules.get("suspicious_headers", []))
    suspicious_marker_count = count_matches(full_text, rules.get("suspicious_markers", []))
    evasion_raw_patterns = rules.get("evasion_patterns", [])
    # regex search for evasion patterns
    evasion_pattern_count = 0
    for pat in evasion_raw_patterns:
        try:
            if re.search(pat, full_text):
                evasion_pattern_count += 1
        except re.error:
            if pat in full_text:
                evasion_pattern_count += 1
    urgency_patterns = rules.get("urgency_patterns", [])
    urgency_pattern_count = sum(1 for p in urgency_patterns if p and p.lower() in full_text)
    # Patrones de teléfono (configurables). Si no hay, usar regex genérica.
    phone_cfg_patterns = rules.get("phone_patterns", []) or []
    phone_pattern_count = 0
    if phone_cfg_patterns:
        for pat in phone_cfg_patterns:
            try:
                if re.search(pat, full_text, re.IGNORECASE):
                    phone_pattern_count = 1
                    break
            except re.error:
                if pat.lower() in full_text:
                    phone_pattern_count = 1
                    break
    else:
        phone_pattern_regex = re.compile(r"\b(?:\+?\d[\d .()\-]{7,}\d)\b")
        phone_pattern_count = 1 if phone_pattern_regex.search(full_text) else 0
    suspicious_domain_count = 1 if any(d in (rec.from_addr or "").lower() for d in rules.get("suspicious_domains", [])) else 0
    frequent_spam_domain_count = 1 if any(d in (rec.from_addr or "").lower() for d in rules.get("frequent_spam_domains", [])) else 0

    # Newsletter / marketing limpio
    clean_marketing_cfg = cfg.get("clean_marketing_rules", {})
    reputable_domains = [d.lower() for d in clean_marketing_cfg.get("reputable_domains", [])]
    subject_markers = [s.lower() for s in clean_marketing_cfg.get("subject_markers", [])]
    sender_domain = (rec.from_addr.split("@")[-1].lower() if rec.from_addr and "@" in rec.from_addr else "")
    is_newsletter = (sender_domain in reputable_domains) and any(m in subject for m in subject_markers)
    reputable_marketing_safe = 1 if (sender_domain in reputable_domains and url_shortener_count == 0 and scam_keyword_count == 0 and spam_keyword_count == 0) else 0

    # Transactional corto allowlist
    trans_cfg = cfg.get("transactional_short_allowlist", {})
    trans_trusted = [d.lower() for d in trans_cfg.get("trusted_domains", [])]
    trans_subject_needles = [s.lower() for s in trans_cfg.get("subject_must_match_one", [])]
    body_len = len(body.strip()) if body else 0
    is_transactional_short = (
        sender_domain in trans_trusted
        and body_len <= int(trans_cfg.get("max_body_chars", 220) or 220)
        and len(subject) >= int(trans_cfg.get("min_subject_chars", 3) or 3)
        and any(n in subject for n in trans_subject_needles)
    )

    # Scoring
    score = 0
    score += spam_keyword_count * int(scoring_cfg.get("spam_keyword", 0))
    score += scam_keyword_count * int(scoring_cfg.get("scam_keyword", 0))
    score += gambling_term_count * int(scoring_cfg.get("gambling_term", 0))
    score += url_shortener_count * int(scoring_cfg.get("url_shortener", 0))
    score += suspicious_header_count * int(scoring_cfg.get("suspicious_header", 0))
    score += suspicious_marker_count * int(scoring_cfg.get("suspicious_marker", 0))
    score += evasion_pattern_count * int(scoring_cfg.get("evasion_pattern", 0))
    score += urgency_pattern_count * int(scoring_cfg.get("urgency_pattern", 0))
    score += phone_pattern_count * int(scoring_cfg.get("phone_pattern", 0))
    # Bonuses
    if is_newsletter:
        score += int(scoring_cfg.get("reputable_domain_clean_bonus", 0))
    if is_transactional_short:
        score += int(scoring_cfg.get("transactional_allow_bonus", 0))

    # Palabras políticas (limpias)
    political_kw = rules.get("political_keywords", [])
    political_keywords_count = sum(1 for p in political_kw if p and p.lower() in full_text)

    # FedEx + shortener => clean combo (si config lo permite)
    fedex_shortener_combo = 0
    if 'fedex' in full_text and url_shortener_count > 0:
        treat_fedex = rules.get('domain_overrides', {}).get('treat_fedex_shortener_as_clean', False) if isinstance(rules.get('domain_overrides'), dict) else False
        if treat_fedex:
            fedex_shortener_combo = 1

    # Hard rules evaluation (simple parser for "metric>=N" terms AND separated by AND)
    metrics = {
        "scam_keywords": scam_keyword_count,
        "spam_keywords": spam_keyword_count,
        "gambling_terms": gambling_term_count,
        "url_shorteners": url_shortener_count,
        "suspicious_headers": suspicious_header_count,
        "suspicious_markers": suspicious_marker_count,
        "evasion_patterns": evasion_pattern_count,
        "urgency_patterns": urgency_pattern_count,
        "phone_patterns": phone_pattern_count,
        "suspicious_domains": suspicious_domain_count,
        "frequent_spam_domains": frequent_spam_domain_count,
        # extras sintéticos
        "newsletter": 1 if is_newsletter else 0,
        "transactional_short_allowlist matched": 1 if is_transactional_short else 0,
        "reputable_marketing_safe": reputable_marketing_safe,
        "political_keywords": 1 if political_keywords_count > 0 else 0,
        "fedex_shortener_combo": fedex_shortener_combo,
    }

    def rule_any(rule_block: List[dict]) -> bool:
        for cond in rule_block:
            exprs = cond.get("any", [])
            for expr in exprs:
                parts = [p.strip() for p in expr.split("AND")]
                ok = True
                for p in parts:
                    if ">=" in p:
                        left, right = [x.strip() for x in p.split(">=", 1)]
                        val = metrics.get(left, 0)
                        try:
                            needed = int(right)
                        except ValueError:
                            needed = 9999
                        if val < needed:
                            ok = False
                            break
                    else:
                        # Direct presence metric (expects value truthy)
                        val = metrics.get(p, 0)
                        if val <= 0:
                            ok = False
                            break
                if ok:
                    return True
        return False

    try:
        rec.score = score  # adjuntar score para auto-tune
    except Exception:
        pass
    if rule_any(hard.get("scam_if", [])):
        return "Scam"
    if rule_any(hard.get("spam_if", [])):
        return "Spam"
    if rule_any(hard.get("clean_if", [])):
        return "Clean"

    # --- Domain tie-break logic (no new labels) ---
    dc = cfg.get("domain_classification", {}) or {}
    sender_domain = (rec.from_addr.split('@')[-1].lower() if rec.from_addr and '@' in rec.from_addr else '')
    if sender_domain:
        if sender_domain in [d.lower() for d in dc.get('clean', [])]:
            # Prefer Clean unless very strong scam signals (handled later by thresholds if extreme)
            if scam_keyword_count < 2 and url_shortener_count == 0:
                return "Clean"
        elif sender_domain in [d.lower() for d in dc.get('clean_or_spam', [])]:
            # Marketing: decide after seeing spam vs scam counts (bias to Clean if low spam signals)
            if spam_keyword_count == 0 and scam_keyword_count == 0:
                return "Clean"
        elif sender_domain in [d.lower() for d in dc.get('clean_or_scam_sensitive', [])]:
            # Sensitive: downgrade borderline scam to Sus unless multiple strong indicators
            strong = 0
            strong += 1 if scam_keyword_count >= 2 else 0
            strong += 1 if url_shortener_count and (urgency_pattern_count or suspicious_marker_count) else 0
            if strong == 0:
                return "Clean"
            if strong == 1:
                return "Sus"
        elif sender_domain in [d.lower() for d in dc.get('sus_or_unknown', [])]:
            if scam_keyword_count == 0 and spam_keyword_count == 0 and url_shortener_count == 0:
                return "Unknown"
            return "Sus"
        elif sender_domain in [d.lower() for d in dc.get('sus_or_spam', [])]:
            if spam_keyword_count > 0:
                return "Spam"
            return "Sus"

    # Overrides de dominio (force clean salvo hard scam ya aplicado)
    domain_overrides = rules.get('domain_overrides', {}) if isinstance(rules.get('domain_overrides'), dict) else {}
    fcd = [d.lower() for d in domain_overrides.get('force_clean_domains', [])]
    fsd = [d.lower() for d in domain_overrides.get('force_spam_domains', [])]
    sender_domain = (rec.from_addr.split('@')[-1].lower() if rec.from_addr and '@' in rec.from_addr else '')
    # Si es dominio interno forzado clean y no hay combinación de >=2 señales scam fuertes, devolver Clean
    if sender_domain in fcd:
        strong_flags = 0
        strong_flags += 1 if scam_keyword_count >= 2 else 0
        strong_flags += 1 if url_shortener_count >= 1 and (urgency_pattern_count + suspicious_marker_count) >= 1 else 0
        strong_flags += 1 if phone_pattern_count and scam_keyword_count else 0
        if strong_flags <= 1:  # tolera una sola señal leve
            return 'Clean'
    # Fuerza Spam para dominios listados (marketing masivo), incluso si score alcanzaría Scam.
    if sender_domain in fsd:
        # si hubiera hard rule scam disparada, degradamos a Spam para evitar FP de Scam
        # (hard rules ya evaluadas arriba; aquí solo interceptamos antes de thresholds)
        return 'Spam'

    # --- Democión Scam->Spam para marketing confiable con señales débiles ---
    def weak_scam_signals() -> bool:
        strong = 0
        strong += 1 if scam_keyword_count >= 2 else 0
        strong += 1 if (url_shortener_count >= 1 and (urgency_pattern_count or suspicious_marker_count)) else 0
        strong += 1 if (phone_pattern_count and scam_keyword_count) else 0
        return strong <= 1
    marketing_like_domain = (
        sender_domain in reputable_domains or
        sender_domain in [d.lower() for d in dc.get('clean_or_spam', [])]
    )

    # Aplicar solo si la etiqueta habría sido Scam por score (no hard rule previa) y es dominio marketing
    if score >= int(thresholds.get("to_scam", 9999)) and marketing_like_domain and weak_scam_signals():
        return "Spam"

    if score >= int(thresholds.get("to_scam", 9999)):
        return "Scam"
    if score >= int(thresholds.get("to_sus", 9999)):
        return "Sus"
    if score >= int(thresholds.get("to_spam", 9999)):
        return "Spam"
    if is_newsletter or is_transactional_short or reputable_marketing_safe:
        return "Clean"
    # Fallback heurístico: dominio marketing creíble => Clean
    credible_marketing = [d.lower() for d in rules.get("credible_marketing_domains", [])]
    if sender_domain in credible_marketing:
        return "Clean"
    # gambling => Sus si nada más
    if gambling_term_count > 0:
        return "Sus"
    # frecuentes spam domain sin otras señales => Spam
    if frequent_spam_domain_count > 0:
        return "Spam"
    # Reducción de Unknown: si existe alguna señal leve, degradar a Spam/Sus
    if scam_keyword_count == 1 or suspicious_marker_count == 1 or url_shortener_count == 1:
        return "Sus"
    if spam_keyword_count == 1 or frequent_spam_domain_count == 1 or evasion_pattern_count == 1:
        return "Spam"
    return "Unknown"


def validate_email(cfg: dict, rec: EmailRecord) -> Tuple[bool, Optional[str]]:
    # Blacklist exclusions (early)
    excl = cfg.get("exclusions", {}).get("blacklist", [])
    if excl:
        subj_l = (rec.subject or "").lower()
        from_l = (rec.from_addr or "").lower()
        for rule in excl:
            pat = (rule.get("pattern") or "").lower()
            if pat and pat in from_l:
                subj_terms = [s.lower() for s in (rule.get("subject_contains") or [])]
                if not subj_terms or any(t in subj_l for t in subj_terms):
                    return False, rule.get("reason") or "blacklisted"
    # Exclusión de hilos reenviados/respondidos según prefijos configurados
    thread_prefixes = [p.strip().lower() for p in (cfg.get("exclude_thread_prefixes") or []) if p]
    if thread_prefixes:
        subj_l = (rec.subject or "").strip().lower()
        for pref in thread_prefixes:
            if subj_l.startswith(pref):
                return False, "thread_chain"
    lang_cfg = cfg.get("language_validation", {})
    if lang_cfg.get("enabled", False):
        body = (rec.body or "").strip()
        if body or not lang_cfg.get("accept_if_empty_body", True):
            text = (rec.subject or "") + "\n" + body
            try:
                expected = cfg.get("language", {}).get("code", "es")
                detected_list = detect_langs(text)
                prob_es = 0.0
                for langprob in detected_list:
                    # format like 'es:0.999'
                    parts = str(langprob).split(':')
                    if parts[0] == expected:
                        try:
                            prob_es = float(parts[1])
                        except ValueError:
                            prob_es = 0.0
                thresh = float(lang_cfg.get("threshold_percent_es", 0.7) or 0.7)
                if prob_es < thresh:
                    return False, f"lang_prob<{thresh:.2f} ({prob_es:.2f})"
            except Exception:
                detected = ""
                if expected != "es":  # fallback simple
                    pass
                else:
                    return False, "lang_detect_error"
    # Longitudes desde raíz (fallback a rules si legacy)
    min_body = int(cfg.get("min_body_chars_for_real_mail", cfg.get("rules", {}).get("min_body_chars_for_real_mail", 0)) or 0)
    min_subject = int(cfg.get("min_subject_chars", cfg.get("rules", {}).get("min_subject_chars", 0)) or 0)
    if min_subject and len((rec.subject or "").strip()) < min_subject:
        return False, f"subject<len({min_subject})"
    if min_body and len((rec.body or "").strip()) < min_body:
        return False, f"body<len({min_body})"
    return True, None


# Helper para extraer dominio base
import re as _re

def _base_domain(addr: str) -> str:
    if not addr:
        return "unknown"
    m = addr.split('@')
    dom = m[-1].lower().strip() if len(m) > 1 else addr.lower().strip()
    # quitar posibles etiquetas de nombre "Nombre <user@dom>"
    if '<' in dom and '>' in dom:
        dom = dom.split('<')[-1].split('>')[0]
    # eliminar caracteres no válidos en carpeta
    dom = _re.sub(r"[^a-z0-9._-]", "_", dom)
    # dominio base (mantener hasta dos labels finales si tld compuesto mx, com.mx, com)
    parts = dom.split('.')
    if len(parts) >= 3 and parts[-2] in ("com", "org", "net"):
        return '.'.join(parts[-3:])
    if len(parts) >= 2:
        return '.'.join(parts[-2:])
    return dom


def save_eml(rec: EmailRecord, folder: Path, index: int, pattern: str, zero_pad_width: int, region: str, cfg: Optional[dict] = None) -> Path:
    # Ajustar subcarpeta de dominio si toggle activo
    if cfg and cfg.get('output_structure', {}).get('domain_subfolders'):
        bd = _base_domain(rec.from_addr or rec.account_email or '')
        folder = folder / bd
    folder.mkdir(parents=True, exist_ok=True)
    idx_str = str(index).zfill(zero_pad_width) if zero_pad_width and zero_pad_width > 0 else str(index)
    # Usar el correo de la cuenta utilizada para descargar, no el remitente
    email_for_name = (rec.account_email or rec.from_addr or "unknown").replace("/", "_")
    category = rec.category or "Unknown"
    filename = pattern.format(email=email_for_name, category=category.replace("Suspicious", "Sus"), index=idx_str, region=region)
    fn = folder / filename
    with open(fn, "wb") as fh:
        fh.write(rec.raw_bytes)
    return fn


def fetch_emails_for_account(
    *,
    account_name: str,
    provider: str,
    host: str,
    port: int,
    user: str,
    password: str,
    folders: List[str],
    max_age_days: int,
    max_emails: int,
    chunk_size: int = 200,
) -> List[EmailRecord]:
    if not all([host, user, password]):
        raise RuntimeError("Faltan credenciales IMAP para la cuenta. Rellenar .env.")

    emails: List[EmailRecord] = []
    date_gte = None
    if max_age_days and max_age_days > 0:
        date_gte = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).date()

    log.info("Conectando a IMAP %s (%s)", host, account_name)

    # We'll wrap the login in a helper with fallback for hotmail
    def login_with_fallback(host, port, user, password):
        try:
            return MailBox(host, port=port).login(user, password)
        except Exception as e:
            log.warning("Error en login inicial: %s", e)
            # Si es Hotmail, intentar con host alternativo
            if "hotmail" in user.lower():
                fallback_host = "imap-mail.outlook.com"
                log.info("Intentando login con host alternativo: %s", fallback_host)
                return MailBox(fallback_host, port=port).login(user, password)
            raise

    with login_with_fallback(host, port, user, password) as mailbox:
        for folder in folders:
            try:
                mailbox.folder.set(folder)
            except Exception as e:
                log.warning("No se pudo abrir carpeta %s: %s", folder, e)
                continue
            # Criterio base
            criteria = 'ALL'
            if date_gte:
                criteria = A(date_gte=date_gte)

            # Obtener UIDs y leer en chunks para robustez
            try:
                uids = mailbox.uids(criteria)
            except Exception as e:
                log.warning("No se pudieron obtener UIDs en %s/%s: %s", account_name, folder, e)
                continue

            if max_emails and max_emails > 0:
                uids = uids[:max_emails]

            def chunk_iter(lst: List[str], n: int):
                n = max(1, int(n or 200))
                for i in range(0, len(lst), n):
                    yield lst[i:i+n]

            for uid_chunk in chunk_iter(uids, chunk_size):
                try:
                    # Buscar por UID en chunk: usar criterio raw 'UID seqset'
                    uid_seq = ",".join(uid_chunk)
                    uid_criteria = f"UID {uid_seq}"
                    for msg in mailbox.fetch(uid_criteria, bulk=False):
                        raw = msg.obj.as_bytes()
                        size = len(raw)
                        try:
                            headers_text = str(getattr(msg, "headers", ""))
                        except Exception:
                            headers_text = ""
                        to_list: List[str] = []
                        try:
                            to_val = getattr(msg, "to", None)
                            if isinstance(to_val, list):
                                to_list = to_val
                            elif isinstance(to_val, str):
                                to_list = [x.strip() for x in to_val.split(",") if x.strip()]
                        except Exception:
                            to_list = []
                        body_text = (msg.text or "") if getattr(msg, "text", None) else ""
                        msg_id = getattr(msg, "message_id", None)
                        rec = EmailRecord(
                            subject=msg.subject or "",
                            from_addr=msg.from_ or "",
                            to=to_list,
                            date=str(msg.date),
                            raw_bytes=raw,
                            size=size,
                            body=body_text,
                            headers=headers_text,
                            folder=folder,
                            provider=provider,
                            account_name=account_name,
                            message_id=msg_id,
                            account_email=user,
                        )
                        emails.append(rec)
                        if max_emails and max_emails > 0 and len(emails) >= max_emails:
                            return emails
                except Exception as e:
                    log.warning("Fallo al leer chunk (%s) en %s/%s: %s", len(uid_chunk), account_name, folder, e)
                    continue

    log.info("Descargados %d correos de %s", len(emails), account_name)
    return emails


def main(argv: Optional[List[str]] = None):
    parser = argparse.ArgumentParser(prog="email-collect")
    parser.add_argument("--precheck", action="store_true", help="Ejecutar solo pre-check")
    parser.add_argument("--config", default="config.yaml", help="Ruta a config.yaml")
    parser.add_argument("-v", "--verbose", action="store_true", help="Log detallado DEBUG")
    parser.add_argument("--reprocess-existing", action="store_true", help="Reclasificar .eml ya guardados")
    parser.add_argument("--auto-tune-thresholds", action="store_true", help="Ajustar thresholds para reducir Unknown")
    parser.add_argument("--target-unknown", type=float, default=0.30, help="Target proporción Unknown tras auto-tune")
    parser.add_argument(
        "--account",
        choices=["gmail1", "hotmail", "gmail2"],
        help="Selecciona la cuenta a usar (también se puede vía EMAIL_ACCOUNT)",
    )
    args = parser.parse_args(argv)

    load_dotenv()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Filtro opcional por --account o EMAIL_ACCOUNT (mapeo a user_env)
    selected = args.account or os.getenv("EMAIL_ACCOUNT")
    selected_user_env = None
    if selected == "gmail1":
        selected_user_env = "GMAIL1_USER"
    elif selected == "gmail2":
        selected_user_env = "GMAIL2_USER"
    elif selected == "hotmail":
        selected_user_env = "HOTMAIL_USER"

    cfg_path = Path(args.config)
    if not cfg_path.exists():
        cfg_path = Path(__file__).resolve().parent.parent / "config.yaml"
    cfg = load_config(str(cfg_path))

    accounts_cfg = cfg.get("accounts", [])
    folders_cfg: Dict[str, dict] = cfg.get("folders", {})
    max_age_days = int(cfg.get("max_age_days", 0) or 0)
    purge_days = int(cfg.get("purge_saved_older_than_days", 0) or 0)
    max_per_acc = int(cfg.get("max_emails_per_account", 0) or 0)
    fetch_cfg = cfg.get("fetch", {})
    chunk_size = int(fetch_cfg.get("chunk_size", 200) or 200)
    out_root = Path(cfg.get("output_path", "emails_out"))
    naming_cfg = cfg.get("naming", {})
    name_pattern = naming_cfg.get("pattern", "{email}_{category}_{index}_{region}.eml")
    zero_pad = int(naming_cfg.get("zero_pad_width", 0) or 0)
    region = cfg.get("language", {}).get("region_tag", "")

    # Determinar cuentas a procesar
    to_process = []
    for acc in accounts_cfg:
        # Skip disabled accounts if 'enabled' flag is present
        if acc.get("enabled") is False:
            continue
        if selected_user_env and acc.get("user_env") != selected_user_env:
            continue
        user = os.getenv(acc.get("user_env", ""), "")
        pwd = os.getenv(acc.get("pass_env", ""), "")
        if not user or not pwd:
            log.warning("Saltando cuenta %s por credenciales faltantes", acc.get("name"))
            continue
        provider = acc.get("provider", "")
        include_folders = folders_cfg.get(provider, {}).get("include", ["INBOX"]) if provider else ["INBOX"]
        to_process.append({
            "name": acc.get("name", user),
            "provider": provider,
            "host": acc.get("imap_server", ""),
            "port": int(acc.get("port", 993)),
            "user": user,
            "password": pwd,
            "folders": include_folders,
        })

    if args.precheck:
        # Precheck: listar conteos por carpeta (sin escribir archivos)
        log.info("Ejecutando precheck...")
        limit_pf = int(cfg.get("precheck", {}).get("max_list_per_folder", 10) or 10)
        sample_headers = bool(cfg.get("precheck", {}).get("log_headers_sample", False))
        summary = []
        for acc in to_process:
            emails = fetch_emails_for_account(
                account_name=acc["name"],
                provider=acc["provider"],
                host=acc["host"],
                port=acc["port"],
                user=acc["user"],
                password=acc["password"],
                folders=acc["folders"],
                max_age_days=max_age_days,
                max_emails=limit_pf,
                chunk_size=chunk_size,
            )
            item = {"account": acc["name"], "fetched": len(emails), "folders": acc["folders"]}
            if sample_headers and emails:
                item["sample_header"] = (emails[0].headers or "")[:300]
            summary.append(item)
        from pprint import pprint
        pprint(summary)
        return

    # Purga opcional de .eml previamente guardados más antiguos que purge_days
    if purge_days and purge_days > 0:
        cutoff_dt = datetime.now(timezone.utc) - timedelta(days=purge_days)
        root = Path(cfg.get("output_path", "emails_out"))
        if root.exists():
            removed = 0
            scanned = 0
            thread_removed = 0
            purge_threads = bool(cfg.get('purge_thread_chains', False))
            thread_prefixes = [p.strip().lower() for p in (cfg.get('exclude_thread_prefixes') or []) if p]
            for eml in root.rglob('*.eml'):
                scanned += 1
                try:
                    # Intentar extraer fecha del encabezado Date dentro del archivo
                    raw = eml.read_bytes()
                    try:
                        msg = message_from_bytes(raw, policy=policy.default)
                        date_hdr = msg.get('Date') or msg.get('date')
                        if date_hdr:
                            try:
                                msg_dt = parsedate_to_datetime(date_hdr)
                                if msg_dt.tzinfo is None:
                                    msg_dt = msg_dt.replace(tzinfo=timezone.utc)
                            except Exception:
                                msg_dt = None
                        else:
                            msg_dt = None
                    except Exception:
                        msg_dt = None
                    # Fallback: usar fecha de modificación del archivo
                    if not msg_dt:
                        mtime = datetime.fromtimestamp(eml.stat().st_mtime, tz=timezone.utc)
                        msg_dt = mtime
                    delete_flag = False
                    if msg_dt < cutoff_dt:
                        delete_flag = True
                    # Purga adicional por cadenas (subject) si se pide
                    if not delete_flag and purge_threads and thread_prefixes:
                        try:
                            from email import message_from_bytes as _mfb
                            msg2 = _mfb(raw, policy=policy.default)
                            subj2 = (msg2.get('Subject') or '').strip().lower()
                            if any(subj2.startswith(tp) for tp in thread_prefixes):
                                delete_flag = True
                                thread_removed += 1
                        except Exception:
                            pass
                    if delete_flag:
                        try:
                            eml.unlink()
                            removed += 1
                        except Exception:
                            pass
                except Exception:
                    continue
            log.info("Purga temporal: %d eliminados (edad / hilos) de %d examinados (>{} días, threads=%s, threads_elim=%d)".format(purge_days), removed, scanned, purge_threads, thread_removed)

    # Ejecución completa
    saved: List[str] = []
    report: List[dict] = []
    summary_counts: Dict[str, int] = {"total": 0, "saved": 0, "duplicates": 0, "invalid_skipped": 0, "similar_skipped": 0}
    per_category: Dict[str, int] = {}
    per_reason: Dict[str, int] = {}
    idx = 1
    seen_ids: set[str] = set()
    seen_hashes: set[int] = set()
    # store signatures of saved emails for similarity filtering
    saved_signatures: List[set] = []
    # Multihilo: descargar cada cuenta en paralelo
    fetch_workers = int(cfg.get("fetch", {}).get("parallel_accounts", 10) or 10)
    all_emails: List[EmailRecord] = []
    with ThreadPoolExecutor(max_workers=fetch_workers) as ex:
        future_map = {
            ex.submit(
                fetch_emails_for_account,
                account_name=acc["name"],
                provider=acc["provider"],
                host=acc["host"],
                port=acc["port"],
                user=acc["user"],
                password=acc["password"],
                folders=acc["folders"],
                max_age_days=max_age_days,
                max_emails=max_per_acc,
                chunk_size=chunk_size,
            ): acc for acc in to_process
        }
        for fut in as_completed(future_map):
            acc_info = future_map[fut]
            try:
                fetched_list = fut.result()
                all_emails.extend(fetched_list)
                log.info("Cuenta %s completada (%d correos)", acc_info["name"], len(fetched_list))
            except Exception as e:
                log.error("Error fetch cuenta %s: %s", acc_info["name"], e)

    # Primera pasada: clasificar (sin guardar) para permitir auto-tune
    for e in all_emails:
        e.category = classify_email(cfg, e)
    if args.auto_tune_thresholds and all_emails:
        classifier_cfg = cfg.get("classifier", {})
        thresholds = classifier_cfg.get("thresholds", {})
        # Copiar para modificar en memoria
        cur_scam = int(thresholds.get("to_scam", 7))
        cur_sus = int(thresholds.get("to_sus", 4))
        cur_spam = int(thresholds.get("to_spam", 3))
        def unknown_ratio() -> float:
            total = len(all_emails)
            if total == 0:
                return 0.0
            unk = sum(1 for x in all_emails if x.category == "Unknown")
            return unk / total
        # Ajustar bajando thresholds (sin cruzarlos) hasta target o límites
        guard_cycles = 0
        while unknown_ratio() > args.target_unknown and guard_cycles < 20:
            changed = False
            if cur_spam > 1:
                cur_spam -= 1
                changed = True
            if cur_sus > cur_spam + 0:  # mantener orden lógico
                cur_sus -= 1
                changed = True
            if cur_scam > cur_sus + 0:
                cur_scam -= 1
                changed = True
            if not changed:
                break
            # Reclasificar solo Unknown con nuevos thresholds temporales
            temp_thr = {"to_scam": cur_scam, "to_sus": cur_sus, "to_spam": cur_spam}
            classifier_cfg['thresholds'] = temp_thr
            for x in all_emails:
                if x.category == "Unknown":
                    x.category = classify_email(cfg, x)
            guard_cycles += 1
        log.info("Auto-tune thresholds aplicado: scam=%d sus=%d spam=%d unk_ratio=%.2f", cur_scam, cur_sus, cur_spam, unknown_ratio())
    # Preparar deduplicación y escritura
    for e in all_emails:
        acc_name = e.account_name or "unknown"
        acc_provider = e.provider or ""
        # deduplicación simple por Message-ID o hash
        dedup_key = e.message_id or None
        if dedup_key and dedup_key in seen_ids:
            e.category = e.category or "Unknown"
            e.valid = False
            e.reason = "duplicate"
            summary_counts["duplicates"] += 1
            per_reason[e.reason] = per_reason.get(e.reason, 0) + 1
            report.append({
                "account": acc_name,
                "provider": acc_provider,
                "subject": e.subject,
                "from": e.from_addr,
                "folder": e.folder,
                "category": e.category,
                "valid": e.valid,
                "reason": e.reason,
            })
            continue
        if not dedup_key:
            rb_hash = hash(e.raw_bytes)
            if rb_hash in seen_hashes:
                e.category = e.category or "Unknown"
                e.valid = False
                e.reason = "duplicate"
                summary_counts["duplicates"] += 1
                per_reason[e.reason] = per_reason.get(e.reason, 0) + 1
                report.append({
                    "account": acc_name,
                    "provider": acc_provider,
                    "subject": e.subject,
                    "from": e.from_addr,
                    "folder": e.folder,
                    "category": e.category,
                    "valid": e.valid,
                    "reason": e.reason,
                })
                continue
            seen_hashes.add(rb_hash)

            if dedup_key:
                seen_ids.add(dedup_key)
            e.category = classify_email(cfg, e)
            valid, reason = validate_email(cfg, e)
            e.valid = valid
            e.reason = reason
            summary_counts["total"] += 1
            if not valid:
                summary_counts["invalid_skipped"] += 1
                per_reason[reason or "invalid"] = per_reason.get(reason or "invalid", 0) + 1
                # Registrar en reporte aunque no se guarde el archivo
                report.append({
                    "account": acc_name,
                    "provider": acc_provider,
                    "subject": e.subject,
                    "from": e.from_addr,
                    "folder": e.folder,
                    "category": e.category,
                    "valid": e.valid,
                    "reason": e.reason,
                })
                continue
            # Similarity filter (skip near duplicates)
            canon_sig = _text_signature(_canonical_text(e.subject, e.body))
            is_dup = False
            sim_ratio_cfg = float(cfg.get("deduplication", {}).get("subject_fuzzy_ratio", 0.85) or 0.85)
            for sig in saved_signatures:
                if sig and canon_sig and (len(canon_sig) > 1) and (len(sig) > 1):
                    inter = len(canon_sig & sig)
                    union = len(canon_sig | sig)
                    if union and (inter / union) >= sim_ratio_cfg:
                        is_dup = True
                        break
        if is_dup:
            e.valid = False
            e.reason = "similar"
            summary_counts["similar_skipped"] += 1
            per_reason[e.reason] = per_reason.get(e.reason, 0) + 1
            report.append({
                "account": acc_name,
                "provider": acc_provider,
                "subject": e.subject,
                "from": e.from_addr,
                "folder": e.folder,
                "category": e.category,
                "valid": e.valid,
                "reason": e.reason,
            })
            continue
        # guardar solo si es válido
        account_folder = re.sub(r"[^A-Za-z0-9_-]+", "_", acc_name) or "account"
        target_folder = out_root / account_folder / (e.category or "Unknown")
        fn = save_eml(e, target_folder, idx, name_pattern, zero_pad, region, cfg)
        idx += 1
        saved.append(str(fn))
        summary_counts["saved"] += 1
        per_category[e.category or "Unknown"] = per_category.get(e.category or "Unknown", 0) + 1
        report.append({
            "account": acc_name,
            "provider": acc_provider,
            "subject": e.subject,
            "from": e.from_addr,
            "folder": e.folder,
            "category": e.category,
            "valid": e.valid,
            "reason": e.reason,
        })
        saved_signatures.append(canon_sig)

    # Reportes
    out_root.mkdir(parents=True, exist_ok=True)
    rpt_cfg = cfg.get("report", {})
    if rpt_cfg.get("create_json", True):
        fn_json = out_root / rpt_cfg.get("filename_json", "validation_report.json")
        import json
        payload = {"summary": {**summary_counts, "per_category": per_category, "per_reason": per_reason}, "items": report}
        with open(fn_json, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
    if rpt_cfg.get("create_txt", True):
        fn_txt = out_root / rpt_cfg.get("filename_txt", "validation_report.txt")
        with open(fn_txt, "w", encoding="utf-8") as fh:
            fh.write("Summary:\n")
            fh.write(f"  total: {summary_counts['total']}\n")
            fh.write(f"  saved: {summary_counts['saved']}\n")
            fh.write(f"  duplicates: {summary_counts['duplicates']}\n")
            fh.write("  per_category:\n")
            for k,v in sorted(per_category.items()):
                fh.write(f"    {k}: {v}\n")
            fh.write("  per_reason:\n")
            for k,v in sorted(per_reason.items()):
                fh.write(f"    {k}: {v}\n")
            fh.write("\nItems:\n")
            for r in report:
                fh.write(f"[{r['provider']}/{r['account']}] {r['category']} | {r['from']} | {r['subject']} | valid={r['valid']} | reason={r['reason']}\n")
    log.info("Run completo. Correos guardados: %d", len(saved))

    # Reprocesado existente si se solicita
    if args.reprocess_existing:
        def migrate_suspicious(root: Path):
            for acc_dir in root.glob('*'):
                if not acc_dir.is_dir():
                    continue
                old_dir = acc_dir / 'Suspicious'
                new_dir = acc_dir / 'Sus'
                if old_dir.exists():
                    new_dir.mkdir(parents=True, exist_ok=True)
                    for f in old_dir.glob('*.eml'):
                        dest = new_dir / f.name.replace('Suspicious', 'Sus')
                        try:
                            shutil.move(str(f), dest)
                        except Exception:
                            pass
                    try:
                        old_dir.rmdir()
                    except OSError:
                        pass
        migrate_suspicious(out_root)

        # Migración a subcarpetas de dominio si está activo el toggle
        if cfg.get('output_structure', {}).get('domain_subfolders'):
            moved_domain = 0
            for acc_dir in out_root.glob('*'):
                if not acc_dir.is_dir():
                    continue
                for cat_dir in acc_dir.glob('*'):
                    if not cat_dir.is_dir():
                        continue
                    # detectar .eml directamente en cat_dir (sin subcarpeta dominio)
                    for eml in list(cat_dir.glob('*.eml')):
                        try:
                            raw = eml.read_bytes()
                            msg = message_from_bytes(raw, policy=policy.default)
                            from_addr = msg.get('from') or ''
                            bd = _base_domain(from_addr)
                            target_dir = cat_dir / bd
                            target_dir.mkdir(parents=True, exist_ok=True)
                            new_path = target_dir / eml.name
                            shutil.move(str(eml), new_path)
                            moved_domain += 1
                        except Exception:
                            pass
            if moved_domain:
                log.info("Migrados %d correos a subcarpetas de dominio", moved_domain)

        def parse_eml(path: Path) -> Optional[EmailRecord]:
            try:
                raw = path.read_bytes()
                msg = message_from_bytes(raw, policy=policy.default)
                subject = msg.get('subject', '') or ''
                from_addr = msg.get('from', '') or ''
                # Extract plain text
                body = ''
                if msg.is_multipart():
                    for part in msg.walk():
                        ctype = part.get_content_type()
                        if ctype == 'text/plain':
                            try:
                                body += part.get_content()
                            except Exception:
                                pass
                else:
                    try:
                        body = msg.get_content()
                    except Exception:
                        body = ''
                rec = EmailRecord(
                    subject=subject,
                    from_addr=from_addr,
                    to=[],
                    date="",
                    raw_bytes=raw,
                    size=len(raw),
                    body=body or '',
                    headers='',
                    folder='',
                    provider='',
                    account_name='',
                    message_id=msg.get('Message-ID'),
                    account_email='',
                )
                return rec
            except Exception as e:
                log.debug("Error parse %s: %s", path, e)
                return None

        changed = 0
        total_files = 0
        # Blacklist removal config
        blacklist_rules = cfg.get("exclusions", {}).get("blacklist", [])
        def is_blacklisted_from_file(path: Path) -> bool:
            if not blacklist_rules:
                return False
            try:
                raw = path.read_bytes()
                msg = message_from_bytes(raw, policy=policy.default)
                from_addr = (msg.get('from') or '').lower()
                subject = (msg.get('subject') or '').lower()
                for r in blacklist_rules:
                    pat = (r.get('pattern') or '').lower()
                    if pat and pat in from_addr:
                        terms = [s.lower() for s in (r.get('subject_contains') or [])]
                        if not terms or any(t in subject for t in terms):
                            return True
            except Exception:
                return False
            return False
        for acc_dir in out_root.glob('*'):
            if not acc_dir.is_dir():
                continue
            for cat_dir in acc_dir.glob('*'):
                if not cat_dir.is_dir():
                    continue
                # Si hay subcarpetas de dominio, iterar dentro; si no, usar cat_dir directamente
                domain_mode = cfg.get('output_structure', {}).get('domain_subfolders')
                domain_dirs = list(cat_dir.glob('*')) if domain_mode else []
                eml_sources = []
                if domain_mode and domain_dirs:
                    for dsub in domain_dirs:
                        if dsub.is_dir():
                            eml_sources.append(dsub)
                else:
                    eml_sources.append(cat_dir)
                for source_dir in eml_sources:
                    for eml in source_dir.glob('*.eml'):
                        total_files += 1
                        # Blacklist purge
                        if is_blacklisted_from_file(eml):
                            try:
                                eml.unlink()
                            except Exception:
                                pass
                            continue
                        rec = parse_eml(eml)
                        if not rec:
                            continue
                        new_cat = classify_email(cfg, rec)
                        if new_cat != cat_dir.name:
                            target_dir = acc_dir / new_cat
                            if domain_mode:
                                bd = _base_domain(rec.from_addr or '')
                                target_dir = target_dir / bd
                            target_dir.mkdir(parents=True, exist_ok=True)
                            new_name = eml.name.replace(cat_dir.name, new_cat)
                            try:
                                shutil.move(str(eml), str(target_dir / new_name))
                                changed += 1
                            except Exception as e:
                                log.debug("No se pudo mover %s: %s", eml, e)
        log.info("Reproceso finalizado: %d archivos revisados, %d movidos", total_files, changed)

        # --- Reporte post-reproceso ---
        def build_post_reprocess_snapshot(root: Path):
            per_account: Dict[str, Dict[str, int]] = {}
            global_per_category: Dict[str, int] = {}
            total = 0
            scam_domain_counter: Dict[str, int] = {}
            for acc_dir in root.glob('*'):
                if not acc_dir.is_dir():
                    continue
                acc_name = acc_dir.name
                per_account.setdefault(acc_name, {})
                for cat_dir in acc_dir.glob('*'):
                    if not cat_dir.is_dir():
                        continue
                    cat = cat_dir.name
                    files = list(cat_dir.glob('*.eml'))
                    count = len(files)
                    if count == 0:
                        continue
                    per_account[acc_name][cat] = per_account[acc_name].get(cat, 0) + count
                    global_per_category[cat] = global_per_category.get(cat, 0) + count
                    total += count
                    if cat == 'Scam':
                        # extrae dominio remitente del nombre del archivo (patrón email_category...)
                        for f in files[:500]:  # limitar para rendimiento
                            parts = f.name.split('_')
                            if parts:
                                em = parts[0]
                                if '@' in em:
                                    dom = em.split('@')[-1].lower()
                                    scam_domain_counter[dom] = scam_domain_counter.get(dom, 0) + 1
            top_scam = sorted(scam_domain_counter.items(), key=lambda x: x[1], reverse=True)[:20]
            return {"per_account": per_account, "global_per_category": global_per_category, "total_files": total, "top_scam_domains": top_scam}

        snapshot = build_post_reprocess_snapshot(out_root)
        # Actualizar JSON existente (o crear) agregando clave post_reprocess
        try:
            import json, time
            rpt_cfg = cfg.get("report", {})
            fn_json = out_root / rpt_cfg.get("filename_json", "validation_report.json")
            data = {}
            if fn_json.exists():
                try:
                    data = json.loads(fn_json.read_text(encoding='utf-8'))
                except Exception:
                    data = {}
            data["post_reprocess"] = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "files_reclassified": changed,
                "files_scanned": total_files,
                **snapshot,
            }
            with open(fn_json, 'w', encoding='utf-8') as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
            # TXT append
            if rpt_cfg.get("create_txt", True):
                fn_txt = out_root / rpt_cfg.get("filename_txt", "validation_report.txt")
                with open(fn_txt, 'a', encoding='utf-8') as fh:
                    fh.write("\nPost-reprocess snapshot (" + data["post_reprocess"]["timestamp"] + ")\n")
                    fh.write(f"  scanned: {total_files}\n  moved: {changed}\n")
                    fh.write("  global_per_category:\n")
                    for k,v in sorted(snapshot["global_per_category"].items()):
                        fh.write(f"    {k}: {v}\n")
        except Exception as e:
            log.warning("No se pudo escribir reporte post-reproceso: %s", e)

