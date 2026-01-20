from __future__ import annotations

import json
from pathlib import Path

TARGET_IDS = [6, 8, 12, 14, 18, 23, 25, 36, 38, 43, 45, 47, 58]


def load_question_subset(bank_path: Path) -> list[dict]:
    data = json.loads(bank_path.read_text(encoding="utf-8"))
    by_id = {q["id"]: q for q in data.get("questions", []) if isinstance(q, dict) and isinstance(q.get("id"), int)}
    missing = [qid for qid in TARGET_IDS if qid not in by_id]
    if missing:
        raise SystemExit(f"Missing question IDs in bank: {missing}")
    return [by_id[qid] for qid in TARGET_IDS]


def assert_no_placeholders(rendered_text: str, *, qid: int | None = None) -> None:
    bad_markers = ["[Ver PDF original]", "⚠️", "No se extrajeron correctamente"]
    found = [m for m in bad_markers if m in rendered_text]
    if found:
        context = f" (qid={qid})" if qid is not None else ""
        snippet = rendered_text
        if len(snippet) > 600:
            snippet = snippet[:600] + "..."
        raise AssertionError(
            f"Found placeholder/warning markers in render output{context}: {found}\n"
            f"Rendered snippet:\n{snippet}"
        )


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    app_path = script_dir / "streamlit_exam_app.py"
    bank_path = script_dir.parent.parent / "GES-C01_Exam_Sample_Questions.json"

    subset = load_question_subset(bank_path)

    try:
        from streamlit.testing.v1 import AppTest  # type: ignore
    except Exception as e:  # pragma: no cover
        raise SystemExit(
            "streamlit.testing.v1 is not available in this Streamlit version. "
            "Upgrade Streamlit (>=1.26-ish) or run a manual spot-check in the browser.\n"
            f"Import error: {e}"
        )

    at = AppTest.from_file(str(app_path))
    at.run()

    # Start Practice mode
    at.button(key="btn_practice").click().run()

    # Force the app to focus on the target questions in a deterministic order.
    at.session_state["questions"] = subset
    at.session_state["current_question"] = 0
    at.session_state["answers"] = {}
    at.session_state["marked"] = set()
    at.session_state["mode"] = "practice"
    at.session_state["exam_started"] = True
    at.session_state["exam_finished"] = False
    at.session_state["show_explanation"] = {}
    at.session_state["start_time"] = 0.0
    at.session_state["time_limit"] = None
    at.run()

    # Practice: each question should render without placeholder warnings.
    for idx, q in enumerate(subset):
        qid = q["id"]
        at.session_state["current_question"] = idx
        at.run()

        rendered = "\n".join([m.value for m in at.markdown])
        assert_no_placeholders(rendered, qid=qid)

        # Toggle explanation (practice mode) and ensure we get an explanation box.
        at.button(key=f"show_{qid}").click().run()
        rendered2 = "\n".join([m.value for m in at.markdown])
        assert "Explicación:" in rendered2
        assert_no_placeholders(rendered2, qid=qid)

    # Start Exam mode (no immediate explanation toggle should be present).
    at2 = AppTest.from_file(str(app_path))
    at2.run()
    at2.button(key="btn_exam").click().run()
    at2.session_state["questions"] = subset
    at2.session_state["current_question"] = 0
    at2.session_state["answers"] = {}
    at2.session_state["marked"] = set()
    at2.session_state["mode"] = "exam"
    at2.session_state["exam_started"] = True
    at2.session_state["exam_finished"] = False
    at2.session_state["show_explanation"] = {}
    at2.session_state["start_time"] = 0.0
    at2.session_state["time_limit"] = 115 * 60
    at2.run()

    # Ensure exam mode does not render the Show Answer toggle.
    for idx, q in enumerate(subset):
        qid = q["id"]
        at2.session_state["current_question"] = idx
        at2.run()
        # In exam mode, the show button should not exist.
        if any(b.key == f"show_{qid}" for b in at2.button):
            raise AssertionError(f"Show Answer button unexpectedly present in exam mode for qid={qid}")

    print("OK: Practice and Exam flows render cleanly for target question IDs.")


if __name__ == "__main__":
    main()
