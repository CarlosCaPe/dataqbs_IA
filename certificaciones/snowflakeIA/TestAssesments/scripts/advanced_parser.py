"""
Advanced parser for OCR extracted exam questions.
This script properly handles the OCR text structure from GES-C01 exam screenshots.
"""
import json
import re
from typing import List, Dict, Optional, Tuple

def load_json(filepath: str) -> List[Dict]:
    """Load JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def fix_ocr_errors(text: str) -> str:
    """Fix common OCR errors in the text."""
    fixes = [
        (r'\bof\b', 'of'), (r'\bot\b', 'of'),
        (r'\bfor\b', 'for'), (r'\btor\b', 'for'),
        (r'\bfrom\b', 'from'), (r'\btrom\b', 'from'),
        (r'\bif\b', 'if'), (r'\bit\b', 'if'),
        (r'\bfine-', 'fine-'), (r'\btine-', 'fine-'),
        (r'\bfile\b', 'file'), (r'\btile\b', 'file'),
        (r'\bfiles\b', 'files'), (r'\btiles\b', 'files'),
        (r'NIJLC', 'NULL'), (r'NULC', 'NULL'),
        (r'æython', 'Python'),
        (r'GBImo', 'GB/mo'), (r'GBImonth', 'GB/month'),
        (r'\bfail\b', 'fail'), (r'\btail\b', 'fail'),
        (r'\bfails\b', 'fails'), (r'\btails\b', 'fails'),
        (r'\bfunction\b', 'function'), (r'\btunction\b', 'function'),
        (r'\beffective\b', 'effective'), (r'\bettective\b', 'effective'),
        (r'\befficiency\b', 'efficiency'), (r'\betticiency\b', 'efficiency'),
        (r'\bdefault\b', 'default'), (r'\bdetault\b', 'default'),
        (r'\bafter\b', 'after'), (r'\batter\b', 'after'),
        (r'\bbefore\b', 'before'), (r'\bbetre\b', 'before'),
        (r'\bdefine\b', 'define'), (r'\bdetine\b', 'define'),
        (r'\bdifferent\b', 'different'), (r'\bditterent\b', 'different'),
        (r'\bsignificant\b', 'significant'), (r'\bsigniticant\b', 'significant'),
        (r'\bconfidence\b', 'confidence'), (r'\bcontidence\b', 'confidence'),
        (r'\binformation\b', 'information'), (r'\bintormation\b', 'information'),
        (r'\bconform\b', 'conform'), (r'\bcontorm\b', 'conform'),
        (r'\bbenefits\b', 'benefits'), (r'\bbenetits\b', 'benefits'),
        (r'\binfluence\b', 'influence'), (r'\bintluence\b', 'influence'),
        (r'\bperformance\b', 'performance'), (r'\bperormance\b', 'performance'),
        (r'\bspecific\b', 'specific'), (r'\bspecitic\b', 'specific'),
        (r'Cortex Search Service', 'Cortex Search Service'),
    ]
    
    for pattern, replacement in fixes:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Clean multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_answer(text: str) -> Tuple[Optional[str], str]:
    """Extract answer from text. Returns (answer, remaining_text)."""
    # Pattern: Answer: A or Answer: A,B or Answer: A,B,C
    answer_pattern = r'Answer:\s*([A-E](?:,[A-E])*)'
    match = re.search(answer_pattern, text)
    if match:
        return match.group(1), text
    return None, text

def extract_explanation(text: str) -> Optional[str]:
    """Extract explanation from text."""
    # Find explanation section
    pattern = r'Explanation:\s*(.*?)(?=\d+\s*[\-\.]\s*[A-Z]|$)'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        explanation = match.group(1).strip()
        # Clean up and limit length
        explanation = fix_ocr_errors(explanation)
        return explanation[:2000]
    return None

def parse_all_questions(entries: List[Dict]) -> List[Dict]:
    """Parse all entries to extract questions."""
    questions = []
    seen_questions = set()
    
    # Combine all text for processing
    combined_entries = []
    for entry in entries:
        text = fix_ocr_errors(entry['text'])
        source = entry['image']
        combined_entries.append({
            'text': text,
            'source': source
        })
    
    # Process each entry
    for idx, entry in enumerate(combined_entries):
        text = entry['text']
        source = entry['source']
        
        # Skip the intro text (first image)
        if 'TFSTP' in text or 'Testpassport' in text.lower():
            # First image has intro + question 1
            # Extract question 1 from it
            q1_match = re.search(r'1\s*[\-\.]\s*(.+?)(?=A\.\s|$)', text, re.DOTALL)
            if q1_match:
                q_text = q1_match.group(1).strip()
                answer_match = re.search(r'Answer:\s*([A-E](?:,[A-E])*)', text)
                # Question 1 answer is in image 2
                continue
        
        # Find question number
        q_num_match = re.match(r'.*?(\d+)\s*[\-\.]', text[:50])
        q_num = int(q_num_match.group(1)) if q_num_match else None
        
        # Find answer
        answer, _ = extract_answer(text)
        
        # Find explanation
        explanation = extract_explanation(text)
        
        # Check if this is primarily an answer/explanation entry
        has_answer_start = text.strip().startswith('Answer:')
        
        if answer:
            # Try to extract question text
            question_text = ""
            
            # Look for question text pattern
            if q_num:
                # Pattern: number followed by question text before options
                q_pattern = rf'{q_num}\s*[\-\.]?\s*(.+?)(?=\s*A[\.\)]\s*[A-Z]|A\.\s*Option|$)'
                q_match = re.search(q_pattern, text, re.DOTALL | re.IGNORECASE)
                if q_match:
                    question_text = q_match.group(1).strip()
            
            # If no question text found, look for significant text before Answer:
            if not question_text:
                before_answer = text.split('Answer:')[0] if 'Answer:' in text else text
                # Remove option patterns
                before_answer = re.sub(r'[A-E][\.\)]\s*[Oo]ption\s*[A-E]', '', before_answer)
                before_answer = before_answer.strip()
                if len(before_answer) > 50:
                    question_text = before_answer[:500]
            
            # Clean question text
            question_text = fix_ocr_errors(question_text)
            question_text = re.sub(r'^[A-E][\.\)]\s*', '', question_text)  # Remove leading option markers
            question_text = re.sub(r'\s+', ' ', question_text).strip()
            
            # Create question entry
            question = {
                'number': q_num,
                'question': question_text,
                'answer': answer,
                'explanation': explanation or "",
                'source_images': [source]
            }
            
            # Deduplication key
            dedup_key = f"{q_num}_{answer}" if q_num else f"{question_text[:50]}_{answer}"
            
            if dedup_key not in seen_questions:
                seen_questions.add(dedup_key)
                questions.append(question)
    
    return questions

def enhance_questions_from_context(questions: List[Dict], entries: List[Dict]) -> List[Dict]:
    """Enhance questions by looking at related entries for context."""
    # Create a mapping from question number to all related text
    q_context = {}
    
    for entry in entries:
        text = fix_ocr_errors(entry['text'])
        source = entry['image']
        
        # Find all question numbers mentioned
        q_nums = re.findall(r'\b(\d+)\s*[\-\.]', text[:100])
        for q_num_str in q_nums:
            q_num = int(q_num_str)
            if q_num not in q_context:
                q_context[q_num] = []
            q_context[q_num].append({'text': text, 'source': source})
    
    # Enhance questions with additional context
    for q in questions:
        q_num = q.get('number')
        if q_num and q_num in q_context:
            # Look for better question text
            for ctx in q_context[q_num]:
                ctx_text = ctx['text']
                # Try to extract cleaner question text
                q_pattern = rf'{q_num}\s*[\-\.]?\s*(.+?)(?=\s*[A-E][\.\)]\s|Answer:|$)'
                q_match = re.search(q_pattern, ctx_text, re.DOTALL)
                if q_match:
                    potential_q = q_match.group(1).strip()
                    potential_q = fix_ocr_errors(potential_q)
                    if len(potential_q) > len(q['question']) and len(potential_q) < 1000:
                        q['question'] = potential_q
    
    return questions

def build_final_json(questions: List[Dict]) -> Dict:
    """Build the final JSON structure."""
    # Sort by question number
    numbered = [q for q in questions if q.get('number')]
    unnumbered = [q for q in questions if not q.get('number')]
    numbered.sort(key=lambda x: x['number'])
    
    # Combine and clean up
    final_questions = []
    for q in numbered + unnumbered:
        final_q = {
            'id': q.get('number', len(final_questions) + 100),
            'question': q['question'],
            'correct_answer': q['answer'],
            'explanation': q['explanation'],
            'source': q.get('source_images', [])[0] if q.get('source_images') else 'unknown'
        }
        final_questions.append(final_q)
    
    return {
        "exam_code": "GES-C01",
        "exam_name": "SnowPro Specialty: Generative AI",
        "provider": "Snowflake",
        "total_questions": len(final_questions),
        "source_note": "OCR extracted from exam practice images",
        "questions": final_questions
    }

def main():
    input_file = 'extracted_text.json'
    output_file = 'parsed_questions_v2.json'
    
    print("Loading extracted OCR text...")
    entries = load_json(input_file)
    print(f"Loaded {len(entries)} image entries")
    
    print("\nParsing questions...")
    questions = parse_all_questions(entries)
    print(f"Initial parse: {len(questions)} questions")
    
    print("\nEnhancing questions with context...")
    questions = enhance_questions_from_context(questions, entries)
    
    print("\nBuilding final JSON...")
    final_data = build_final_json(questions)
    
    # Save
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved to: {output_file}")
    print(f"Total questions: {final_data['total_questions']}")
    
    # Show samples
    print("\n" + "="*60)
    print("SAMPLE QUESTIONS:")
    print("="*60)
    for q in final_data['questions'][:5]:
        print(f"\n[Q{q['id']}] {q['question'][:150]}...")
        print(f"Answer: {q['correct_answer']}")
        print(f"Explanation: {q['explanation'][:100]}..." if q['explanation'] else "")

if __name__ == '__main__':
    main()
