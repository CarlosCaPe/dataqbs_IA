#!/usr/bin/env python3
"""
Chatbot RAG Stress Test — 100 HR/Recruiter Questions
=====================================================
Sends 100 sequential questions to the /api/chat endpoint simulating a recruiter
evaluating Carlos Carrillo's portfolio. Each question is sent with the prior
conversation history (up to 8 turns, matching the API's MAX_HISTORY).

The test measures:
  - Response latency (time to complete streaming)
  - Whether the chatbot answered or deflected ("don't have that information")
  - Whether the answer seems relevant (keyword overlap with the question)
  - Token-level throughput

Results are saved to tests/chatbot_stress_results.json with a summary report
printed to stdout.

Usage:
  # Start dev server first:  npx astro dev
  python3 tests/chatbot_stress_test.py [--base-url http://localhost:4321] [--max-questions 100]
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# ── 100 HR / Recruiter questions organized by category ──────────────
QUESTIONS: list[dict] = [
    # ─── 1. PROFESSIONAL SUMMARY & BACKGROUND (1-15) ───
    {"id": 1,  "cat": "summary",       "q": "Can you give me a brief professional summary of Carlos?"},
    {"id": 2,  "cat": "summary",       "q": "How many years of experience does Carlos have?"},
    {"id": 3,  "cat": "summary",       "q": "What is Carlos's current job title?"},
    {"id": 4,  "cat": "summary",       "q": "Where is Carlos located?"},
    {"id": 5,  "cat": "summary",       "q": "Is Carlos open to remote work?"},
    {"id": 6,  "cat": "summary",       "q": "What languages does Carlos speak?"},
    {"id": 7,  "cat": "summary",       "q": "What is Carlos's educational background?"},
    {"id": 8,  "cat": "summary",       "q": "Where did Carlos study?"},
    {"id": 9,  "cat": "summary",       "q": "What degree does Carlos hold?"},
    {"id": 10, "cat": "summary",       "q": "What is Carlos's personal vision or philosophy?"},
    {"id": 11, "cat": "summary",       "q": "What drives Carlos professionally?"},
    {"id": 12, "cat": "summary",       "q": "What kind of roles is Carlos open to?"},
    {"id": 13, "cat": "summary",       "q": "How would you describe Carlos's work style?"},
    {"id": 14, "cat": "summary",       "q": "What sets Carlos apart from other data engineers?"},
    {"id": 15, "cat": "summary",       "q": "Can Carlos work in English and Spanish?"},

    # ─── 2. TECHNICAL SKILLS (16-35) ───
    {"id": 16, "cat": "skills",        "q": "What programming languages does Carlos know?"},
    {"id": 17, "cat": "skills",        "q": "What is Carlos's proficiency level in Python?"},
    {"id": 18, "cat": "skills",        "q": "Does Carlos know SQL? At what level?"},
    {"id": 19, "cat": "skills",        "q": "Does Carlos have experience with JavaScript or TypeScript?"},
    {"id": 20, "cat": "skills",        "q": "What cloud platforms has Carlos worked with?"},
    {"id": 21, "cat": "skills",        "q": "Does Carlos have Snowflake experience?"},
    {"id": 22, "cat": "skills",        "q": "What Azure services is Carlos proficient in?"},
    {"id": 23, "cat": "skills",        "q": "Does Carlos know Microsoft Fabric?"},
    {"id": 24, "cat": "skills",        "q": "What AI and machine learning skills does Carlos have?"},
    {"id": 25, "cat": "skills",        "q": "Does Carlos have experience with RAG systems?"},
    {"id": 26, "cat": "skills",        "q": "What does Carlos know about vector embeddings?"},
    {"id": 27, "cat": "skills",        "q": "Has Carlos worked with LLM evaluation or prompt engineering?"},
    {"id": 28, "cat": "skills",        "q": "What databases has Carlos used?"},
    {"id": 29, "cat": "skills",        "q": "Does Carlos have SQL Server experience?"},
    {"id": 30, "cat": "skills",        "q": "What ETL tools has Carlos used?"},
    {"id": 31, "cat": "skills",        "q": "Does Carlos know Docker?"},
    {"id": 32, "cat": "skills",        "q": "What CI/CD experience does Carlos have?"},
    {"id": 33, "cat": "skills",        "q": "Does Carlos use any code quality tools?"},
    {"id": 34, "cat": "skills",        "q": "What Python libraries is Carlos proficient in?"},
    {"id": 35, "cat": "skills",        "q": "Does Carlos have experience with web frameworks like Astro or Svelte?"},

    # ─── 3. WORK EXPERIENCE (36-55) ───
    {"id": 36, "cat": "experience",    "q": "What is Carlos's most recent work experience?"},
    {"id": 37, "cat": "experience",    "q": "Has Carlos worked as a Senior Data Engineer?"},
    {"id": 38, "cat": "experience",    "q": "What kind of companies has Carlos worked for?"},
    {"id": 39, "cat": "experience",    "q": "Has Carlos done contract or freelance work?"},
    {"id": 40, "cat": "experience",    "q": "What is the largest dataset Carlos has worked with?"},
    {"id": 41, "cat": "experience",    "q": "Has Carlos built data pipelines? Describe one."},
    {"id": 42, "cat": "experience",    "q": "What was Carlos's role at his most recent position?"},
    {"id": 43, "cat": "experience",    "q": "Has Carlos worked with high-volume data environments?"},
    {"id": 44, "cat": "experience",    "q": "Did Carlos achieve cost savings in any role?"},
    {"id": 45, "cat": "experience",    "q": "Has Carlos implemented data quality monitoring?"},
    {"id": 46, "cat": "experience",    "q": "What industries has Carlos worked in?"},
    {"id": 47, "cat": "experience",    "q": "Has Carlos led any teams or projects?"},
    {"id": 48, "cat": "experience",    "q": "What was Carlos's biggest professional achievement?"},
    {"id": 49, "cat": "experience",    "q": "How long has Carlos been self-employed?"},
    {"id": 50, "cat": "experience",    "q": "What does dataqbs do as a company?"},

    # ─── 4. PROJECTS (51-70) ───
    {"id": 51, "cat": "projects",      "q": "What projects has Carlos built?"},
    {"id": 52, "cat": "projects",      "q": "Tell me about the Crypto Arbitrage Scanner project."},
    {"id": 53, "cat": "projects",      "q": "What is the OAI Code Evaluator?"},
    {"id": 54, "cat": "projects",      "q": "What does the Email Collector project do?"},
    {"id": 55, "cat": "projects",      "q": "Has Carlos built any real estate tools?"},
    {"id": 56, "cat": "projects",      "q": "What is the Supplier Verifier project?"},
    {"id": 57, "cat": "projects",      "q": "Tell me about the Media Comparison tools."},
    {"id": 58, "cat": "projects",      "q": "Has Carlos built a portfolio website? What tech stack?"},
    {"id": 59, "cat": "projects",      "q": "What is the Linux Migration Toolkit?"},
    {"id": 60, "cat": "projects",      "q": "Does Carlos have any open-source projects on GitHub?"},
    {"id": 61, "cat": "projects",      "q": "How many exchanges does the arbitrage scanner support?"},
    {"id": 62, "cat": "projects",      "q": "What algorithms are used in the arbitrage scanner?"},
    {"id": 63, "cat": "projects",      "q": "Does the OAI Evaluator use YAML configuration?"},
    {"id": 64, "cat": "projects",      "q": "Does Carlos's email collector support OAuth?"},
    {"id": 65, "cat": "projects",      "q": "What web scraping tools has Carlos used in his projects?"},
    {"id": 66, "cat": "projects",      "q": "Has Carlos built any chatbots or AI assistants?"},
    {"id": 67, "cat": "projects",      "q": "Does Carlos use a monorepo structure? Why?"},
    {"id": 68, "cat": "projects",      "q": "What testing frameworks does Carlos use in his projects?"},
    {"id": 69, "cat": "projects",      "q": "Has Carlos built any automation tools?"},
    {"id": 70, "cat": "projects",      "q": "Can Carlos show live demos of his projects?"},

    # ─── 5. CERTIFICATIONS (71-80) ───
    {"id": 71, "cat": "certifications","q": "What certifications does Carlos hold?"},
    {"id": 72, "cat": "certifications","q": "Is Carlos Snowflake certified?"},
    {"id": 73, "cat": "certifications","q": "Does Carlos have any Azure certifications?"},
    {"id": 74, "cat": "certifications","q": "What is the SnowPro GenAI certification?"},
    {"id": 75, "cat": "certifications","q": "When did Carlos get his Azure Data Engineer certification?"},
    {"id": 76, "cat": "certifications","q": "What is the MCSA SQL 2016 certification?"},
    {"id": 77, "cat": "certifications","q": "Does Carlos have any AI-related certifications?"},
    {"id": 78, "cat": "certifications","q": "What topics does the SnowPro GenAI exam cover?"},
    {"id": 79, "cat": "certifications","q": "Has Carlos studied Cortex AI in Snowflake?"},
    {"id": 80, "cat": "certifications","q": "Does Carlos plan to get more certifications?"},

    # ─── 6. SOFT SKILLS & CULTURE FIT (81-90) ───
    {"id": 81, "cat": "soft_skills",   "q": "How does Carlos approach problem-solving?"},
    {"id": 82, "cat": "soft_skills",   "q": "Is Carlos a team player or more independent?"},
    {"id": 83, "cat": "soft_skills",   "q": "How does Carlos handle tight deadlines?"},
    {"id": 84, "cat": "soft_skills",   "q": "What is Carlos's communication style?"},
    {"id": 85, "cat": "soft_skills",   "q": "Does Carlos mentor or share knowledge?"},
    {"id": 86, "cat": "soft_skills",   "q": "How does Carlos stay current with new technologies?"},
    {"id": 87, "cat": "soft_skills",   "q": "What role does AI play in Carlos's daily work?"},
    {"id": 88, "cat": "soft_skills",   "q": "Does Carlos value work-life balance?"},
    {"id": 89, "cat": "soft_skills",   "q": "How does Carlos approach documentation?"},
    {"id": 90, "cat": "soft_skills",   "q": "What motivates Carlos in his career?"},

    # ─── 7. SCENARIO & BEHAVIORAL (91-100) ───
    {"id": 91, "cat": "scenario",      "q": "If I needed someone to design a Snowflake data warehouse from scratch, could Carlos do it?"},
    {"id": 92, "cat": "scenario",      "q": "Can Carlos build a real-time data pipeline on Azure?"},
    {"id": 93, "cat": "scenario",      "q": "If we have a legacy SQL Server database that needs modernization, is Carlos the right fit?"},
    {"id": 94, "cat": "scenario",      "q": "Could Carlos implement a RAG-based chatbot for our company?"},
    {"id": 95, "cat": "scenario",      "q": "We need someone to evaluate LLM outputs systematically. Can Carlos help?"},
    {"id": 96, "cat": "scenario",      "q": "Can Carlos automate our CI/CD pipeline with GitHub Actions?"},
    {"id": 97, "cat": "scenario",      "q": "We need to process 100M+ rows daily. Does Carlos have experience at that scale?"},
    {"id": 98, "cat": "scenario",      "q": "Could Carlos help us migrate from Windows to Linux dev environments?"},
    {"id": 99, "cat": "scenario",      "q": "Can Carlos build API integrations with third-party platforms?"},
    {"id": 100,"cat": "scenario",      "q": "How would Carlos approach optimizing our data warehouse costs?"},
]


# ── Deflection patterns (chatbot says "I don't know") ───────────────
DEFLECT_PATTERNS = [
    r"don't have that information",
    r"not.{0,20}in.{0,10}(context|profile|public)",
    r"cannot.{0,15}(find|answer|provide)",
    r"no.{0,10}information.{0,10}available",
    r"i('m| am) not (sure|able)",
    r"outside.{0,15}scope",
    r"not.{0,15}mentioned",
]


def parse_sse_stream(raw: bytes) -> str:
    """Parse an SSE byte stream into the full text response."""
    text = raw.decode("utf-8", errors="replace")
    full = []
    for line in text.split("\n"):
        if line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]":
                break
            try:
                obj = json.loads(data)
                delta = ""
                for choice in obj.get("choices", []):
                    delta += choice.get("delta", {}).get("content", "")
                if delta:
                    full.append(delta)
            except json.JSONDecodeError:
                full.append(data)
    return "".join(full)


def send_question(
    base_url: str,
    question: str,
    history: list[dict],
    locale: str = "en",
    max_retries: int = 5,
) -> tuple[str, float, int]:
    """
    Send a question to /api/chat and return (answer_text, latency_secs, status_code).
    Retries on 429/502 (Groq rate limit) with exponential backoff.
    """
    payload = json.dumps({
        "message": question,
        "history": history[-8:],  # match MAX_HISTORY
        "locale": locale,
    }).encode()

    for attempt in range(max_retries + 1):
        req = Request(
            f"{base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        t0 = time.monotonic()
        try:
            with urlopen(req, timeout=60) as resp:
                status = resp.status
                raw = resp.read()
                latency = time.monotonic() - t0
                answer = parse_sse_stream(raw)
                return answer, latency, status
        except HTTPError as e:
            latency = time.monotonic() - t0
            body = e.read().decode(errors="replace")
            # Retry on rate limit (429) or Groq upstream limit (502)
            if e.code in (429, 502) and attempt < max_retries:
                wait = 30 * (attempt + 1)  # 30s, 60s, 90s, 120s, 150s
                print(f"\n        ⏳ Rate limited ({e.code}), waiting {wait}s (retry {attempt+1}/{max_retries})...", end=" ", flush=True)
                time.sleep(wait)
                continue
            return f"HTTP {e.code}: {body}", latency, e.code
        except URLError as e:
            latency = time.monotonic() - t0
            return f"Connection error: {e.reason}", latency, 0
        except Exception as e:
            latency = time.monotonic() - t0
            return f"Error: {e}", latency, 0
    return "Max retries exceeded", 0.0, 0


def is_deflection(answer: str) -> bool:
    """Check if the chatbot deflected (said it doesn't have the info)."""
    lower = answer.lower()
    return any(re.search(p, lower) for p in DEFLECT_PATTERNS)


def keyword_overlap(question: str, answer: str) -> float:
    """Simple relevance score: what fraction of question keywords appear in the answer."""
    stop_words = {
        "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "need", "dare", "ought",
        "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
        "into", "about", "like", "through", "after", "over", "between",
        "out", "against", "during", "without", "before", "under", "around",
        "and", "but", "or", "nor", "not", "so", "yet", "both", "either",
        "neither", "each", "every", "all", "any", "few", "more", "most",
        "other", "some", "such", "no", "only", "own", "same", "than",
        "too", "very", "just", "because", "if", "when", "where", "how",
        "what", "which", "who", "whom", "this", "that", "these", "those",
        "i", "me", "my", "myself", "we", "our", "you", "your", "he", "him",
        "his", "she", "her", "it", "its", "they", "them", "their", "us",
        "tell", "give", "describe", "does", "carlos", "carlos's",
    }
    q_words = set(re.findall(r"\b\w+\b", question.lower())) - stop_words
    a_words = set(re.findall(r"\b\w+\b", answer.lower()))
    if not q_words:
        return 1.0
    return len(q_words & a_words) / len(q_words)


def run_stress_test(base_url: str, max_q: int, locale: str):
    """Execute the full stress test."""
    questions = QUESTIONS[:max_q]
    results = []
    history: list[dict] = []
    
    total = len(questions)
    answered = 0
    deflected = 0
    errors = 0
    total_latency = 0.0
    
    print(f"\n{'='*80}")
    print(f"  CHATBOT STRESS TEST — {total} Questions")
    print(f"  Endpoint: {base_url}/api/chat")
    print(f"  Locale: {locale}")
    print(f"{'='*80}\n")

    for i, q in enumerate(questions):
        qid = q["id"]
        cat = q["cat"]
        question = q["q"]
        
        print(f"  [{qid:3d}/{total}] [{cat:15s}] {question[:60]}...", end=" ", flush=True)
        
        answer, latency, status = send_question(base_url, question, history, locale)
        total_latency += latency
        
        deflect = is_deflection(answer) if status == 200 else False
        relevance = keyword_overlap(question, answer) if status == 200 and not deflect else 0.0
        
        if status != 200:
            errors += 1
            verdict = "ERROR"
        elif deflect:
            deflected += 1
            verdict = "DEFLECT"
        else:
            answered += 1
            verdict = "OK"
        
        result = {
            "id": qid,
            "category": cat,
            "question": question,
            "answer": answer,
            "latency_s": round(latency, 2),
            "status": status,
            "verdict": verdict,
            "relevance": round(relevance, 2),
        }
        results.append(result)
        
        # Print inline result
        latency_str = f"{latency:.1f}s"
        if verdict == "OK":
            print(f"✅ {latency_str}  rel={relevance:.0%}  [{len(answer)} chars]")
        elif verdict == "DEFLECT":
            print(f"⚠️  {latency_str}  DEFLECTED")
        else:
            print(f"❌ {latency_str}  {answer[:60]}")
        
        # Add to conversation history for sequential context
        if status == 200:
            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": answer})
        
        # Delay between questions — Groq free tier TPM limits
        # Using 8b model for testing: 6K TPM / 500K TPD
        time.sleep(5.0)

    # ── Summary ─────────────────────────────────────
    avg_latency = total_latency / total if total > 0 else 0
    answer_rate = answered / total * 100 if total > 0 else 0
    deflect_rate = deflected / total * 100 if total > 0 else 0
    error_rate = errors / total * 100 if total > 0 else 0

    # Category breakdown
    cats: dict[str, dict] = {}
    for r in results:
        c = r["category"]
        if c not in cats:
            cats[c] = {"total": 0, "ok": 0, "deflect": 0, "error": 0, "latency": 0.0, "relevance": 0.0}
        cats[c]["total"] += 1
        cats[c]["latency"] += r["latency_s"]
        if r["verdict"] == "OK":
            cats[c]["ok"] += 1
            cats[c]["relevance"] += r["relevance"]
        elif r["verdict"] == "DEFLECT":
            cats[c]["deflect"] += 1
        else:
            cats[c]["error"] += 1

    print(f"\n{'='*80}")
    print(f"  RESULTS SUMMARY")
    print(f"{'='*80}")
    print(f"  Total questions:   {total}")
    print(f"  ✅ Answered:       {answered} ({answer_rate:.0f}%)")
    print(f"  ⚠️  Deflected:     {deflected} ({deflect_rate:.0f}%)")
    print(f"  ❌ Errors:         {errors} ({error_rate:.0f}%)")
    print(f"  Avg latency:       {avg_latency:.2f}s")
    print(f"  Total time:        {total_latency:.1f}s")
    print()
    print(f"  {'Category':<18} {'OK':>4} {'Defl':>5} {'Err':>4} {'Avg Lat':>8} {'Avg Rel':>8}")
    print(f"  {'─'*18} {'─'*4} {'─'*5} {'─'*4} {'─'*8} {'─'*8}")
    for c, v in sorted(cats.items()):
        avg_l = v["latency"] / v["total"]
        avg_r = v["relevance"] / v["ok"] if v["ok"] > 0 else 0
        print(f"  {c:<18} {v['ok']:>4} {v['deflect']:>5} {v['error']:>4} {avg_l:>7.2f}s {avg_r:>7.0%}")

    # ── Deflection details ──────────────────────────
    deflections = [r for r in results if r["verdict"] == "DEFLECT"]
    if deflections:
        print(f"\n  DEFLECTED QUESTIONS (knowledge gaps):")
        print(f"  {'─'*60}")
        for r in deflections:
            print(f"  [{r['id']:3d}] {r['question']}")
            print(f"        → {r['answer'][:120]}...")
            print()

    # ── Low relevance answers ───────────────────────
    low_rel = [r for r in results if r["verdict"] == "OK" and r["relevance"] < 0.3]
    if low_rel:
        print(f"\n  LOW RELEVANCE ANSWERS (may need knowledge enrichment):")
        print(f"  {'─'*60}")
        for r in low_rel:
            print(f"  [{r['id']:3d}] rel={r['relevance']:.0%} {r['question']}")
            print(f"        → {r['answer'][:120]}...")
            print()

    # ── Save results ────────────────────────────────
    output = {
        "test_timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "base_url": base_url,
        "total_questions": total,
        "answered": answered,
        "deflected": deflected,
        "errors": errors,
        "answer_rate_pct": round(answer_rate, 1),
        "deflect_rate_pct": round(deflect_rate, 1),
        "avg_latency_s": round(avg_latency, 2),
        "total_time_s": round(total_latency, 1),
        "categories": {
            c: {
                "ok": v["ok"],
                "deflect": v["deflect"],
                "error": v["error"],
                "avg_relevance": round(v["relevance"] / v["ok"], 2) if v["ok"] > 0 else 0,
            }
            for c, v in sorted(cats.items())
        },
        "results": results,
    }

    out_path = Path(__file__).parent / "chatbot_stress_results.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"\n  📄 Full results saved to: {out_path}")
    print(f"{'='*80}\n")

    # ── Recommendations ─────────────────────────────
    print("  RECOMMENDATIONS:")
    if deflect_rate > 20:
        print("  ⚠️  High deflection rate. Add more knowledge chunks for:")
        for r in deflections:
            print(f"      - {r['category']}: {r['question']}")
    if avg_latency > 5:
        print("  ⚠️  High average latency. Consider reducing MAX_CONTEXT_CHUNKS or MAX_CHAT_TOKENS.")
    if error_rate > 5:
        print("  ❌ Significant error rate. Check API rate limits and Groq API status.")
    if deflect_rate <= 20 and avg_latency <= 5 and error_rate <= 5:
        print("  ✅ Chatbot performing well! Knowledge coverage is good.")
    print()

    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chatbot RAG Stress Test")
    parser.add_argument("--base-url", default="http://localhost:4321", help="Dev server URL")
    parser.add_argument("--max-questions", type=int, default=100, help="Max questions to ask")
    parser.add_argument("--locale", default="en", choices=["en", "es", "de"], help="Language")
    args = parser.parse_args()

    run_stress_test(args.base_url, args.max_questions, args.locale)
