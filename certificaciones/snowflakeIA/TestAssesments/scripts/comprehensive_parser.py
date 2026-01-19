"""
Comprehensive parser that processes the OCR text more intelligently.
This script understands that questions and answers can span multiple images.
"""
import json
import re
from typing import List, Dict, Tuple

def load_json(filepath: str) -> List[Dict]:
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data, filepath: str):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def fix_ocr(text: str) -> str:
    """Fix common OCR errors."""
    replacements = {
        ' ot ': ' of ', 'ot ': 'of ',
        ' tor ': ' for ', 'tor ': 'for ',
        ' trom ': ' from ', 'trom ': 'from ',
        'tine-': 'fine-', ' tine ': ' fine ',
        'tile': 'file', 'tiles': 'files',
        'tunction': 'function', 'tunctions': 'functions',
        'ettect': 'effect', 'etticient': 'efficient',
        'specitic': 'specific', 'specilic': 'specific',
        'detault': 'default', 'ditterent': 'different',
        'contidence': 'confidence', 'intormation': 'information',
        'perormance': 'performance', 'signiticant': 'significant',
        'GBImo': 'GB/mo', 'GBImonth': 'GB/month',
        'NIJLC': 'NULL', 'NULC': 'NULL',
        'æython': 'Python', 'atter': 'after',
        'betre': 'before', ' lt ': ' it ',
        'tails': 'fails', 'tail': 'fail',
        'contorm': 'conform', 'detine': 'define',
        'intluence': 'influence', 'benetit': 'benefit',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return re.sub(r'\s+', ' ', text).strip()

def find_all_answers(text: str) -> List[Tuple[str, int]]:
    """Find all Answer: patterns and their positions."""
    pattern = r'Answer:\s*([A-E](?:,[A-E])*)'
    matches = []
    for m in re.finditer(pattern, text):
        matches.append((m.group(1), m.start()))
    return matches

def find_question_number_before(text: str, pos: int) -> Tuple[int, str]:
    """Find the question number that appears before a given position."""
    # Look backwards for question number pattern
    before_text = text[:pos]
    
    # Find all potential question numbers
    pattern = r'(\d{1,2})\s*[\.\-]\s*[A-Z]'
    matches = list(re.finditer(pattern, before_text))
    
    if matches:
        last_match = matches[-1]
        q_num = int(last_match.group(1))
        if 1 <= q_num <= 60:
            # Extract question text after the number
            start_pos = last_match.end() - 1  # -1 to include the first letter
            question_text = before_text[start_pos:pos]
            # Clean up
            question_text = re.sub(r'Answer:.*$', '', question_text, flags=re.DOTALL)
            question_text = re.sub(r'[A-E][\.\)]\s*Option\s*[A-E]', '', question_text)
            question_text = question_text.strip()
            return q_num, question_text
    
    return 0, ""

def extract_explanation_after(text: str, pos: int) -> str:
    """Extract explanation text after an answer position."""
    after_text = text[pos:]
    
    # Find "Explanation:" and extract until next question
    pattern = r'Explanation:\s*(.+?)(?=\d{1,2}\s*[\.\-]\s*[A-Z]|Answer:|$)'
    match = re.search(pattern, after_text, re.DOTALL)
    
    if match:
        explanation = match.group(1).strip()
        explanation = re.sub(r'\s+', ' ', explanation)
        return explanation[:2000]
    
    return ""

def process_combined_text(entries: List[Dict]) -> List[Dict]:
    """Process all entries as combined text."""
    # Combine all text
    combined = " ".join([fix_ocr(e['text']) for e in entries])
    
    # Find all answers
    answers = find_all_answers(combined)
    print(f"   Found {len(answers)} Answer: patterns")
    
    questions = {}
    
    for answer, pos in answers:
        q_num, q_text = find_question_number_before(combined, pos)
        explanation = extract_explanation_after(combined, pos)
        
        if q_num > 0:
            if q_num not in questions:
                questions[q_num] = {
                    'number': q_num,
                    'question': q_text[:800],
                    'answer': answer,
                    'explanation': explanation
                }
            else:
                # Update if we have better data
                if len(q_text) > len(questions[q_num]['question']):
                    questions[q_num]['question'] = q_text[:800]
                if len(explanation) > len(questions[q_num]['explanation']):
                    questions[q_num]['explanation'] = explanation
    
    return list(questions.values())

def extract_questions_by_image_pairs(entries: List[Dict]) -> List[Dict]:
    """
    Many times: Image N has question, Image N+1 has answer/explanation.
    Process pairs of images together.
    """
    questions = {}
    
    for i in range(len(entries)):
        entry = entries[i]
        text = fix_ocr(entry['text'])
        
        # Check if this image has an Answer:
        ans_match = re.search(r'Answer:\s*([A-E](?:,[A-E])*)', text)
        if not ans_match:
            continue
        
        answer = ans_match.group(1)
        
        # Look for question number in this image or previous
        q_num = None
        q_text = ""
        
        # Check current image
        q_match = re.search(r'(\d{1,2})\s*[\.\-]\s*([A-Z].+?)(?=A[\.\)]\s*[A-Z]|Option|Answer:|$)', text, re.DOTALL)
        if q_match:
            try:
                q_num = int(q_match.group(1))
                q_text = q_match.group(2).strip()
            except:
                pass
        
        # If not found, check previous image
        if not q_num and i > 0:
            prev_text = fix_ocr(entries[i-1]['text'])
            q_match = re.search(r'(\d{1,2})\s*[\.\-]\s*([A-Z].+?)(?=A[\.\)]\s*[A-Z]|Option|Answer:|$)', prev_text, re.DOTALL)
            if q_match:
                try:
                    q_num = int(q_match.group(1))
                    q_text = q_match.group(2).strip()
                except:
                    pass
        
        # Extract explanation
        expl_match = re.search(r'Explanation:\s*(.+?)(?=\d{1,2}\s*[\.\-]\s*[A-Z]|$)', text, re.DOTALL)
        explanation = expl_match.group(1).strip() if expl_match else ""
        
        if q_num and 1 <= q_num <= 60:
            if q_num not in questions:
                questions[q_num] = {
                    'number': q_num,
                    'question': q_text[:800],
                    'answer': answer,
                    'explanation': explanation[:1500]
                }
            else:
                if len(q_text) > len(questions[q_num]['question']):
                    questions[q_num]['question'] = q_text[:800]
                if len(explanation) > len(questions[q_num]['explanation']):
                    questions[q_num]['explanation'] = explanation[:1500]
    
    return list(questions.values())

def extract_by_analyzing_flow(entries: List[Dict]) -> List[Dict]:
    """
    Analyze the flow: Each "Answer: X" corresponds to a question.
    Work backwards from each answer to find its question.
    """
    # Build full text with markers
    full_text = ""
    markers = []
    
    for i, entry in enumerate(entries):
        text = fix_ocr(entry['text'])
        start = len(full_text)
        full_text += text + " "
        markers.append((i, start, len(full_text), entry['image']))
    
    # Find all Answer patterns
    answer_pattern = r'Answer:\s*([A-E](?:,[A-E])*)'
    answers = list(re.finditer(answer_pattern, full_text))
    print(f"   Found {len(answers)} answer patterns in combined text")
    
    questions = {}
    
    for ans_match in answers:
        answer = ans_match.group(1)
        ans_pos = ans_match.start()
        
        # Find question number before this answer
        before = full_text[:ans_pos]
        
        # Find the last question number pattern before Answer:
        q_nums = list(re.finditer(r'(\d{1,2})\s*[\.\-]\s*[A-Z]', before))
        
        if q_nums:
            last_q = q_nums[-1]
            try:
                q_num = int(last_q.group(1))
                if not (1 <= q_num <= 60):
                    continue
            except:
                continue
            
            # Extract question text between number and answer
            q_start = last_q.end() - 1
            q_end = ans_pos
            q_text = before[q_start:q_end]
            
            # Clean up question text
            q_text = re.sub(r'[A-E][\.\)]\s*Option\s*[A-E]', '', q_text)
            q_text = re.sub(r'A\.\s*Option\s*A.*$', '', q_text, flags=re.DOTALL)
            q_text = re.sub(r'\s+', ' ', q_text).strip()
            
            # Extract explanation
            after = full_text[ans_pos:]
            expl_match = re.search(r'Explanation:\s*(.+?)(?=\d{1,2}\s*[\.\-]\s*[A-Z]|Answer:|$)', after, re.DOTALL)
            explanation = ""
            if expl_match:
                explanation = re.sub(r'\s+', ' ', expl_match.group(1).strip())
            
            # Store
            if q_num not in questions:
                questions[q_num] = {
                    'number': q_num,
                    'question': q_text[:1000],
                    'answer': answer,
                    'explanation': explanation[:2000]
                }
            else:
                if len(q_text) > len(questions[q_num]['question']):
                    questions[q_num]['question'] = q_text[:1000]
                if len(explanation) > len(questions[q_num]['explanation']):
                    questions[q_num]['explanation'] = explanation[:2000]
    
    return list(questions.values())

def categorize(text: str) -> str:
    """Categorize question by topic."""
    t = text.lower()
    if 'document ai' in t or 'document al' in t or '!predict' in t:
        return 'Document AI'
    if 'cortex search' in t:
        return 'Cortex Search'
    if 'cortex analyst' in t or 'semantic model' in t:
        return 'Cortex Analyst'
    if 'fine-tun' in t or 'fine tun' in t:
        return 'Fine-tuning'
    if 'vector' in t or 'embed' in t:
        return 'Vector Embeddings'
    if 'rag' in t or 'retrieval' in t:
        return 'RAG'
    if 'complete' in t or 'ai_complete' in t or 'llm function' in t:
        return 'Cortex LLM Functions'
    if 'spcs' in t or 'container' in t:
        return 'Snowpark Container Services'
    if 'cost' in t or 'billing' in t or 'credit' in t:
        return 'Cost & Governance'
    if 'privilege' in t or 'grant' in t or 'rbac' in t:
        return 'Access Control'
    return 'General Cortex AI'

def build_output(questions: List[Dict]) -> Dict:
    """Build final output."""
    questions.sort(key=lambda x: x['number'])
    
    final = []
    for q in questions:
        # Clean question
        question = q['question']
        question = re.sub(r'^[A-E][\.\)]\s*', '', question)
        question = question.strip()
        
        final.append({
            'id': q['number'],
            'question': question,
            'correct_answer': q['answer'],
            'explanation': q['explanation'],
            'topic': categorize(question + " " + q['explanation'])
        })
    
    return {
        'exam': {
            'code': 'GES-C01',
            'name': 'SnowPro Specialty: Generative AI',
            'provider': 'Snowflake'
        },
        'stats': {
            'total': len(final),
            'source': 'OCR from practice exam screenshots'
        },
        'questions': final
    }

def main():
    print("="*60)
    print("GES-C01 Question Extractor v3")
    print("="*60)
    
    entries = load_json('extracted_text.json')
    print(f"\nLoaded {len(entries)} OCR entries")
    
    print("\n--- Method 1: Flow Analysis ---")
    q1 = extract_by_analyzing_flow(entries)
    print(f"   Extracted: {len(q1)} questions")
    
    print("\n--- Method 2: Image Pairs ---")
    q2 = extract_questions_by_image_pairs(entries)
    print(f"   Extracted: {len(q2)} questions")
    
    # Merge results
    all_q = {}
    for q in q1 + q2:
        n = q['number']
        if n not in all_q:
            all_q[n] = q
        else:
            if len(q['question']) > len(all_q[n]['question']):
                all_q[n]['question'] = q['question']
            if len(q['explanation']) > len(all_q[n]['explanation']):
                all_q[n]['explanation'] = q['explanation']
    
    print(f"\n--- Merged: {len(all_q)} unique questions ---")
    
    # Build output
    output = build_output(list(all_q.values()))
    save_json(output, 'GES-C01_Extracted_Questions.json')
    
    print(f"\nSaved: GES-C01_Extracted_Questions.json")
    print(f"Total questions: {output['stats']['total']}")
    
    # Topic breakdown
    topics = {}
    for q in output['questions']:
        t = q['topic']
        topics[t] = topics.get(t, 0) + 1
    
    print("\nBy Topic:")
    for t, c in sorted(topics.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")
    
    # Show some samples
    print("\n" + "="*60)
    print("SAMPLE QUESTIONS:")
    print("="*60)
    for q in output['questions'][:5]:
        print(f"\n[Q{q['id']}] {q['topic']}")
        print(f"Q: {q['question'][:150]}...")
        print(f"A: {q['correct_answer']}")

if __name__ == '__main__':
    main()
