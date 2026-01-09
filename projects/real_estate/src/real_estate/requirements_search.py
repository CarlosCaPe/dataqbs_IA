import argparse
import json
import math
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.lower().strip()


def _to_float(val: Any) -> float | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        v = val.strip().replace(",", ".")
        try:
            return float(v)
        except Exception:
            return None
    return None


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected dict JSON in {path}")
    return data


def _iter_property_jsons(data_dir: Path) -> Iterable[Path]:
    for p in sorted(data_dir.glob("*.json")):
        # Skip obvious non-property JSONs if any
        if p.name.lower() == "listing_statuses.json":
            continue
        yield p


def _text_blob(prop: dict) -> str:
    parts: list[str] = []
    for key in ("title", "description", "property_type", "public_id", "internal_id"):
        v = prop.get(key)
        if isinstance(v, str) and v.strip():
            parts.append(v)
    loc = prop.get("location")
    if isinstance(loc, dict):
        for key in ("name", "street", "postal_code", "exterior_number", "interior_number"):
            v = loc.get(key)
            if isinstance(v, str) and v.strip():
                parts.append(v)
    # tags/features sometimes carry useful hints
    tags = prop.get("tags")
    if isinstance(tags, list):
        for t in tags:
            if isinstance(t, str) and t.strip():
                parts.append(t)
    feats = prop.get("features")
    if isinstance(feats, list):
        for f in feats:
            if isinstance(f, str) and f.strip():
                parts.append(f)
            elif isinstance(f, dict):
                name = f.get("name")
                if isinstance(name, str) and name.strip():
                    parts.append(name)
    return "\n".join(parts)


def _extract_height_m(text: str) -> float | None:
    t = _norm(text)
    # Common patterns: "altura 8 m", "8mts de altura", "altura mínima 5m"
    patterns = [
        r"altura\s*(?:minima|minima|mínima)?\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:m|mt|mts|metros)\b",
        r"(\d+(?:\.\d+)?)\s*(?:m|mt|mts|metros)\s*(?:de\s*)?altura\b",
        r"port[oó]n\s*(?:de\s*)?(\d+(?:\.\d+)?)\s*(?:m|mt|mts|metros)\b",
    ]
    vals: list[float] = []
    for pat in patterns:
        for m in re.finditer(pat, t):
            v = _to_float(m.group(1))
            if v is not None and 0 < v < 50:
                vals.append(v)
    return max(vals) if vals else None


def _extract_gate_height_m(text: str) -> float | None:
    t = _norm(text)
    # Examples: "Portón de 4x4.5 m2 de altura", "porton 5m"
    vals: list[float] = []
    # Try WxH patterns first
    # Note: many listings mistakenly write "m2" when they mean meters in a height context.
    for m in re.finditer(r"port[oó]n\s*(?:de\s*)?(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*(?:m2|m\^2|m|mt|mts|metros)\b", t):
        h = _to_float(m.group(2))
        if h is not None and 0 < h < 50:
            vals.append(h)
    # Then simple "porton ... 4.5 m" patterns
    for m in re.finditer(r"port[oó]n\s*(?:de\s*)?(\d+(?:\.\d+)?)\s*(?:m2|m\^2|m|mt|mts|metros)\b", t):
        h = _to_float(m.group(1))
        if h is not None and 0 < h < 50:
            vals.append(h)
    return max(vals) if vals else None


def _zone_match(text_norm: str, zone: str) -> bool:
    """Match zone by full phrase OR by all significant tokens.

    Keeps matching strict but robust to extra words (e.g., "Av. Periférico Sur").
    """
    z = _norm(zone)
    if not z:
        return False
    if z in text_norm:
        return True
    tokens = [t for t in re.split(r"\s+", z) if len(t) >= 3]
    return bool(tokens) and all(t in text_norm for t in tokens)


def _text_has_220v(text: str) -> bool:
    t = _norm(text)
    return bool(re.search(r"\b220\s*v\b|\b220v\b|\btrifasica\b|\btrifasica\b", t))


def _text_has_rent_to_own(text: str) -> bool:
    t = _norm(text)
    return any(
        kw in t
        for kw in (
            "opcion a compra",
            "opción a compra",
            "renta con opcion a compra",
            "renta con opción a compra",
            "rent to own",
            "lease to own",
        )
    )


def _area_m2(prop: dict, prefer: str | None) -> float | None:
    construction = _to_float(prop.get("construction_size"))
    lot = _to_float(prop.get("lot_size"))
    if prefer == "construction":
        return construction if construction is not None else lot
    if prefer == "lot":
        return lot if lot is not None else construction
    # Default: prefer construction
    return construction if construction is not None else lot


def _dimensions_from_prop_or_text(prop: dict, text: str) -> tuple[float, float] | None:
    w = _to_float(prop.get("lot_width"))
    l = _to_float(prop.get("lot_length"))
    if w is not None and l is not None:
        return (w, l)

    t = _norm(text)
    # e.g. "12x16", "12 x 16", "12×16"
    m = re.search(r"\b(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\b", t)
    if not m:
        return None
    a = _to_float(m.group(1))
    b = _to_float(m.group(2))
    if a is None or b is None:
        return None
    return (a, b)


def _get_operation_amount_mxn(prop: dict, op_type: str) -> float | None:
    ops = prop.get("operations")
    if not isinstance(ops, list):
        return None
    for op in ops:
        if not isinstance(op, dict):
            continue
        if op.get("type") != op_type:
            continue
        if (op.get("currency") or "").upper() != "MXN":
            continue
        amount = _to_float(op.get("amount"))
        if amount is not None:
            return amount
    return None


@dataclass(frozen=True)
class MatchResult:
    ok: bool
    reasons: list[str]


@dataclass(frozen=True)
class EvalResult:
    ok: bool
    reasons: list[str]
    warnings: list[str]


def _humanize_reason(reason: str) -> str:
    r = reason.strip()
    if r.startswith("zone:"):
        return "Zona: fuera de las zonas aceptadas"
    if r.startswith("property_type:"):
        return "Tipo: no es bodega/terreno según el requerimiento"
    if r.startswith("operation:"):
        return "Operación: no coincide (renta/venta)"
    if r.startswith("rent_mxn:"):
        return "Renta: fuera de rango o no indicada"
    if r.startswith("sale_mxn:"):
        return "Compra: fuera de rango o no indicada"
    if r.startswith("area_m2:"):
        return "Superficie: fuera de rango o no indicada"
    if r.startswith("height_m:"):
        return "Altura: fuera de rango o no indicada"
    if r.startswith("gate_height_m:"):
        return "Portón: altura insuficiente o no indicada (obligatorio)"
    if r.startswith("220v:"):
        return "Electricidad: no se encontró 220V (obligatorio)"
    if r.startswith("rent_to_own:"):
        return "Esquema: no se encontró 'renta con opción a compra' (obligatorio)"
    if r.startswith("dimensions:"):
        return "Medidas: no coincide con 12x16 (o no indicada)"
    if r.startswith("keyword_all missing:"):
        return "Texto: falta palabra obligatoria"
    if r.startswith("keyword_any:"):
        return "Texto: no contiene palabras clave requeridas"
    return r


def _humanize_warning(warn: str) -> str:
    w = warn.strip()
    if w.startswith("soft_keyword_all missing:"):
        return "Uso: no se menciona un término esperado"
    if w.startswith("soft_keyword_any:"):
        return "Uso: no se menciona (maquila/alimentos/gym), revisar manualmente"
    return w


def _passed_checks(profile: dict, reasons: list[str]) -> list[str]:
    failed_prefixes = (
        "zone:",
        "property_type:",
        "operation:",
        "rent_mxn:",
        "sale_mxn:",
        "area_m2:",
        "height_m:",
        "gate_height_m:",
        "220v:",
        "rent_to_own:",
        "dimensions:",
    )
    failed = set()
    for r in reasons:
        for pfx in failed_prefixes:
            if r.startswith(pfx):
                failed.add(pfx)

    checks: list[tuple[str, str]] = []
    checks.append(("zone:", "Zona"))
    checks.append(("rent_mxn:", "Renta"))
    checks.append(("sale_mxn:", "Compra"))
    checks.append(("area_m2:", "Superficie"))
    checks.append(("height_m:", "Altura"))
    if bool(profile.get("require_gate_height_at_least_min_height")):
        checks.append(("gate_height_m:", "Portón"))
    if bool(profile.get("require_220v")):
        checks.append(("220v:", "220V"))
    if bool(profile.get("require_rent_to_own")):
        checks.append(("rent_to_own:", "Opción a compra"))
    if isinstance(profile.get("dimensions_m"), dict):
        checks.append(("dimensions:", "Medidas"))

    out: list[str] = []
    for pfx, label in checks:
        # only report checks that apply (sale/rent presence depends on profile)
        if pfx == "sale_mxn:" and profile.get("sale_mxn") is None:
            continue
        if pfx == "rent_mxn:" and profile.get("rent_mxn") is None:
            continue
        if pfx not in failed:
            out.append(label)
    return out


def _prop_line_md(
    prop: dict,
    profile: dict,
    res: EvalResult,
    failed_checks: int | None = None,
) -> str:
    pid = prop.get("public_id") or prop.get("id") or "(sin id)"
    title = prop.get("title") or "(sin título)"
    url = prop.get("public_url") or ""
    rent = _get_operation_amount_mxn(prop, "rental")
    sale = _get_operation_amount_mxn(prop, "sale")
    prefer = (profile.get("area_m2") or {}).get("prefer") if isinstance(profile.get("area_m2"), dict) else None
    area = _area_m2(prop, prefer)
    height = _extract_height_m(_text_blob(prop))
    gate_h = _extract_gate_height_m(_text_blob(prop))

    cumple = _passed_checks(profile, res.reasons)
    no_cumple = [_humanize_reason(r) for r in res.reasons]
    avisos = [_humanize_warning(w) for w in res.warnings]

    lines: list[str] = []
    head = f"- **{pid}** — {title}"
    if failed_checks is not None:
        head += f" (fallas: {failed_checks})"
    lines.append(head)
    if url:
        lines.append(f"  - Link: {url}")
    meta: list[str] = []
    if rent is not None:
        meta.append(f"Renta: ${rent:,.0f} MXN")
    if sale is not None:
        meta.append(f"Compra: ${sale:,.0f} MXN")
    if area is not None:
        meta.append(f"Superficie: {area:.1f} m²")
    if height is not None:
        meta.append(f"Altura: {height:.1f} m")
    if gate_h is not None:
        meta.append(f"Portón: {gate_h:.1f} m")
    if meta:
        lines.append("  - Datos: " + " | ".join(meta))
    if cumple:
        lines.append("  - Sí cumple: " + ", ".join(cumple))
    if no_cumple:
        lines.append("  - No cumple: " + "; ".join(no_cumple))
    if avisos:
        lines.append("  - Revisar: " + "; ".join(avisos))
    return "\n".join(lines)


def _looks_residential(tnorm: str) -> bool:
    """Heuristic: exclude listings that are clearly residential (casa/depa).

    EasyBroker's property_type can be misclassified; for 'solo bodegas' reports we
    prefer to drop obvious residential ads rather than let them pollute results.
    """

    strong_terms = (
        "recamara",
        "recamaras",
        "recámara",
        "recámaras",
        "cocina",
        "cocina integral",
        "sala comedor",
        "departamento",
        "depto",
        "coto",
        "roof",
        "roof garden",
        "amueblad",
        "fraccionamiento",
        "jardin",
        "jardín",
        "alberca",
        "terraza",
        "vestidor",
        "casa habitacion",
        "casa habitación",
    )
    if any(term in tnorm for term in strong_terms):
        return True

    # "casa" by itself is ambiguous; require a second residential hint.
    if "casa" in tnorm:
        soft_terms = ("recamara", "cocina", "departamento", "coto", "fraccionamiento")
        return any(term in tnorm for term in soft_terms)

    return False


def _write_report_md(
    out_path: Path,
    profile_name: str,
    profile: dict,
    scanned: int,
    matched: list[tuple[dict, EvalResult]],
    misses: list[tuple[int, dict, EvalResult]],
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(_render_report_section_md(profile_name, profile, scanned, matched, misses)) + "\n", encoding="utf-8")


def _render_report_section_md(
    profile_name: str,
    profile: dict,
    scanned: int,
    matched: list[tuple[dict, EvalResult]],
    misses: list[tuple[int, dict, EvalResult]],
) -> list[str]:
    desc = profile.get("description") if isinstance(profile.get("description"), str) else ""
    content: list[str] = []
    content.append(f"## {profile_name}")
    if desc:
        content.append(f"**Requerimiento**: {desc}")
    content.append(f"**Propiedades analizadas**: {scanned}")
    content.append(f"**Coincidencias exactas**: {len(matched)}")
    content.append("")

    content.append("### Coincidencias exactas")
    if not matched:
        content.append("No se encontraron coincidencias exactas con este dataset.")
    else:
        for prop, res in matched:
            content.append(_prop_line_md(prop, profile, res))
    content.append("")
    content.append("### Casi coincidencias (para revisión)")
    if not misses:
        content.append("No hay candidatos para mostrar.")
    else:
        misses_sorted = sorted(misses, key=lambda x: (x[0], str((x[1].get('public_id') or x[1].get('id') or ''))))
        for failed_checks, prop, res in misses_sorted[:10]:
            content.append(_prop_line_md(prop, profile, res, failed_checks=failed_checks))
    content.append("")
    return content


def _in_range(name: str, val: float | None, r: dict | None) -> tuple[bool, str | None]:
    if r is None:
        return True, None
    if val is None:
        return False, f"{name}: missing"
    mn = _to_float(r.get("min"))
    mx = _to_float(r.get("max"))
    if mn is not None and val < mn:
        return False, f"{name}: {val} < {mn}"
    if mx is not None and val > mx:
        return False, f"{name}: {val} > {mx}"
    return True, None


def _match_profile(prop: dict, profile: dict) -> EvalResult:
    reasons: list[str] = []
    warnings: list[str] = []
    text = _text_blob(prop)
    tnorm = _norm(text)

    # zones
    zones = profile.get("zones_any")
    if isinstance(zones, list) and zones:
        zones_norm = [_norm(z) for z in zones if isinstance(z, str) and z.strip()]
        if zones_norm and not any(_zone_match(tnorm, z) for z in zones_norm):
            reasons.append("zone: no match")

    # property type
    ptype_any = profile.get("property_type_any")
    if isinstance(ptype_any, list) and ptype_any:
        ptype_norms = [_norm(x) for x in ptype_any if isinstance(x, str) and x.strip()]
        prop_ptype = _norm(str(prop.get("property_type") or ""))
        # STRICT: match ONLY against the property_type field (do not infer type from description)
        if ptype_norms and not any(x in prop_ptype for x in ptype_norms):
            reasons.append("property_type: not allowed")

    # operations and money
    op_mode = profile.get("operation")
    rent = _get_operation_amount_mxn(prop, "rental")
    sale = _get_operation_amount_mxn(prop, "sale")

    if op_mode == "rental":
        if rent is None:
            reasons.append("operation: missing rental")
    elif op_mode == "sale":
        if sale is None:
            reasons.append("operation: missing sale")
    elif op_mode == "rental_or_sale":
        if rent is None and sale is None:
            reasons.append("operation: missing rental/sale")

    ok, why = _in_range("rent_mxn", rent, profile.get("rent_mxn"))
    if not ok and why:
        reasons.append(why)
    ok, why = _in_range("sale_mxn", sale, profile.get("sale_mxn"))
    if not ok and why:
        reasons.append(why)

    # area
    area_cfg = profile.get("area_m2")
    prefer = None
    if isinstance(area_cfg, dict):
        prefer = area_cfg.get("prefer")
    area = _area_m2(prop, prefer)
    ok, why = _in_range("area_m2", area, area_cfg if isinstance(area_cfg, dict) else None)
    if not ok and why:
        reasons.append(why)

    # height
    min_h = _to_float(profile.get("min_height_m"))
    if min_h is not None:
        h = _extract_height_m(text)
        require_explicit = bool(profile.get("require_explicit_height"))
        if h is None:
            if require_explicit:
                reasons.append("height_m: missing")
        else:
            if h < min_h:
                reasons.append(f"height_m: {h} < {min_h}")

        # Gate/portón height ("incluido el portón")
        if bool(profile.get("require_gate_height_at_least_min_height")):
            gh = _extract_gate_height_m(text)
            require_gate_explicit = bool(profile.get("require_explicit_gate_height"))
            if gh is None:
                if require_gate_explicit:
                    reasons.append("gate_height_m: missing")
            else:
                if gh < min_h:
                    reasons.append(f"gate_height_m: {gh} < {min_h}")

    # 220V
    if bool(profile.get("require_220v")):
        if not _text_has_220v(text):
            reasons.append("220v: not found")

    # rent-to-own
    if bool(profile.get("require_rent_to_own")):
        if not _text_has_rent_to_own(text):
            reasons.append("rent_to_own: not found")

    # keywords
    kw_all = profile.get("keywords_all")
    if isinstance(kw_all, list) and kw_all:
        for kw in kw_all:
            if isinstance(kw, str) and kw.strip() and _norm(kw) not in tnorm:
                reasons.append(f"keyword_all missing: {kw}")

    kw_any = profile.get("keywords_any")
    if isinstance(kw_any, list) and kw_any:
        kn = [_norm(kw) for kw in kw_any if isinstance(kw, str) and kw.strip()]
        if kn and not any(k in tnorm for k in kn):
            reasons.append("keyword_any: none matched")

    # Soft checks (evaluated + reported, but do not exclude)
    skw_all = profile.get("soft_keywords_all")
    if isinstance(skw_all, list) and skw_all:
        for kw in skw_all:
            if isinstance(kw, str) and kw.strip() and _norm(kw) not in tnorm:
                warnings.append(f"soft_keyword_all missing: {kw}")

    skw_any = profile.get("soft_keywords_any")
    if isinstance(skw_any, list) and skw_any:
        kn = [_norm(kw) for kw in skw_any if isinstance(kw, str) and kw.strip()]
        if kn and not any(k in tnorm for k in kn):
            warnings.append("soft_keyword_any: none matched")

    # dimensions
    dim = profile.get("dimensions_m")
    if isinstance(dim, dict):
        w_req = _to_float(dim.get("width"))
        l_req = _to_float(dim.get("length"))
        tol = _to_float(dim.get("tolerance")) or 0.5
        got = _dimensions_from_prop_or_text(prop, text)
        if w_req is None or l_req is None:
            reasons.append("dimensions: invalid requirement")
        elif got is None:
            reasons.append("dimensions: missing")
        else:
            w, l = got
            # accept either orientation
            def close(a: float, b: float) -> bool:
                return math.isfinite(a) and math.isfinite(b) and abs(a - b) <= tol

            if not ((close(w, w_req) and close(l, l_req)) or (close(w, l_req) and close(l, w_req))):
                reasons.append(f"dimensions: got {w}x{l} (need {w_req}x{l_req}±{tol})")

    return EvalResult(ok=(len(reasons) == 0), reasons=reasons, warnings=warnings)


def _resolve_data_dir(project_root: Path, config: dict, override: str | None) -> Path:
    if override:
        p = (project_root / override).resolve() if not Path(override).is_absolute() else Path(override)
        return p

    cfg_dir = config.get("BASE_JSON_FOLDER")
    candidates: list[Path] = []
    if isinstance(cfg_dir, str) and cfg_dir.strip():
        candidates.append((project_root / cfg_dir).resolve())

    # common fallback(s)
    candidates.append((project_root / "easybrokers" / "properties" / "data").resolve())
    candidates.append((project_root / "properties" / "data").resolve())

    for c in candidates:
        if c.exists() and c.is_dir():
            return c

    # default to first candidate (will error later)
    return candidates[0] if candidates else (project_root / "easybrokers" / "properties" / "data")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Exact requirements search over EasyBroker JSONs")
    parser.add_argument("--profile", default=None, help="Profile name in requirements.json (e.g. bodega_chica)")
    parser.add_argument("--profiles", nargs="+", default=None, help="Multiple profile names to run in one go")
    parser.add_argument("--requirements", default="requirements.json", help="Path to requirements.json")
    parser.add_argument("--config", default="config.json", help="Path to config.json")
    parser.add_argument("--data-dir", default=None, help="Override data dir (folder with *.json)")
    parser.add_argument("--limit", type=int, default=50, help="Max matches to print")
    parser.add_argument("--explain", action="store_true", help="Print reasons for each match")
    parser.add_argument("--top-misses", type=int, default=10, help="Also print N closest non-matches (fewest failed checks)")
    parser.add_argument("--report", default=None, help="Write a promoter-friendly Markdown report to this path")
    args = parser.parse_args(argv)

    project_root = Path(__file__).resolve().parents[2]
    cfg_path = (project_root / args.config).resolve() if not Path(args.config).is_absolute() else Path(args.config)
    req_path = (project_root / args.requirements).resolve() if not Path(args.requirements).is_absolute() else Path(args.requirements)

    if not cfg_path.exists():
        raise SystemExit(f"config not found: {cfg_path}")
    if not req_path.exists():
        raise SystemExit(f"requirements not found: {req_path}")

    config = _load_json(cfg_path)
    requirements = _load_json(req_path)
    profiles = requirements.get("profiles")
    if not isinstance(profiles, dict):
        raise SystemExit("requirements.json must contain a top-level 'profiles' object")

    run_profiles: list[str] = []
    if args.profiles:
        run_profiles = [p for p in args.profiles if isinstance(p, str) and p.strip()]
    elif isinstance(args.profile, str) and args.profile.strip():
        run_profiles = [args.profile.strip()]
    else:
        raise SystemExit("Provide --profile or --profiles")

    data_dir = _resolve_data_dir(project_root, config, args.data_dir)
    if not data_dir.exists():
        raise SystemExit(f"data dir not found: {data_dir}")

    # If report is requested, build one combined promoter-friendly file.
    report_path: Path | None = None
    if args.report:
        report_path = Path(args.report)
        if not report_path.is_absolute():
            report_path = (project_root / report_path).resolve()

    combined_report: list[str] = []
    if report_path is not None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        combined_report.append("# REPORTE — Requerimiento de Bodegas")
        combined_report.append("")
        combined_report.append(f"**Fecha**: {now}")
        combined_report.append(f"**Dataset**: {data_dir}")
        combined_report.append("")

    for profile_name in run_profiles:
        profile = profiles.get(profile_name)
        if not isinstance(profile, dict):
            raise SystemExit(f"profile not found: {profile_name}")

        ptype_any = profile.get("property_type_any")
        ptype_norms: list[str] = []
        if isinstance(ptype_any, list) and ptype_any:
            ptype_norms = [_norm(x) for x in ptype_any if isinstance(x, str) and x.strip()]

        total = 0
        matched: list[tuple[dict, EvalResult]] = []
        misses: list[tuple[int, dict, EvalResult]] = []
        for p in _iter_property_jsons(data_dir):
            total += 1
            try:
                prop = _load_json(p)
            except Exception:
                continue

            # For bodega profiles, drop listings that clearly look residential.
            # This keeps the output "solo bodegas" even if EasyBroker type is wrong.
            if profile_name.startswith("bodega_"):
                tnorm = _norm(_text_blob(prop))
                if _looks_residential(tnorm):
                    continue

            # STRICT type gating: if the profile specifies property_type_any,
            # only consider properties whose property_type matches one of those values.
            if ptype_norms:
                prop_ptype = _norm(str(prop.get("property_type") or ""))
                if not any(x in prop_ptype for x in ptype_norms):
                    continue

            res = _match_profile(prop, profile)
            if res.ok:
                matched.append((prop, res))
            else:
                misses.append((len(res.reasons), prop, res))

        print(f"Profile: {profile_name}")
        desc = profile.get("description")
        if isinstance(desc, str) and desc.strip():
            print(f"Desc: {desc}")
        print(f"Data: {data_dir}")
        print(f"Scanned: {total} | Matches: {len(matched)}")

        # Console output remains as before (matches + closest misses)
        for prop, res in matched[: max(args.limit, 0)]:
            pid = prop.get("public_id") or prop.get("id") or "(no id)"
            title = prop.get("title") or "(no title)"
            url = prop.get("public_url") or ""
            rent = _get_operation_amount_mxn(prop, "rental")
            sale = _get_operation_amount_mxn(prop, "sale")
            area = _area_m2(prop, (profile.get("area_m2") or {}).get("prefer") if isinstance(profile.get("area_m2"), dict) else None)
            print("-")
            print(f"{pid} | {title}")
            if rent is not None:
                print(f"  rent_mxn: {rent}")
            if sale is not None:
                print(f"  sale_mxn: {sale}")
            if area is not None:
                print(f"  area_m2: {area}")
            if url:
                print(f"  url: {url}")
            if args.explain:
                for r in res.reasons:
                    print(f"  reason: {r}")
                for w in res.warnings:
                    print(f"  warn: {w}")

        if args.top_misses and misses:
            misses.sort(key=lambda x: (x[0], str((x[1].get('public_id') or x[1].get('id') or ''))))
            print("\nClosest non-matches:")
            for count, prop, res in misses[: max(args.top_misses, 0)]:
                pid = prop.get("public_id") or prop.get("id") or "(no id)"
                title = prop.get("title") or "(no title)"
                url = prop.get("public_url") or ""
                print("-")
                print(f"{pid} | {title} | failed_checks: {count}")
                if url:
                    print(f"  url: {url}")
                if args.explain:
                    for r in res.reasons:
                        print(f"  reason: {r}")
                    for w in res.warnings:
                        print(f"  warn: {w}")

        if report_path is not None:
            combined_report.extend(_render_report_section_md(profile_name, profile, total, matched, misses))

    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("\n".join(combined_report) + "\n", encoding="utf-8")
        print(f"\nReport written: {report_path}")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
