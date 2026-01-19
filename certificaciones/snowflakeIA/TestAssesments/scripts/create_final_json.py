"""
Create the final comprehensive exam questions JSON file.
Merges extracted questions with proper structure.
"""
import json
from typing import Dict, List

def load_json(filepath: str):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data, filepath: str):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def create_comprehensive_output(questions: List[Dict]) -> Dict:
    """Create the comprehensive final output."""
    
    # Build the final structure
    output = {
        "examInfo": {
            "code": "GES-C01",
            "name": "SnowPro Specialty: Generative AI Certification Exam",
            "provider": "Snowflake",
            "passingScore": "750/1000 (approximately 75%)",
            "duration": "115 minutes",
            "questionCount": "65 questions on actual exam",
            "fee": "$375 USD",
            "format": [
                "Multiple Choice (single answer)",
                "Multiple Select (choose all that apply)"
            ],
            "prerequisites": "SnowPro Core Certification (preferred)",
            "domains": [
                {"name": "Snowflake Cortex AI Foundations", "weight": "10-15%"},
                {"name": "Cortex LLM Functions (AI_COMPLETE, etc.)", "weight": "15-20%"},
                {"name": "Cortex Search", "weight": "15-20%"},
                {"name": "Cortex Analyst", "weight": "10-15%"},
                {"name": "Document AI", "weight": "15-20%"},
                {"name": "Vector Embeddings & RAG", "weight": "10-15%"},
                {"name": "Fine-tuning & Custom Models", "weight": "10-15%"},
                {"name": "AI Observability & Governance", "weight": "5-10%"}
            ]
        },
        "metadata": {
            "totalQuestions": len(questions),
            "source": "OCR extracted from GES-C01 practice exam screenshots",
            "extractionDate": "2025-01-27",
            "note": "These questions are for study purposes. Some OCR artifacts may remain. Always verify against official Snowflake documentation."
        },
        "questions": [],
        "studyGuide": {
            "Cortex Analyst": [
                "Semantic models bridge natural language and database schema",
                "LLM summarization agent manages multi-turn conversations",
                "Llama 3.1 70B used for summarization (96.5% accuracy)",
                "verified_queries for pre-defined specific questions",
                "Warehouse size MEDIUM or smaller recommended for all Cortex functions"
            ],
            "Cortex Search": [
                "Hybrid search engine (vector + keyword)",
                "Chunk text to max 512 tokens for best results",
                "CHANGE_TRACKING required for incremental refreshes",
                "Cost: 6.3 credits per GB/month of indexed data",
                "Requires virtual warehouse for refreshes (MEDIUM or smaller)"
            ],
            "Document AI": [
                "SNOWFLAKE_SSE encryption required for internal stages",
                "Maximum 125 pages and 50 MB per document",
                "Maximum 1000 documents per query",
                "Supported formats: PDF, PNG, DOCX, XML, JPEG, HTML, TXT, TIFF",
                "SNOWFLAKE.DOCUMENT_INTELLIGENCE_CREATOR role required",
                "Training with diverse documents improves accuracy"
            ],
            "Vector Embeddings": [
                "VECTOR data type supports up to 4096 dimensions",
                "Element types: FLOAT (32-bit) or INT (32-bit)",
                "Not supported: VARIANT columns, clustering keys, primary keys",
                "EMBED_TEXT_768: e5-base-v2, etc.",
                "EMBED_TEXT_1024: snowflake-arctic-embed, voyage-multilingual-2, etc."
            ],
            "Cortex LLM Functions": [
                "AI_COMPLETE: General LLM completions with structured outputs",
                "response_format parameter for JSON schema enforcement",
                "temperature=0 for most consistent results",
                "TRY_COMPLETE returns NULL on failure instead of error",
                "Token billing: input + output tokens (varies by function)"
            ],
            "Fine-tuning": [
                "Supported models: llama3-8b, llama3.1-8b, llama3.1-70b, mistral-7b",
                "Training data: prompt/completion pairs",
                "Context window varies by model (e.g., 8k for llama3-8b)",
                "Fine-tuned models exclusive to your account",
                "Deploy to SPCS with GPU compute pools"
            ],
            "Governance & Security": [
                "CORTEX_MODELS_ALLOWLIST controls model access",
                "Customer data never used to train shared models",
                "Cortex Guard filters unsafe/harmful responses",
                "RBAC controls access to stages and semantic models",
                "Metadata should not contain sensitive data"
            ]
        }
    }
    
    # Add formatted questions
    for q in questions:
        formatted_q = {
            "id": q['id'],
            "topic": q.get('topic', 'General Cortex AI'),
            "question": q['question'],
            "correctAnswer": q['correct_answer'],
            "explanation": q.get('explanation', ''),
            "multipleSelect": ',' in q['correct_answer']
        }
        output["questions"].append(formatted_q)
    
    return output

def main():
    print("="*60)
    print("Creating Final Comprehensive Exam Questions JSON")
    print("="*60)
    
    # Load cleaned questions
    print("\n1. Loading cleaned questions...")
    data = load_json('GES-C01_Exam_Questions_Clean.json')
    questions = data.get('questions', [])
    print(f"   Loaded {len(questions)} questions")
    
    # Create comprehensive output
    print("\n2. Building comprehensive output...")
    output = create_comprehensive_output(questions)
    
    # Save to multiple locations
    print("\n3. Saving output files...")
    
    # Save in TestAssesments folder
    save_json(output, 'GES-C01_Final_Questions.json')
    print("   - Saved: TestAssesments/GES-C01_Final_Questions.json")
    
    # Save in parent folder (update existing file)
    save_json(output, '../GES-C01_Exam_Sample_Questions.json')
    print("   - Updated: GES-C01_Exam_Sample_Questions.json")
    
    # Print summary
    print("\n" + "="*60)
    print("FINAL OUTPUT SUMMARY")
    print("="*60)
    print(f"Total questions: {output['metadata']['totalQuestions']}")
    
    # Count by topic
    topics = {}
    multi_select = 0
    for q in output['questions']:
        t = q['topic']
        topics[t] = topics.get(t, 0) + 1
        if q['multipleSelect']:
            multi_select += 1
    
    print(f"\nSingle answer questions: {len(questions) - multi_select}")
    print(f"Multiple select questions: {multi_select}")
    
    print("\nQuestions by Topic:")
    for t, c in sorted(topics.items(), key=lambda x: -x[1]):
        print(f"  - {t}: {c}")
    
    # Sample
    print("\n" + "="*60)
    print("SAMPLE QUESTIONS (First 3)")
    print("="*60)
    for q in output['questions'][:3]:
        print(f"\n[Q{q['id']}] {q['topic']}")
        print(f"Type: {'Multiple Select' if q['multipleSelect'] else 'Single Answer'}")
        print(f"Q: {q['question'][:200]}...")
        print(f"A: {q['correctAnswer']}")

if __name__ == '__main__':
    main()
