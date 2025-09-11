"""
email_collector.main

Orquesta descarga, clasificación y validación de correos .eml
según el esquema de configuración nuevo en `config.yaml`.

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
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml
from dotenv import load_dotenv
from imap_tools import MailBox, A
from langdetect import detect

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


def classify_email(cfg: dict, rec: EmailRecord) -> str:
    rules = cfg.get("rules", {})
    cats = cfg.get("categories", ["Unknown"]) or ["Unknown"]

    subject = (rec.subject or "").lower()
    body = (rec.body or "").lower()
    headers = (rec.headers or "").lower()
    text = f"{subject} {body}"

    def has_any(text_: str, keywords: List[str]) -> bool:
        return any(kw.lower() in text_ for kw in (keywords or []))

    # Scam
    if "Scam" in cats and has_any(text, rules.get("scam_keywords", [])):
        return "Scam"
    # Spam
    if "Spam" in cats and has_any(text, rules.get("spam_keywords", [])):
        return "Spam"
    # Suspicious by headers
    if "Suspicious" in cats and has_any(headers, rules.get("suspicious_headers", [])):
        return "Suspicious"
    # Clean whitelist domain
    domain = rec.from_addr.split("@")[-1].lower() if "@" in rec.from_addr else ""
    if domain and domain in [d.lower() for d in rules.get("clean_senders_whitelist_domains", [])]:
        if "Clean" in cats:
            return "Clean"
    # Fallback
    return "Unknown"


def validate_email(cfg: dict, rec: EmailRecord) -> Tuple[bool, Optional[str]]:
    # Idioma
    lang_cfg = cfg.get("language_validation", {})
    if lang_cfg.get("enabled", False):
        body = (rec.body or "").strip()
        if not body and lang_cfg.get("accept_if_empty_body", True):
            pass
        else:
            text = (rec.subject or "") + "\n" + body
            try:
                detected = detect(text)
            except Exception:
                detected = ""
            expected = cfg.get("language", {}).get("code", "es")
            if detected != expected:
                return False, f"lang!={expected} ({detected})"
    # Validaciones mínimas de longitud
    rules = cfg.get("rules", {})
    min_body = int(rules.get("min_body_chars_for_real_mail", 0) or 0)
    min_subject = int(rules.get("min_subject_chars", 0) or 0)
    if min_subject and len((rec.subject or "").strip()) < min_subject:
        return False, f"subject<len({min_subject})"
    if min_body and len((rec.body or "").strip()) < min_body:
        return False, f"body<len({min_body})"
    return True, None


def save_eml(rec: EmailRecord, folder: Path, index: int, pattern: str, zero_pad_width: int, region: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    idx_str = str(index).zfill(zero_pad_width) if zero_pad_width and zero_pad_width > 0 else str(index)
    # Usar el correo de la cuenta utilizada para descargar, no el remitente
    email_for_name = (rec.account_email or rec.from_addr or "unknown").replace("/", "_")
    category = rec.category or "Unknown"
    filename = pattern.format(email=email_for_name, category=category, index=idx_str, region=region)
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
    with MailBox(host, port=port).login(user, password) as mailbox:
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

    # Ejecución completa
    saved: List[str] = []
    report: List[dict] = []
    summary_counts: Dict[str, int] = {"total": 0, "saved": 0, "duplicates": 0}
    per_category: Dict[str, int] = {}
    per_reason: Dict[str, int] = {}
    idx = 1
    seen_ids: set[str] = set()
    seen_hashes: set[int] = set()
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
            max_emails=max_per_acc,
            chunk_size=chunk_size,
        )
        for e in emails:
            # deduplicación simple por Message-ID o hash
            dedup_key = e.message_id or None
            if dedup_key and dedup_key in seen_ids:
                e.category = e.category or "Unknown"
                e.valid = False
                e.reason = "duplicate"
                summary_counts["duplicates"] += 1
                per_reason[e.reason] = per_reason.get(e.reason, 0) + 1
                report.append({
                    "account": acc["name"],
                    "provider": acc["provider"],
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
                        "account": acc["name"],
                        "provider": acc["provider"],
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
            # carpeta por cuenta y categoría
            account_folder = re.sub(r"[^A-Za-z0-9_-]+", "_", acc["name"]) or "account"
            target_folder = out_root / account_folder / (e.category or "Unknown")
            fn = save_eml(e, target_folder, idx, name_pattern, zero_pad, region)
            idx += 1
            saved.append(str(fn))
            summary_counts["saved"] += 1
            per_category[e.category or "Unknown"] = per_category.get(e.category or "Unknown", 0) + 1
            report.append({
                "account": acc["name"],
                "provider": acc["provider"],
                "subject": e.subject,
                "from": e.from_addr,
                "folder": e.folder,
                "category": e.category,
                "valid": e.valid,
                "reason": e.reason,
            })
            summary_counts["total"] += 1

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


if __name__ == "__main__":
    main()

