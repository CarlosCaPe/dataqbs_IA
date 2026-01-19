"""
Final comprehensive parser for GES-C01 exam questions.
This script reconstructs the full questions by analyzing the OCR text patterns.
"""
import json
import re
from typing import List, Dict, Optional, Tuple

def load_json(filepath: str) -> List[Dict]:
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def fix_ocr(text: str) -> str:
    """Fix common OCR errors."""
    # Simple character substitutions
    text = text.replace('ot ', 'of ').replace(' ot ', ' of ')
    text = text.replace('tor ', 'for ').replace(' tor ', ' for ')
    text = text.replace('trom ', 'from ').replace(' trom ', ' from ')
    text = text.replace('tine-', 'fine-').replace(' tine ', ' fine ')
    text = text.replace('tile', 'file')
    text = text.replace('tunction', 'function')
    text = text.replace('ettect', 'effect')
    text = text.replace('specilic', 'specific')
    text = text.replace('specitic', 'specific')
    text = text.replace('detault', 'default')
    text = text.replace('ditterent', 'different')
    text = text.replace('contidence', 'confidence')
    text = text.replace('intormation', 'information')
    text = text.replace('perormance', 'performance')
    text = text.replace('signiticant', 'significant')
    text = text.replace('GBImo', 'GB/mo')
    text = text.replace('NIJLC', 'NULL')
    text = text.replace('æython', 'Python')
    text = text.replace('atter', 'after')
    text = text.replace('betre', 'before')
    text = text.replace(' lt ', ' it ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_all_questions_and_answers(entries: List[Dict]) -> List[Dict]:
    """
    Extract all questions by analyzing the full text flow.
    The OCR images follow a pattern:
    - Question text followed by options (A, B, C, D, E)
    - Next image often contains Answer and Explanation
    - Sometimes question continues from previous image
    """
    all_text = "\n\n=== IMAGE BREAK ===\n\n".join([fix_ocr(e['text']) for e in entries])
    
    # Find all question patterns
    questions = []
    
    # Pattern for finding questions: "1." or "1-" or "1 -" followed by text
    # Answer pattern: "Answer: X" or "Answer: X,Y"
    
    # First pass: Find all answers with their question numbers
    answer_pattern = r'(\d+)\s*[\.\-].*?Answer:\s*([A-E](?:,[A-E])*)'
    
    # Actually, let's process sequentially through the combined text
    # Split by "Answer:" to find Q&A pairs
    
    segments = re.split(r'(Answer:\s*[A-E](?:,[A-E])*)', all_text)
    
    current_q_num = 0
    current_q_text = ""
    
    results = []
    
    for i in range(0, len(segments) - 1, 2):
        content = segments[i]
        answer_part = segments[i + 1] if i + 1 < len(segments) else ""
        
        # Extract question number from content
        q_nums = re.findall(r'(\d{1,2})\s*[\.\-]\s*[A-Z]', content)
        
        # Get the latest question number
        if q_nums:
            try:
                latest_q = int(q_nums[-1])
                if 1 <= latest_q <= 60:
                    current_q_num = latest_q
            except:
                pass
        
        # Extract answer
        ans_match = re.search(r'Answer:\s*([A-E](?:,[A-E])*)', answer_part)
        answer = ans_match.group(1) if ans_match else ""
        
        # Look for the question text
        # Find text after the question number and before options/answer
        if current_q_num > 0:
            q_text_pattern = rf'{current_q_num}\s*[\.\-]?\s*(.+?)(?=\s*A[\.\)]\s*[A-Z]|A\.\s*Option|Answer:|$)'
            q_match = re.search(q_text_pattern, content, re.DOTALL)
            if q_match:
                current_q_text = q_match.group(1).strip()
        
        # Get explanation (text after Answer until next question)
        remaining = ""
        if i + 2 < len(segments):
            remaining = segments[i + 2]
        
        expl_match = re.search(r'Explanation:\s*(.+?)(?=\d{1,2}\s*[\.\-]\s*[A-Z]|=== IMAGE|$)', 
                               answer_part + remaining, re.DOTALL)
        explanation = expl_match.group(1).strip() if expl_match else ""
        
        if answer and current_q_num > 0:
            results.append({
                'number': current_q_num,
                'question': current_q_text[:800],
                'answer': answer,
                'explanation': explanation[:1500]
            })
    
    return results

def manual_extraction(entries: List[Dict]) -> List[Dict]:
    """
    Manually parse each entry to extract question, answer, and explanation.
    This is a more reliable approach given the OCR output structure.
    """
    questions = {}  # Use dict to dedupe by question number
    
    for entry in entries:
        text = fix_ocr(entry['text'])
        source = entry['image']
        
        # Find answer in this entry
        ans_match = re.search(r'Answer:\s*([A-E](?:,[A-E])*)', text)
        if not ans_match:
            continue
            
        answer = ans_match.group(1)
        
        # Find question number - look at beginning of text
        q_num = None
        
        # Check for question number at start
        q_start = re.match(r'^.*?(\d{1,2})\s*[\.\-]\s*[A-Z]', text[:100])
        if q_start:
            try:
                q_num = int(q_start.group(1))
            except:
                pass
        
        # If not found at start, look for any question number in context
        if not q_num:
            # Check if text references a specific question
            q_refs = re.findall(r'\b(\d{1,2})\s*[\.\-]', text[:200])
            for ref in q_refs:
                try:
                    n = int(ref)
                    if 1 <= n <= 60:
                        q_num = n
                        break
                except:
                    pass
        
        # Extract question text
        question_text = ""
        if q_num:
            # Try to find the question text after the number
            q_pattern = rf'{q_num}\s*[\.\-]?\s*(.+?)(?=\s*A[\.\)]\s*[A-Z]|Option\s*A|Answer:|$)'
            q_match = re.search(q_pattern, text, re.DOTALL | re.IGNORECASE)
            if q_match:
                question_text = q_match.group(1).strip()
                question_text = re.sub(r'\s+', ' ', question_text)
        
        # If no question text found, try to get text before options
        if not question_text:
            before_answer = text.split('Answer:')[0]
            # Remove option markers
            before_answer = re.sub(r'[A-E][\.\)]\s*(Option\s*[A-E]|option\s*[A-E])', '', before_answer)
            before_answer = re.sub(r'A\.\s*Option\s*A.*', '', before_answer, flags=re.DOTALL)
            before_answer = before_answer.strip()
            if len(before_answer) > 30:
                question_text = before_answer[:600]
        
        # Extract explanation
        expl_match = re.search(r'Explanation:\s*(.+?)(?=\d{1,2}\s*[\.\-]\s*[A-Z]|$)', text, re.DOTALL)
        explanation = expl_match.group(1).strip() if expl_match else ""
        explanation = re.sub(r'\s+', ' ', explanation)[:1500]
        
        # Store or update
        if q_num:
            if q_num not in questions:
                questions[q_num] = {
                    'number': q_num,
                    'question': question_text,
                    'answer': answer,
                    'explanation': explanation,
                    'sources': [source]
                }
            else:
                # Update if we have better data
                if len(question_text) > len(questions[q_num]['question']):
                    questions[q_num]['question'] = question_text
                if len(explanation) > len(questions[q_num]['explanation']):
                    questions[q_num]['explanation'] = explanation
                if source not in questions[q_num]['sources']:
                    questions[q_num]['sources'].append(source)
    
    return list(questions.values())

def enrich_from_full_text(questions: List[Dict], entries: List[Dict]) -> List[Dict]:
    """
    Enrich questions by looking at the full combined text for better extraction.
    """
    # Combine all text
    full_text = "\n\n".join([fix_ocr(e['text']) for e in entries])
    
    for q in questions:
        q_num = q['number']
        
        # Try to find better question text
        patterns = [
            rf'{q_num}\s*[\.\-]\s*(.+?)(?=\s*A[\.\)]\s*[A-Z])',
            rf'{q_num}\s*[\.\-]\s*(.+?)(?=Option\s*A)',
            rf'{q_num}\s*[\.\-]\s*(.+?)(?=Answer:)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, full_text, re.DOTALL)
            if match:
                potential = match.group(1).strip()
                potential = re.sub(r'\s+', ' ', potential)
                if 50 < len(potential) < 800 and len(potential) > len(q['question']):
                    q['question'] = potential
                    break
        
        # Try to find better explanation
        expl_pattern = rf'{q_num}.*?Answer:\s*{q["answer"]}.*?Explanation:\s*(.+?)(?=\d{{1,2}}\s*[\.\-]\s*[A-Z]|$)'
        expl_match = re.search(expl_pattern, full_text, re.DOTALL)
        if expl_match:
            potential_expl = expl_match.group(1).strip()
            potential_expl = re.sub(r'\s+', ' ', potential_expl)[:1500]
            if len(potential_expl) > len(q['explanation']):
                q['explanation'] = potential_expl
    
    return questions

def create_final_output(questions: List[Dict]) -> Dict:
    """Create the final JSON output."""
    # Sort by question number
    questions.sort(key=lambda x: x['number'])
    
    # Clean and format
    final_questions = []
    for q in questions:
        # Clean question text
        question_text = q['question']
        question_text = re.sub(r'^[A-E][\.\)]\s*', '', question_text)  # Remove leading option markers
        question_text = re.sub(r'\s*Option\s*[A-E]\s*$', '', question_text)  # Remove trailing option refs
        question_text = question_text.strip()
        
        # Clean explanation
        explanation = q['explanation']
        explanation = re.sub(r'^Option\s+[A-E]\s+', '', explanation)  # Remove leading "Option X"
        
        final_q = {
            'id': q['number'],
            'question': question_text,
            'correct_answer': q['answer'],
            'explanation': explanation,
            'topic': categorize_question(question_text + " " + explanation)
        }
        final_questions.append(final_q)
    
    return {
        'exam_info': {
            'code': 'GES-C01',
            'name': 'SnowPro Specialty: Generative AI',
            'provider': 'Snowflake',
            'passing_score': '750/1000',
            'duration': '115 minutes',
            'price': '$375 USD'
        },
        'metadata': {
            'total_questions': len(final_questions),
            'source': 'OCR extracted from exam practice screenshots',
            'extraction_date': '2025-01-27'
        },
        'questions': final_questions
    }

def categorize_question(text: str) -> str:
    """Categorize question by topic."""
    text_lower = text.lower()
    
    if 'document ai' in text_lower or 'document al' in text_lower or '!predict' in text_lower:
        return 'Document AI'
    elif 'cortex search' in text_lower:
        return 'Cortex Search'
    elif 'cortex analyst' in text_lower or 'semantic model' in text_lower:
        return 'Cortex Analyst'
    elif 'fine-tun' in text_lower or 'fine tun' in text_lower:
        return 'Fine-tuning'
    elif 'vector' in text_lower or 'embed' in text_lower:
        return 'Vector Embeddings'
    elif 'rag' in text_lower or 'retrieval' in text_lower:
        return 'RAG'
    elif 'complete' in text_lower or 'llm function' in text_lower or 'ai_complete' in text_lower:
        return 'Cortex LLM Functions'
    elif 'spcs' in text_lower or 'container' in text_lower or 'snowpark container' in text_lower:
        return 'Snowpark Container Services'
    elif 'cost' in text_lower or 'billing' in text_lower or 'credit' in text_lower:
        return 'Cost & Governance'
    elif 'security' in text_lower or 'rbac' in text_lower or 'privilege' in text_lower or 'grant' in text_lower:
        return 'Access Control & Security'
    else:
        return 'General Cortex AI'

def main():
    input_file = 'extracted_text.json'
    output_file = 'GES-C01_Questions_Final.json'
    
    print("="*60)
    print("GES-C01 Exam Questions Parser")
    print("="*60)
    
    print("\n1. Loading OCR extracted text...")
    entries = load_json(input_file)
    print(f"   Loaded {len(entries)} image entries")
    
    print("\n2. Extracting questions and answers...")
    questions = manual_extraction(entries)
    print(f"   Found {len(questions)} unique questions")
    
    print("\n3. Enriching with additional context...")
    questions = enrich_from_full_text(questions, entries)
    
    print("\n4. Building final output...")
    output = create_final_output(questions)
    
    # Save
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n5. Saved to: {output_file}")
    
    # Statistics
    print("\n" + "="*60)
    print("EXTRACTION SUMMARY")
    print("="*60)
    print(f"Total questions extracted: {output['metadata']['total_questions']}")
    
    # Topic breakdown
    topics = {}
    for q in output['questions']:
        topic = q['topic']
        topics[topic] = topics.get(topic, 0) + 1
    
    print("\nQuestions by Topic:")
    for topic, count in sorted(topics.items(), key=lambda x: -x[1]):
        print(f"  - {topic}: {count}")
    
    # Sample output
    print("\n" + "="*60)
    print("SAMPLE QUESTIONS")
    print("="*60)
    for q in output['questions'][:3]:
        print(f"\n[Q{q['id']}] Topic: {q['topic']}")
        print(f"Question: {q['question'][:200]}...")
        print(f"Answer: {q['correct_answer']}")

if __name__ == '__main__':
    main()
