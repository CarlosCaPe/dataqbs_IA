import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

QUESTION_BANK_PATH = Path(__file__).resolve().parents[2] / "GES-C01_Exam_Sample_Questions.json"

# Regenerated to fix OCR truncation/missing options/correctAnswer mismatches.
# Each item includes structured options and at least one docs.snowflake.com source.
REGENERATED_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": 6,
        "topic": "Cortex LLM Functions",
        "question": "You want consistent, machine-parseable JSON from a Cortex LLM call and you also want the SQL to be resilient to generation failures. Which actions help achieve this? (Select all that apply)",
        "options": {
            "A": "Use the COMPLETE function with the response_format option and provide a JSON schema.",
            "B": "In the JSON schema, list required keys under required so the model must include them.",
            "C": "Use TRY_COMPLETE so the function returns NULL instead of raising an error when it cannot perform the operation.",
            "D": "Set temperature to 0 to reduce randomness and improve determinism.",
            "E": "Rely on TRY_COMPLETE to return a structured error object instead of text when failures occur.",
        },
        "correctAnswer": "A,B,C,D",
        "multipleSelect": True,
        "explanation": "COMPLETE supports response_format with a JSON schema, and you can mark properties as required to encourage consistent JSON outputs. TRY_COMPLETE behaves like COMPLETE but returns NULL instead of raising an error if it cannot perform the operation. Setting temperature to 0 reduces randomness.",
        "source": [
            "https://docs.snowflake.com/en/sql-reference/functions/complete-snowflake-cortex",
            "https://docs.snowflake.com/en/sql-reference/functions/try_complete-snowflake-cortex",
        ],
    },
    {
        "id": 8,
        "topic": "Cortex Search",
        "question": "You are planning a Cortex Search service over a table that changes frequently. Which statements about requirements and cost/performance are true? (Select all that apply)",
        "options": {
            "A": "Change tracking must be enabled on the underlying object(s) used as the service source.",
            "B": "A warehouse is used for service refresh operations.",
            "C": "Snowflake recommends using a dedicated warehouse no larger than MEDIUM for a Cortex Search service.",
            "D": "Costs can include refresh warehouse usage, embedding token costs, and serving costs.",
            "E": "Cortex Search services refresh continuously without any warehouse usage.",
        },
        "correctAnswer": "A,B,C,D",
        "multipleSelect": True,
        "explanation": "Cortex Search requires change tracking on the underlying source object(s) and uses a warehouse for refresh. Snowflake recommends a dedicated warehouse no larger than MEDIUM. Cost components include refresh compute, embedding token usage, and serving costs.",
        "source": [
            "https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/cortex-search-overview",
        ],
    },
    {
        "id": 12,
        "topic": "Governance & Security",
        "question": "Which statement aligns with Snowflake's guidance about how customer data is handled when using Snowflake AI features?",
        "options": {
            "A": "Customer data is not used to train models that are shared with other customers.",
            "B": "Customer prompts and completions are automatically shared with other Snowflake accounts for benchmarking.",
            "C": "Using Snowflake AI features requires exporting data to an external model provider by default.",
            "D": "AI features only work when data is stored in a stage encrypted with customer-managed keys.",
            "E": "AI features require disabling access controls so models can read all account data.",
        },
        "correctAnswer": "A",
        "multipleSelect": False,
        "explanation": "Snowflake's AI feature guidance emphasizes customer trust and privacy, including that customer data is not used to train models shared across customers.",
        "source": [
            "https://docs.snowflake.com/en/guides-overview-ai-features",
        ],
    },
    {
        "id": 14,
        "topic": "AI Observability",
        "question": "You are enabling AI Observability tracing in a Python application that connects to Snowflake. Which prerequisite is explicitly required to ensure traces are sent to Snowflake?",
        "options": {
            "A": "Set the TRULENS_OTEL_TRACING environment variable to 1 before connecting to Snowflake.",
            "B": "Run the application only inside a Snowflake Notebook.",
            "C": "Disable network policies so traces can be exported.",
            "D": "Grant CREATE WAREHOUSE to the application role.",
            "E": "Set a parameter that forces all Cortex models to be enabled for the account.",
        },
        "correctAnswer": "A",
        "multipleSelect": False,
        "explanation": "AI Observability requires setting TRULENS_OTEL_TRACING=1 prior to connecting. The documentation also notes that AI Observability is not supported from within Snowflake Notebooks.",
        "source": [
            "https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-observability/ai-observability",
        ],
    },
    {
        "id": 18,
        "topic": "Document AI",
        "question": "You are building a Document AI model to extract fields from invoices. Which practices are recommended to improve results? (Select all that apply)",
        "options": {
            "A": "Always set a high temperature to maximize creativity in extracted values.",
            "B": "Use training documents that reflect the real-world variability you expect (including missing or empty values when relevant).",
            "C": "Involve subject matter experts and document owners iteratively to define fields and validate results.",
            "D": "Only train on perfectly formatted documents so the model never sees edge cases.",
            "E": "Increase the refresh warehouse size to XL to improve extraction accuracy.",
        },
        "correctAnswer": "B,C",
        "multipleSelect": True,
        "explanation": "Document AI guidance emphasizes using representative documents (including variations and missing values) and involving domain experts iteratively to define and validate extracted fields.",
        "source": [
            "https://docs.snowflake.com/en/user-guide/snowflake-cortex/document-ai/overview",
            "https://docs.snowflake.com/en/user-guide/snowflake-cortex/document-ai/preparing-documents",
        ],
    },
    {
        "id": 23,
        "topic": "AI Observability",
        "question": "Which prerequisites are needed to use AI Observability with a Python application? (Select all that apply)",
        "options": {
            "A": "Grant the SNOWFLAKE.CORTEX_USER database role to the role used by the application.",
            "B": "Install the TruLens packages required by the Snowflake AI Observability connector.",
            "C": "Set TRULENS_OTEL_TRACING=1 before connecting to Snowflake.",
            "D": "Run the application only from Snowflake Notebooks.",
            "E": "Grant the AI_OBSERVABILITY_EVENTS_LOOKUP application role to access trace events.",
        },
        "correctAnswer": "A,B,C,E",
        "multipleSelect": True,
        "explanation": "AI Observability documentation lists required roles/privileges (including CORTEX_USER and the AI Observability application roles), required Python packages (TruLens), and the TRULENS_OTEL_TRACING setting. Snowflake Notebooks are explicitly not supported.",
        "source": [
            "https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-observability/ai-observability",
        ],
    },
    {
        "id": 25,
        "topic": "Document AI",
        "question": "Which statements about Document AI limits and operational usage are correct? (Select all that apply)",
        "options": {
            "A": "Documents must be within supported file type and size limits (for example, PDFs up to 125 pages and 50 MB).",
            "B": "Document AI can process up to 1000 documents per query.",
            "C": "For internal stages, Document AI supports only server-side encryption.",
            "D": "You can build automated pipelines for Document AI using streams and tasks.",
            "E": "Document AI pipelines support serverless tasks.",
        },
        "correctAnswer": "A,B,C,D",
        "multipleSelect": True,
        "explanation": "Document AI has explicit document constraints (format, size, pages) and query limits. It supports only server-side encryption for internal stages and can be operationalized with streams and tasks, but does not support serverless tasks.",
        "source": [
            "https://docs.snowflake.com/en/user-guide/snowflake-cortex/document-ai/preparing-documents",
            "https://docs.snowflake.com/en/user-guide/snowflake-cortex/document-ai/limitations",
            "https://docs.snowflake.com/en/user-guide/snowflake-cortex/document-ai/overview",
        ],
    },
    {
        "id": 36,
        "topic": "Cost & Governance",
        "question": "You are planning to use SNOWFLAKE.CORTEX.TRANSLATE for text translation at scale. Which statements are correct? (Select all that apply)",
        "options": {
            "A": "TRANSLATE runs on Snowflake-managed compute, not your virtual warehouse.",
            "B": "TRANSLATE is billed by warehouse credits only.",
            "C": "TRANSLATE supports translating non-text inputs such as images.",
            "D": "Because TRANSLATE may add an internal prompt to your input text, its token-based billing can be higher than the raw input text token count.",
            "E": "Snowflake recommends you use a warehouse no larger than MEDIUM for workloads that call Cortex AI functions.",
        },
        "correctAnswer": "A,D,E",
        "multipleSelect": True,
        "explanation": "TRANSLATE uses Snowflake-managed compute. Cortex AI function usage is token-based, and some functions (including TRANSLATE) may add internal prompts affecting token counts. Snowflake recommends using warehouses no larger than MEDIUM for AI workloads.",
        "source": [
            "https://docs.snowflake.com/en/sql-reference/functions/translate-snowflake-cortex",
            "https://docs.snowflake.com/en/user-guide/snowflake-cortex/aisql",
        ],
    },
    {
        "id": 38,
        "topic": "Cost & Governance",
        "question": "When estimating token usage for Cortex AI functions, which statement about SNOWFLAKE.CORTEX.COUNT_TOKENS is true?",
        "options": {
            "A": "COUNT_TOKENS includes the managed system prompt added by AI functions, so it always matches the billable token count.",
            "B": "COUNT_TOKENS supports fine-tuned models.",
            "C": "COUNT_TOKENS may underestimate billable tokens because it does not include the managed system prompt that Snowflake adds to AI function calls.",
            "D": "COUNT_TOKENS itself incurs token-based charges just like COMPLETE.",
            "E": "COUNT_TOKENS is only available in regions where a specific model is deployed.",
        },
        "correctAnswer": "C",
        "multipleSelect": False,
        "explanation": "The documentation notes that COUNT_TOKENS does not include the managed system prompt that Snowflake adds when running AI functions, so it can be lower than the billable token count.",
        "source": [
            "https://docs.snowflake.com/en/sql-reference/functions/count_tokens-snowflake-cortex",
        ],
    },
    {
        "id": 43,
        "topic": "Cortex Search",
        "question": "Which requirements apply when creating and operating a Cortex Search service? (Select all that apply)",
        "options": {
            "A": "Change tracking must be enabled on the underlying source object(s).",
            "B": "A warehouse is used for service refresh operations.",
            "C": "The role creating the service must have a Snowflake Cortex database role such as SNOWFLAKE.CORTEX_USER or SNOWFLAKE.CORTEX_EMBED_USER.",
            "D": "Snowflake recommends using a dedicated warehouse no larger than MEDIUM for the service.",
            "E": "Cortex Search services refresh continuously using serverless compute only, so no warehouse is needed.",
        },
        "correctAnswer": "A,B,C,D",
        "multipleSelect": True,
        "explanation": "Cortex Search requires change tracking on the source, uses a warehouse for refresh, and requires appropriate Cortex roles. Snowflake recommends a dedicated warehouse no larger than MEDIUM.",
        "source": [
            "https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/cortex-search-overview",
        ],
    },
    {
        "id": 45,
        "topic": "Document AI",
        "question": "You want to process a set of PDFs with Document AI and productionize the workflow. Which considerations are critical? (Select all that apply)",
        "options": {
            "A": "Documents must be within supported format and size limits (for example, PDFs up to 125 pages and 50 MB).",
            "B": "You must convert PDFs to plain text before Document AI can process them.",
            "C": "Document AI supports processing up to 1000 documents per query.",
            "D": "You can operationalize extraction using streams and tasks.",
            "E": "Document AI supports serverless tasks for pipelines.",
        },
        "correctAnswer": "A,C,D",
        "multipleSelect": True,
        "explanation": "Document AI has explicit limits on supported formats and document size/page count. It can process up to 1000 documents per query, and it can be productionized using streams and tasks. Document AI does not support serverless tasks.",
        "source": [
            "https://docs.snowflake.com/en/user-guide/snowflake-cortex/document-ai/preparing-documents",
            "https://docs.snowflake.com/en/user-guide/snowflake-cortex/document-ai/limitations",
            "https://docs.snowflake.com/en/user-guide/snowflake-cortex/document-ai/overview",
        ],
    },
    {
        "id": 47,
        "topic": "Cortex LLM Functions",
        "question": "You need deterministic, schema-validated JSON output from a Cortex LLM call and you want robust error handling. Which statements are correct? (Select all that apply)",
        "options": {
            "A": "With COMPLETE, you can provide response_format with a JSON schema and set temperature to 0 for more consistent outputs.",
            "B": "You can declare required keys in the schema so the model is expected to include them in the response.",
            "C": "TRY_COMPLETE returns NULL instead of raising an error when it cannot perform the operation.",
            "D": "The response_format option is provided as a string containing JSON schema.",
            "E": "Using a larger virtual warehouse increases COMPLETE speed and lowers token cost.",
        },
        "correctAnswer": "A,B,C,D",
        "multipleSelect": True,
        "explanation": "COMPLETE supports response_format using a JSON schema passed as a string, and using temperature 0 reduces randomness. TRY_COMPLETE is like COMPLETE but returns NULL instead of raising an error.",
        "source": [
            "https://docs.snowflake.com/en/sql-reference/functions/complete-snowflake-cortex",
            "https://docs.snowflake.com/en/sql-reference/functions/try_complete-snowflake-cortex",
        ],
    },
    {
        "id": 58,
        "topic": "Governance & Security",
        "question": "A Streamlit in Snowflake app queries a table in a database/schema and calls Cortex LLM functions. Which privileges are required for the role used by the app? (Select all that apply)",
        "options": {
            "A": "Grant the SNOWFLAKE.CORTEX_USER database role.",
            "B": "Grant USAGE on the database and schema that contain the table.",
            "C": "Grant SELECT on the underlying table or view.",
            "D": "Use ACCOUNTADMIN; Cortex functions require it.",
            "E": "Grant CREATE COMPUTE POOL; Streamlit apps require it.",
        },
        "correctAnswer": "A,B,C",
        "multipleSelect": True,
        "explanation": "Cortex LLM functions require the SNOWFLAKE.CORTEX_USER database role. In addition, standard Snowflake access control requires USAGE on the database and schema and SELECT on the referenced objects.",
        "source": [
            "https://docs.snowflake.com/en/user-guide/snowflake-cortex/aisql",
        ],
    },
]


def _load_bank(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_bank(path: Path, data: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def apply_regenerated_questions(path: Path, regenerated: List[Dict[str, Any]]) -> int:
    data = _load_bank(path)
    questions = data.get("questions")
    if not isinstance(questions, list):
        raise ValueError("Expected JSON top-level key 'questions' to be a list")

    by_id: Dict[int, Dict[str, Any]] = {}
    for q in questions:
        if isinstance(q, dict) and isinstance(q.get("id"), int):
            by_id[q["id"]] = q

    replaced = 0
    now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    for new_q in regenerated:
        qid = new_q["id"]
        if qid not in by_id:
            raise KeyError(f"Question id={qid} not found in bank")
        idx = next(i for i, q in enumerate(questions) if isinstance(q, dict) and q.get("id") == qid)

        normalized = dict(new_q)
        normalized.setdefault("difficulty", by_id[qid].get("difficulty", "medium"))
        normalized["lastUpdatedAt"] = now
        normalized["regenerated"] = True
        normalized["regenerationBatch"] = "batch2"

        questions[idx] = normalized
        replaced += 1

    meta = data.setdefault("metadata", {})
    notes = meta.get("notes", "")
    stamp = f"[{now}] Regenerated {replaced} corrupted questions (batch2) to fix missing/truncated options and answer mismatches."
    if stamp not in notes:
        meta["notes"] = (notes + "\n" + stamp).strip() if notes else stamp
    meta["lastUpdatedAt"] = now

    _write_bank(path, data)
    return replaced


if __name__ == "__main__":
    if not QUESTION_BANK_PATH.exists():
        raise SystemExit(f"Question bank not found at: {QUESTION_BANK_PATH}")

    replaced_count = apply_regenerated_questions(QUESTION_BANK_PATH, REGENERATED_QUESTIONS)
    print(f"Updated question bank: {QUESTION_BANK_PATH}")
    print(f"Replaced questions: {replaced_count}")
