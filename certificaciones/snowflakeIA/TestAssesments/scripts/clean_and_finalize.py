"""
Final cleaning and deduplication script for GES-C01 exam questions.
This script cleans OCR artifacts, deduplicates questions, and produces the final JSON.
"""
import json
import re
from typing import List, Dict

def load_json(filepath: str):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data, filepath: str):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def clean_text(text: str) -> str:
    """Clean OCR artifacts and fix common errors."""
    if not text:
        return ""
    
    # Fix common OCR errors
    fixes = [
        (r'\bnof\b', 'not'),
        (r'\bfor\b', 'for'),
        (r'\btrom\b', 'from'),
        (r'\btile\b', 'file'),
        (r'\btiles\b', 'files'),
        (r'\btunction\b', 'function'),
        (r'\btunctions\b', 'functions'),
        (r'\bettect\b', 'effect'),
        (r'\bettective\b', 'effective'),
        (r'\betticiency\b', 'efficiency'),
        (r'\bspecitic\b', 'specific'),
        (r'\bdetault\b', 'default'),
        (r'\bditterent\b', 'different'),
        (r'\bcontidence\b', 'confidence'),
        (r'\bintormation\b', 'information'),
        (r'\bperormance\b', 'performance'),
        (r'\bsigniticant\b', 'significant'),
        (r'\bsigniticantly\b', 'significantly'),
        (r'\battected\b', 'affected'),
        (r'\bcontorm\b', 'conform'),
        (r'\bdetine\b', 'define'),
        (r'\bdetined\b', 'defined'),
        (r'\bdetines\b', 'defines'),
        (r'\bintluence\b', 'influence'),
        (r'\bbenetit\b', 'benefit'),
        (r'\bbenetits\b', 'benefits'),
        (r'\batter\b', 'after'),
        (r'\bbetre\b', 'before'),
        (r'\btail\b', 'fail'),
        (r'\btails\b', 'fails'),
        (r'\btailure\b', 'failure'),
        (r'\btailures\b', 'failures'),
        (r'\btine-\b', 'fine-'),
        (r'\btine\b', 'fine'),
        (r'\bdetailed\b', 'detailed'),
        (r'\bdefailed\b', 'detailed'),
        (r'GBImo', 'GB/mo'),
        (r'GBImonth', 'GB/month'),
        (r'NIJLC', 'NULL'),
        (r'NULC', 'NULL'),
        (r'æython', 'Python'),
        (r'chatbof', 'chatbot'),
        (r'vecfor', 'vector'),
        (r'tilter', 'filter'),
        (r'tilters', 'filters'),
        (r'\blt\b', 'it'),
    ]
    
    for pattern, replacement in fixes:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Clean multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Fix "nof" to "not" more aggressively
    text = text.replace(' nof ', ' not ')
    text = text.replace('nof ', 'not ')
    text = text.replace(' nof', ' not')
    
    return text.strip()

def dedupe_and_clean(questions: List[Dict]) -> List[Dict]:
    """Deduplicate questions and clean content."""
    seen = {}
    cleaned = []
    
    for q in questions:
        q_id = q.get('id', 0)
        
        # Skip if we've seen this question ID
        if q_id in seen:
            continue
        
        # Clean the question and explanation
        q_text = clean_text(q.get('question', ''))
        explanation = clean_text(q.get('explanation', ''))
        
        # Remove truncated option text at end of questions
        q_text = re.sub(r'\s*[A-E]\.\s*Option\s*[A-E]\s*$', '', q_text)
        q_text = re.sub(r'\s*[A-E]\.\s*The\s*$', '', q_text)
        q_text = re.sub(r'\s*[A-E]\.\s*$', '', q_text)
        
        cleaned_q = {
            'id': q_id,
            'question': q_text,
            'correct_answer': q.get('correct_answer', ''),
            'explanation': explanation,
            'topic': q.get('topic', 'General Cortex AI')
        }
        
        seen[q_id] = True
        cleaned.append(cleaned_q)
    
    return cleaned

def validate_answers(questions: List[Dict]) -> List[Dict]:
    """Validate that answers are properly formatted."""
    valid = []
    
    for q in questions:
        answer = q.get('correct_answer', '')
        
        # Validate answer format (single letter or comma-separated)
        if re.match(r'^[A-E](,[A-E])*$', answer):
            valid.append(q)
        else:
            print(f"  Warning: Invalid answer format for Q{q['id']}: '{answer}'")
            # Try to extract valid answer
            extracted = re.findall(r'[A-E]', answer)
            if extracted:
                q['correct_answer'] = ','.join(extracted[:3])  # Max 3 answers
                valid.append(q)
    
    return valid

def create_final_output(questions: List[Dict]) -> Dict:
    """Create the final structured output."""
    # Sort by question ID
    questions.sort(key=lambda x: x['id'])
    
    # Renumber questions sequentially
    for i, q in enumerate(questions, 1):
        q['id'] = i
    
    # Count topics
    topics = {}
    for q in questions:
        t = q['topic']
        topics[t] = topics.get(t, 0) + 1
    
    return {
        'exam_info': {
            'code': 'GES-C01',
            'name': 'SnowPro Specialty: Generative AI',
            'provider': 'Snowflake',
            'passing_score': '750/1000',
            'duration': '115 minutes',
            'fee': '$375 USD',
            'format': 'Multiple choice, Select all that apply',
            'domains': [
                'Snowflake Cortex AI',
                'Cortex LLM Functions',
                'Cortex Search',
                'Cortex Analyst',
                'Document AI',
                'Vector Embeddings & RAG',
                'Fine-tuning',
                'AI Observability & Governance'
            ]
        },
        'metadata': {
            'total_questions': len(questions),
            'topics': topics,
            'source': 'OCR extracted from practice exam screenshots',
            'note': 'Some OCR artifacts may remain. Verify against official materials.'
        },
        'questions': questions
    }

def main():
    print("="*60)
    print("GES-C01 Question Cleaner & Finalizer")
    print("="*60)
    
    # Load extracted questions
    print("\n1. Loading extracted questions...")
    data = load_json('GES-C01_Extracted_Questions.json')
    questions = data.get('questions', [])
    print(f"   Loaded {len(questions)} questions")
    
    # Clean and dedupe
    print("\n2. Cleaning OCR artifacts...")
    cleaned = dedupe_and_clean(questions)
    print(f"   After deduplication: {len(cleaned)} questions")
    
    # Validate answers
    print("\n3. Validating answer formats...")
    validated = validate_answers(cleaned)
    print(f"   Valid questions: {len(validated)}")
    
    # Create final output
    print("\n4. Creating final output...")
    final = create_final_output(validated)
    
    # Save
    output_file = 'GES-C01_Exam_Questions_Clean.json'
    save_json(final, output_file)
    print(f"\n5. Saved to: {output_file}")
    
    # Summary
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    print(f"Total questions: {final['metadata']['total_questions']}")
    print("\nQuestions by Topic:")
    for topic, count in sorted(final['metadata']['topics'].items(), key=lambda x: -x[1]):
        print(f"  - {topic}: {count}")
    
    # Sample questions
    print("\n" + "="*60)
    print("SAMPLE CLEANED QUESTIONS")
    print("="*60)
    for q in final['questions'][:3]:
        print(f"\n[Q{q['id']}] Topic: {q['topic']}")
        print(f"Question: {q['question'][:200]}...")
        print(f"Answer: {q['correct_answer']}")
        if q['explanation']:
            print(f"Explanation: {q['explanation'][:100]}...")

if __name__ == '__main__':
    main()
