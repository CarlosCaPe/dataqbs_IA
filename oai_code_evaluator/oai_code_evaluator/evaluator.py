from __future__ import annotations
import statistics
import re
from typing import Dict, List, Any
import hashlib
from jinja2 import Template
from .models import EvaluationInput, EvaluationResult, DimensionCorrection
from .rubric import DIMENSIONS, suggest_adjustment, clamp
from .config_loader import ConfigBundle

class Evaluator:
    """Configurable evaluator (YAML-driven).

    Pipeline order:
        1. Dimension base adjustment (heuristic or dimensions.yaml)
        2. Apply rating rules (rules.yaml)
        3. Normalize ranking (ranking.yaml)
        4. Improve rewrite (rewrite.yaml + rewrite_rules)
        5. Prompt validation / feedback
        6. Compute global summary
    """

    def __init__(self, config: ConfigBundle | None = None):
        self.config = config

    # ----------------- preprocessing -----------------
    def _preprocess(self, sub) -> Dict[str, Any]:
        """Extract reusable signals for rule evaluation.

        Returns dict with:
            text_space, text_lower, rewrite_lower, length_total, response_count
        """
        text_space = "\n".join([r.text for r in sub.responses]) + "\n" + sub.rewrite_preferred
        signals = {
            "text_space": text_space,
            "text_lower": text_space.lower(),
            "rewrite_lower": sub.rewrite_preferred.lower(),
            "length_total": len(text_space),
            "response_count": len(sub.responses),
        }
        return signals

    # ----------------- rating adjustment -----------------
    def _adjust_dimensions(self, sub) -> Dict[str, DimensionCorrection]:
        corrected: Dict[str, DimensionCorrection] = {}
        dim_conf = (self.config.dimensions if self.config else {}) or {}
        dims_meta = dim_conf.get("dimensions", {})
        pull_fraction = dim_conf.get("adjustment", {}).get("pull_fraction", 0.4)
        for dim in DIMENSIONS:
            original_val = getattr(sub.ratings, dim)
            if dim in dims_meta:
                ideal = dims_meta[dim].get("ideal", 4.0)
                tol = dims_meta[dim].get("tolerance", 1.0)
                if abs(original_val - ideal) <= tol:
                    updated_val = original_val
                    rationale = "Within tolerance"
                else:
                    updated_val = clamp(original_val + pull_fraction * (ideal - original_val))
                    rationale = f"Adjusted toward ideal {ideal} with fraction {pull_fraction}"
            else:
                # fallback to original heuristic
                updated_val = suggest_adjustment(original_val, dim)
                rationale = "Default heuristic"
            corrected[dim] = DimensionCorrection(
                original=original_val,
                updated=updated_val,
                rationale=rationale,
            )
        return corrected

    # ----------------- rule engine (simplified) -----------------
    def _apply_rating_rules(self, corrected: Dict[str, DimensionCorrection], sub, rules_conf: Dict[str, Any], comments: List[str], fired_rules: List[Dict[str, Any]], signals: Dict[str, Any], state: Dict[str, Any]):
        options = rules_conf.get("options", {})
        stop_after_first = options.get("stop_after_first", False)
        dedupe = options.get("dedupe_comments", False)
        seen_comments = set()
        for rule in rules_conf.get("rating_rules", []):
            when = rule.get("when", {})
            matched, detail = self._match_conditions(when, sub, signals)
            if not matched:
                continue
            actions = rule.get("actions", {})
            explanation = {"id": rule.get("id"), "type": "rating", "detail": detail, "actions": []}
            adj = actions.get("adjust_dimension")
            if adj:
                dim = adj.get("dimension")
                delta = float(adj.get("delta", 0))
                if dim in corrected:
                    prev = corrected[dim].updated
                    new_val = clamp(prev + delta)
                    corrected[dim].rationale += f" | Rule {rule['id']} (Δ {delta:+.2f})"
                    corrected[dim].updated = new_val
                    explanation["actions"].append({"adjust_dimension": {"dimension": dim, "from": prev, "to": new_val, "delta": delta}})
            if actions.get("add_comment"):
                msg = actions["add_comment"]
                if (not dedupe) or (msg not in seen_comments):
                    comments.append(msg)
                    seen_comments.add(msg)
                explanation["actions"].append({"add_comment": msg})
            if actions.get("add_comment_template"):
                template_str = actions["add_comment_template"]
                # Available variables: corrected (dimension->post-adjust value), signals, detail
                context = {"signals": signals, "detail": detail, "corrected": {k: v.updated for k, v in corrected.items()}}
                try:
                    msg = Template(template_str).render(**context)
                except Exception as e:  # pragma: no cover - fallback
                    msg = f"[TEMPLATE_ERROR {e}] {template_str}"
                if (not dedupe) or (msg not in seen_comments):
                    comments.append(msg)
                    seen_comments.add(msg)
                explanation["actions"].append({"add_comment_template": msg})
            if actions.get("set_flag"):
                flag_name = actions["set_flag"]
                state.setdefault("flags", {})[flag_name] = True
                explanation["actions"].append({"set_flag": flag_name})
            if actions.get("increment_score") is not None:
                inc = float(actions.get("increment_score", 0))
                state["score"] = state.get("score", 0.0) + inc
                explanation["actions"].append({"increment_score": inc})
            if actions.get("assign_label"):
                label = actions["assign_label"]
                state["label"] = label
                explanation["actions"].append({"assign_label": label})
            fired_rules.append(explanation)
            if stop_after_first:
                break

    def _match_conditions(self, conds: Dict[str, Any], sub, signals: Dict[str, Any]) -> tuple[bool, Dict[str, Any]]:
        text_space = signals["text_space"]
        text_lower = signals["text_lower"]
        rewrite_lower = signals["rewrite_lower"]
        detail: Dict[str, Any] = {}
        # OR blocks (any_of): list of condition dicts, at least one must pass
        any_of = conds.get("any_of")
        if any_of:
            any_pass = False
            sub_details = []
            for block in any_of:
                m, d = self._match_conditions(block, sub, signals)
                sub_details.append(d)
                if m:
                    any_pass = True
            detail["any_of"] = sub_details
            if not any_pass:
                return False, detail
        # Basic implementations
        if "response_contains_any" in conds:
            matches = [w for w in conds["response_contains_any"] if w.lower() in text_lower]
            detail["response_contains_any"] = matches
            if not matches:
                return False, detail
        if "preferred_rewrite_missing_substring" in conds:
            if not any(s.lower() in rewrite_lower for s in conds["preferred_rewrite_missing_substring"]):
                # Actually condition says missing? interpret as: all substrings absent
                if all(s.lower() not in rewrite_lower for s in conds["preferred_rewrite_missing_substring"]):
                    detail["preferred_rewrite_missing_substring"] = "all_missing"
                else:
                    return False, detail
        if "rewrite_regex_any" in conds:
            reg_hits = [p for p in conds["rewrite_regex_any"] if re.search(p, sub.rewrite_preferred)]
            detail["rewrite_regex_any"] = reg_hits
            if not reg_hits:
                return False, detail
        if "not_contains_any" in conds:
            forbidden = [w for w in conds["not_contains_any"] if w.lower() in text_lower]
            detail["not_contains_any_found"] = forbidden
            if forbidden:
                return False, detail
        # Numeric comparisons: total length of responses+rewrite
        length_total = signals["length_total"]
        if "min_total_length" in conds:
            detail["length_total"] = length_total
            if length_total < conds["min_total_length"]:
                return False, detail
        if "max_total_length" in conds:
            detail["length_total"] = length_total
            if length_total > conds["max_total_length"]:
                return False, detail
        # Dimension comparisons (after initial adjustment only; uses original ratings too?)
        if "dimension_gt" in conds:
            for dim, thr in conds["dimension_gt"].items():
                val = getattr(sub.ratings, dim, None)
                if val is None or val <= thr:
                    detail.setdefault("dimension_gt_fail", {})[dim] = val
                    return False, detail
                detail.setdefault("dimension_gt_pass", {})[dim] = val
        if "dimension_lt" in conds:
            for dim, thr in conds["dimension_lt"].items():
                val = getattr(sub.ratings, dim, None)
                if val is None or val >= thr:
                    detail.setdefault("dimension_lt_fail", {})[dim] = val
                    return False, detail
                detail.setdefault("dimension_lt_pass", {})[dim] = val
        return True, detail

    # ----------------- ranking normalization -----------------
    def _normalize_ranking(self, sub, ranking_conf: Dict[str, Any]) -> tuple[list[str], str]:
        response_ids = [r.id for r in sub.responses]
        ranking = []
        seen = set()
        had_dup = False
        for r in sub.ranking:
            if r in response_ids:
                if r in seen:
                    had_dup = True
                    if not ranking_conf.get("allow_duplicates", False):
                        continue
                ranking.append(r)
                seen.add(r)
        missing = [rid for rid in response_ids if rid not in ranking]
        feedback_key = "complete"
        if missing and ranking_conf.get("corrections", {}).get("append_missing", True):
            ranking.extend(missing)
            feedback_key = "missing_ids"
        if had_dup:
            feedback_key = "had_duplicates"
        templates = ranking_conf.get("feedback_templates", {})
        feedback = templates.get(feedback_key, "Ranking processed.")
        return ranking, feedback

    # ----------------- rewrite improvements -----------------
    def _improve_rewrite(self, sub, rewrite_conf: Dict[str, Any], rules_conf: Dict[str, Any]) -> str:
        text = sub.rewrite_preferred.strip()
        min_len = rewrite_conf.get("min_length", 0)
        if len(text) < min_len and rewrite_conf.get("add_note_if_short", True):
            text += "\n\n" + rewrite_conf.get("note_text", "Expand content.")
        # apply rewrite_rules with simple conditions
        for rule in rules_conf.get("rewrite_rules", []):
            when = rule.get("when", {})
            cond_ok = True
            if when.get("ends_without_punct"):
                if text.endswith(('.', '!', '?')):
                    cond_ok = False
            if when.get("shorter_than_min"):
                if len(text) >= min_len:
                    cond_ok = False
            if not cond_ok:
                continue
            actions = rule.get("actions", {})
            if actions.get("append_text"):
                text += actions["append_text"]
            if actions.get("append_note"):
                text += "\n\n" + rewrite_conf.get("note_text", "Expand content.")
        return text

    # ----------------- prompt feedback -----------------
    def _prompt_feedback(self, sub, prompt_conf: Dict[str, Any]) -> str:
        required = prompt_conf.get("required_fields", [])
        missing = [f for f in required if not getattr(sub, f, None)]
        if missing:
            return prompt_conf.get("feedback", {}).get("missing_field", "Missing fields: {missing}").format(missing=",".join(missing))
        # Validate allowed labels
        for field, allow in prompt_conf.get("label_checks", {}).items():
            val = getattr(sub, field, None)
            if allow and val and val not in allow:
                return prompt_conf.get("feedback", {}).get("invalid_label", "Invalid label {field}={value}").format(field=field, value=val)
        return prompt_conf.get("feedback", {}).get("ok", "Prompt valid.")

    def _final_decision(self, state: Dict[str, Any], rules_conf: Dict[str, Any]) -> Dict[str, Any]:
        decision_conf = rules_conf.get("decision", {})
        score = state.get("score")
        label = state.get("label")
        if score is not None and decision_conf.get("score_thresholds"):
            # Determine label by thresholds (descending)
            thresholds = decision_conf["score_thresholds"]
            # Expect mapping label->min_score
            chosen = None
            for lab, thr in sorted(thresholds.items(), key=lambda x: x[1], reverse=True):
                if score >= thr:
                    chosen = lab
                    break
            if chosen:
                label = chosen
        return {"score": score, "label": label, "flags": state.get("flags", {})}

    def _config_hash(self) -> str | None:
        if not self.config:
            return None
        # Deterministic hash of concatenated sorted JSON dumps of bundle sections
        import json
        parts = []
        for key in sorted(self.config.keys()):
            parts.append(json.dumps(self.config[key], sort_keys=True, ensure_ascii=False))
        digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
        return digest

    def evaluate(self, data: EvaluationInput) -> EvaluationResult:
        sub = data.submission
        comments: List[str] = []
        # Preprocess signals
        signals = self._preprocess(sub)
        state: Dict[str, Any] = {}
        # 1. Dimension adjustment
        corrected = self._adjust_dimensions(sub)
        # 2. Rating rules
        rules_conf = (self.config.rules if self.config else {}) or {}
        fired_rules: List[Dict[str, Any]] = []
        self._apply_rating_rules(corrected, sub, rules_conf, comments, fired_rules, signals, state)
        # 3. Ranking
        ranking_conf = (self.config.ranking if self.config else {}) or {}
        ranking, ranking_feedback = self._normalize_ranking(sub, ranking_conf)
        # 4. Rewrite
        rewrite_conf = (self.config.rewrite if self.config else {}) or {}
        rewrite_final = self._improve_rewrite(sub, rewrite_conf, rules_conf)
        # 5. Prompt feedback
        prompt_conf = (self.config.prompt if self.config else {}) or {}
        prompt_feedback = self._prompt_feedback(sub, prompt_conf)
        # 6. Global summary
        deltas = [abs(c.updated - c.original) for c in corrected.values()]
        mean_delta = statistics.mean(deltas) if deltas else 0.0
        global_summary = (
            f"Adjustments applied to {len(corrected)} dimensions. mean Δ={mean_delta:.2f}. "
            + (f"Comments: {' | '.join(comments)}" if comments else "")
        )
        # 7. Final decision
        decision = self._final_decision(state, rules_conf)
        # 8. Audit metadata
        meta = {
            "rule_version": rules_conf.get("version"),
            "config_hash": self._config_hash(),
            "signals": {k: v for k, v in signals.items() if k in ("length_total", "response_count")},
        }
        return EvaluationResult(
            corrected_ratings=corrected,
            corrected_ranking=ranking,
            ranking_feedback=ranking_feedback,
            rewrite_final=rewrite_final,
            prompt_feedback=prompt_feedback,
            global_summary=global_summary,
            fired_rules=fired_rules,
            score=decision.get("score"),
            flags=decision.get("flags", {}),
            label=decision.get("label"),
            meta=meta,
        )
