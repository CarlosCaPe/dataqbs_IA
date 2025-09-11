"""
email_collector.main

Contiene la orquestación principal con clases:
- EmailDownloader
- EmailClassifier
- EmailValidator
- PreChecker

Rellena credenciales en `.env` y reglas en `config.yaml`.
"""
from __future__ import annotations

import argparse
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

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
    folder: Optional[str] = None
    category: Optional[str] = None
    valid: Optional[bool] = None
    reason: Optional[str] = None


class EmailDownloader:
    def __init__(self, cfg: dict):
        self.cfg = cfg

    def connect_and_fetch(self, limit: Optional[int] = None) -> List[EmailRecord]:
        host = os.getenv("IMAP_HOST") or self.cfg.get("imap", {}).get("host")
        port = int(os.getenv("IMAP_PORT") or self.cfg.get("imap", {}).get("port", 993))
        folder = os.getenv("IMAP_FOLDER") or self.cfg.get("imap", {}).get("folder", "INBOX")

        user = os.getenv("IMAP_USER")
        password = os.getenv("IMAP_PASSWORD")
        if not all([host, user, password]):
            raise RuntimeError("Faltan credenciales IMAP. Rellenar .env o variables de entorno.")

        emails: List[EmailRecord] = []
        log.info("Conectando a IMAP %s %s", host, folder)
        with MailBox(host, port=port).login(user, password, initial_folder=folder) as mailbox:
            criteria = A()
            for idx, msg in enumerate(mailbox.fetch(criteria)):
                if limit and idx >= limit:
                    break
                raw = msg.obj.as_bytes()
                size = len(raw)
                rec = EmailRecord(
                    subject=msg.subject or "",
                    from_addr=msg.from_ or "",
                    to=(msg.to or "").split(",") if msg.to else [],
                    date=str(msg.date),
                    raw_bytes=raw,
                    size=size,
                )
                emails.append(rec)

        log.info("Descargados %d correos", len(emails))
        return emails


class EmailClassifier:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.categories = cfg.get("classification", {}).get("categories", [])

    def classify(self, rec: EmailRecord) -> str:
        text = (rec.subject or "") + " " + rec.from_addr
        text = text.lower()
        for cat in self.categories:
            for pat in cat.get("patterns", []):
                if re.search(re.escape(pat).lower(), text):
                    return cat.get("name")
        return self.cfg.get("classification", {}).get("default_folder", "otros")


class EmailValidator:
    def __init__(self, cfg: dict):
        self.cfg = cfg

    def validate(self, rec: EmailRecord) -> (bool, Optional[str]):
        max_mb = self.cfg.get("validation", {}).get("max_size_mb", 25)
        if rec.size > max_mb * 1024 * 1024:
            return False, f"size>{max_mb}MB"

        allowed = self.cfg.get("validation", {}).get("require_from_domain", [])
        if allowed:
            domain = rec.from_addr.split("@")[-1] if "@" in rec.from_addr else ""
            if domain not in allowed:
                return False, f"domain {domain} not allowed"

        return True, None


class PreChecker:
    def __init__(self, cfg: dict):
        self.cfg = cfg

    def run(self, downloader: EmailDownloader, classifier: EmailClassifier, validator: EmailValidator):
        limit = self.cfg.get("precheck", {}).get("max_emails_preview", 20)
        emails = downloader.connect_and_fetch(limit=limit)
        out = []
        for e in emails:
            try:
                txt = (e.subject or "")
                lang = detect(txt) if txt.strip() else ""
            except Exception:
                lang = ""
            cat = classifier.classify(e)
            valid, reason = validator.validate(e)
            out.append({"subject": e.subject, "from": e.from_addr, "lang": lang, "category": cat, "valid": valid, "reason": reason})

        from pprint import pprint
        pprint(out)
        return out


def save_eml(rec: EmailRecord, folder: Path):
    folder.mkdir(parents=True, exist_ok=True)
    subj = (rec.subject or "no-subject").strip().replace("/", "_")
    fn = folder / f"{subj[:80]}-{abs(hash(rec.from_addr))}.eml"
    with open(fn, "wb") as fh:
        fh.write(rec.raw_bytes)
    return fn


def main(argv: Optional[List[str]] = None):
    parser = argparse.ArgumentParser(prog="email-collect")
    parser.add_argument("--precheck", action="store_true", help="Ejecutar solo pre-check")
    parser.add_argument("--config", default="config.yaml", help="Ruta a config.yaml")
    args = parser.parse_args(argv)

    load_dotenv()
    cfg_path = Path(args.config)
    if not cfg_path.exists():
        cfg_path = Path(__file__).resolve().parent.parent / "config.yaml"
    cfg = load_config(str(cfg_path))

    downloader = EmailDownloader(cfg)
    classifier = EmailClassifier(cfg)
    validator = EmailValidator(cfg)
    prechecker = PreChecker(cfg)

    if args.precheck:
        log.info("Ejecutando precheck...")
        prechecker.run(downloader, classifier, validator)
        return

    log.info("Ejecutando run completo...")
    emails = downloader.connect_and_fetch(limit=None)
    out_folder = Path(cfg.get("report", {}).get("output_folder", "emails_out"))
    saved = []
    report = []
    for e in emails:
        e.category = classifier.classify(e)
        valid, reason = validator.validate(e)
        e.valid = valid
        e.reason = reason
        if cfg.get("report", {}).get("save_eml", True):
            fn = save_eml(e, out_folder / e.category)
            saved.append(str(fn))
        report.append({"subject": e.subject, "from": e.from_addr, "category": e.category, "valid": e.valid, "reason": e.reason})

    import json

    rpt_fn = out_folder / "report.json"
    out_folder.mkdir(parents=True, exist_ok=True)
    with open(rpt_fn, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    log.info("Run completo. Correos guardados: %d. Report: %s", len(saved), rpt_fn)


if __name__ == "__main__":
    main()
