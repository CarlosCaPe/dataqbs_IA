#!/usr/bin/env python3
"""
Extract questions from PDF files and merge with existing JSON.
"""
from pypdf import PdfReader
import json
import re
import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
PDF_DIR = BASE_DIR / "data" / "pdfs"
JSON_DIR = BASE_DIR / "data" / "json"
OUTPUT_JSON = BASE_DIR.parent / "GES-C01_Exam_Sample_Questions.json"

def extract_text_from_pdf(pdf_path):
    """Extract all text from a PDF file."""
    reader = PdfReader(pdf_path)
    full_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n"
    return full_text

def parse_questions_from_text(text, source_file):
    """Parse questions and answers from extracted text."""
    questions = []
    
    # Pattern to find question numbers
    # Look for patterns like "Question 1", "1.", "Q1:", etc.
    question_pattern = r'(?:Question\s*)?(\d+)[\.\):\s]+(.+?)(?=(?:Question\s*)?\d+[\.\):\s]|Answer|$)'
    answer_pattern = r'Answer[:\s]*([A-E](?:\s*,\s*[A-E])*)'
    explanation_pattern = r'Explanation[:\s]*(.+?)(?=Question|\d+[\.\):]|$)'
    
    # Split by "Question" keyword or numbered patterns
    parts = re.split(r'(?=Question\s+\d+|^\d+[\.\)])', text, flags=re.MULTILINE)
    
    current_question = None
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
            
        # Try to extract question number
        q_match = re.match(r'(?:Question\s*)?(\d+)[\.\):\s]*(.*)', part, re.DOTALL)
        if q_match:
            q_num = int(q_match.group(1))
            q_content = q_match.group(2).strip()
            
            # Find answer in this section
            answer_match = re.search(r'(?:Answer|Correct\s+Answer)[:\s]*([A-E](?:\s*[,&]\s*[A-E])*)', part, re.IGNORECASE)
            answer = ""
            if answer_match:
                answer = answer_match.group(1).replace(" ", "").replace("&", ",").upper()
            
            # Find explanation
            expl_match = re.search(r'(?:Explanation|Rationale)[:\s]*(.+?)(?=Question\s*\d+|$)', part, re.DOTALL | re.IGNORECASE)
            explanation = ""
            if expl_match:
                explanation = expl_match.group(1).strip()[:500]  # Limit length
            
            # Clean question text - remove answer section from question
            question_text = q_content
            if answer_match:
                question_text = q_content[:answer_match.start()].strip()
            
            # Determine topic from content
            topic = determine_topic(question_text)
            
            if len(question_text) > 50:  # Only add substantial questions
                questions.append({
                    "source_file": source_file,
                    "original_num": q_num,
                    "topic": topic,
                    "question": clean_text(question_text),
                    "correctAnswer": answer,
                    "explanation": clean_text(explanation),
                    "multipleSelect": "," in answer if answer else False
                })
    
    return questions

def determine_topic(text):
    """Determine topic based on question content."""
    text_lower = text.lower()
    
    if any(kw in text_lower for kw in ["document ai", "!predict", "arctic-tilt", "parse_document"]):
        return "Document AI"
    elif any(kw in text_lower for kw in ["cortex search", "search service", "target_lag"]):
        return "Cortex Search"
    elif any(kw in text_lower for kw in ["cortex analyst", "semantic model", "text-to-sql"]):
        return "Cortex Analyst"
    elif any(kw in text_lower for kw in ["embed_text", "vector", "embedding", "cosine_similarity"]):
        return "Vector Embeddings"
    elif any(kw in text_lower for kw in ["fine-tun", "finetune", "training data", "prompt.*completion"]):
        return "Fine-tuning"
    elif any(kw in text_lower for kw in ["complete", "ai_complete", "llm function", "mistral", "llama"]):
        return "Cortex LLM Functions"
    elif any(kw in text_lower for kw in ["rag", "retrieval", "augmented generation"]):
        return "RAG"
    elif any(kw in text_lower for kw in ["spcs", "container", "compute pool"]):
        return "Snowpark Container Services"
    elif any(kw in text_lower for kw in ["cost", "credit", "governance", "allowlist"]):
        return "Cost & Governance"
    else:
        return "General Cortex AI"

def clean_text(text):
    """Clean OCR/extraction artifacts from text."""
    if not text:
        return ""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove common artifacts
    text = text.replace('\n', ' ').strip()
    return text

def normalize_question(question_text):
    """Normalize question text for deduplication."""
    # Remove extra spaces, lowercase, remove punctuation
    normalized = re.sub(r'[^\w\s]', '', question_text.lower())
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    # Take first 100 chars for comparison
    return normalized[:100]

def load_existing_questions(json_path):
    """Load existing questions from JSON file."""
    if not os.path.exists(json_path):
        return []
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get("questions", [])

def merge_questions(existing, new_questions):
    """Merge new questions avoiding duplicates."""
    # Create set of normalized existing questions
    existing_normalized = {normalize_question(q["question"]) for q in existing}
    
    added = 0
    duplicates = 0
    
    for new_q in new_questions:
        new_normalized = normalize_question(new_q["question"])
        
        # Check if similar question exists
        is_duplicate = False
        for existing_norm in existing_normalized:
            # Check similarity (simple approach: check if 70% of words match)
            new_words = set(new_normalized.split())
            existing_words = set(existing_norm.split())
            if len(new_words) > 0 and len(existing_words) > 0:
                overlap = len(new_words & existing_words) / max(len(new_words), len(existing_words))
                if overlap > 0.7:
                    is_duplicate = True
                    break
        
        if not is_duplicate and len(new_q["question"]) > 50:
            # Assign new ID
            new_q["id"] = len(existing) + added + 1
            existing.append(new_q)
            existing_normalized.add(new_normalized)
            added += 1
        else:
            duplicates += 1
    
    return existing, added, duplicates

def main():
    print("=" * 60)
    print("PDF Question Extractor & Merger")
    print("=" * 60)
    
    # Get all PDFs
    pdf_files = list(PDF_DIR.glob("*.pdf"))
    print(f"\nFound {len(pdf_files)} PDF files:")
    for pdf in pdf_files:
        print(f"  - {pdf.name}")
    
    # Extract from all PDFs
    all_new_questions = []
    for pdf_path in pdf_files:
        print(f"\nProcessing: {pdf_path.name}")
        text = extract_text_from_pdf(pdf_path)
        print(f"  Extracted {len(text)} characters")
        
        questions = parse_questions_from_text(text, pdf_path.name)
        print(f"  Found {len(questions)} questions")
        all_new_questions.extend(questions)
    
    print(f"\nTotal new questions extracted: {len(all_new_questions)}")
    
    # Load existing questions
    print(f"\nLoading existing questions from: {OUTPUT_JSON}")
    existing = load_existing_questions(OUTPUT_JSON)
    print(f"Existing questions: {len(existing)}")
    
    # Merge
    merged, added, duplicates = merge_questions(existing, all_new_questions)
    print(f"\nMerge results:")
    print(f"  Added: {added}")
    print(f"  Duplicates skipped: {duplicates}")
    print(f"  Total questions now: {len(merged)}")
    
    # Save updated JSON
    if added > 0:
        # Load full JSON structure
        with open(OUTPUT_JSON, 'r', encoding='utf-8') as f:
            full_data = json.load(f)
        
        full_data["questions"] = merged
        full_data["metadata"]["totalQuestions"] = len(merged)
        full_data["metadata"]["lastUpdated"] = "2026-01-19"
        full_data["metadata"]["pdfSources"] = [pdf.name for pdf in pdf_files]
        
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(full_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nSaved updated JSON to: {OUTPUT_JSON}")
    else:
        print("\nNo new questions to add.")
    
    # Also save extracted questions separately
    extracted_json = JSON_DIR / "pdf_extracted_questions.json"
    with open(extracted_json, 'w', encoding='utf-8') as f:
        json.dump({"questions": all_new_questions, "source": "PDFs", "count": len(all_new_questions)}, f, indent=2)
    print(f"Saved PDF extracts to: {extracted_json}")

if __name__ == "__main__":
    main()
