"""
Parse extracted OCR text into structured questions and answers.
"""
import json
import re
from typing import List, Dict, Optional

def load_extracted_text(filepath: str) -> List[Dict]:
    """Load the extracted text from JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def clean_text(text: str) -> str:
    """Clean OCR artifacts from text."""
    # Replace common OCR errors
    replacements = {
        'ot ': 'of ',
        ' ot': ' of',
        'tor ': 'for ',
        ' tor': ' for',
        'trom ': 'from ',
        ' trom': ' from',
        'it ': 'if ',
        ' lt ': ' it ',
        'NIJLC': 'NULL',
        'NULC': 'NULL',
        'æython': 'Python',
        'tine-': 'fine-',
        'tine ': 'fine ',
        'GBImo': 'GB/mo',
        'GBImonth': 'GB/month',
        'tile': 'file',
        'tiles': 'files',
        'Llst': 'List',
        'tunction': 'function',
        'detault': 'default',
        'specitic': 'specific',
        'difterent': 'different',
        'contidence': 'confidence',
        'intormation': 'information',
        'contorm': 'conform',
        'perlormed': 'performed',
        'benetit': 'benefit',
        'benetits': 'benefits',
        'ettective': 'effective',
        'etticiently': 'efficiently',
        'etticiency': 'efficiency',
        'atter': 'after',
        'betre': 'before',
        'detine': 'define',
        'detines': 'defines',
        'detinition': 'definition',
        'specilic': 'specific',
        'ditterent': 'different',
        'lunctional': 'functional',
        'lunction': 'function',
        'lunctions': 'functions',
        'Iunctions': 'functions',
        'signiticant': 'significant',
        'signiticantly': 'significantly',
        'intluence': 'influence',
        'intluences': 'influences',
        'contlict': 'conflict',
        'contlicts': 'conflicts',
        'contirm': 'confirm',
        'contirmed': 'confirmed',
        'perlorming': 'performing',
        'perlormed': 'performed',
        'perlorming': 'performing',
        'peformance': 'performance',
        'perormance': 'performance',
        'inlormation': 'information',
        'inlluence': 'influence',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_question_number(text: str) -> Optional[int]:
    """Extract question number from text."""
    # Look for patterns like "1.", "1 -", "1-", "Question 1"
    patterns = [
        r'^(\d+)\s*[\-\.]\s*[A-Z]',  # "1. A", "1 -A", "1-A"
        r'^(\d+)\s*[\-\.]\s*',       # "1.", "1 -"
        r'Question\s*(\d+)',          # "Question 1"
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
    return None

def parse_single_entry(entry: Dict) -> Dict:
    """Parse a single OCR entry into structured format."""
    text = entry.get('text', '')
    image = entry.get('image', '')
    
    result = {
        'source_image': image,
        'raw_text': text,
        'questions': []
    }
    
    # Clean the text
    cleaned_text = clean_text(text)
    
    # Extract question numbers and answers
    # Look for question patterns
    question_pattern = r'(\d+)\s*[\-\.]\s*([A-Z][^A-E]*?)(?=\s*A[\.\)]\s|$)'
    answer_pattern = r'Answer:\s*([A-E](?:,[A-E])*)'
    explanation_pattern = r'Explanation:\s*(.*?)(?=\d+\s*[\-\.]|$)'
    
    # Find answers in the text
    answers = re.findall(answer_pattern, cleaned_text)
    explanations = re.findall(explanation_pattern, cleaned_text, re.DOTALL)
    
    result['answers_found'] = answers
    result['has_explanation'] = len(explanations) > 0
    result['cleaned_text'] = cleaned_text
    
    return result

def combine_and_parse_all(entries: List[Dict]) -> List[Dict]:
    """Combine all entries and parse into questions."""
    # First, combine all text to understand the full context
    all_text = "\n\n".join([clean_text(e['text']) for e in entries])
    
    questions = []
    current_question = None
    
    # Split by question numbers
    # Pattern to find question starts: "1.", "2-", etc. followed by question text
    question_splits = re.split(r'(\d+)\s*[\-\.]\s*(?=[A-Z])', all_text)
    
    i = 1
    while i < len(question_splits) - 1:
        q_num = question_splits[i]
        q_content = question_splits[i + 1]
        
        if q_num.isdigit():
            q_num_int = int(q_num)
            
            # Extract the question and answer info
            # Find the answer pattern
            answer_match = re.search(r'Answer:\s*([A-E](?:,[A-E])*)', q_content)
            explanation_match = re.search(r'Explanation:\s*(.*?)(?=\d+\s*[\-\.]|Option [A-E]|$)', q_content, re.DOTALL)
            
            # Extract options A, B, C, D, E
            options_pattern = r'([A-E])[\.\)]\s*([^A-E\n]+?)(?=[A-E][\.\)]|\s*Answer:|$)'
            options = re.findall(options_pattern, q_content)
            
            # Get question text (before options)
            question_text_match = re.search(r'^(.*?)(?=[A-E][\.\)]|A\.\s)', q_content, re.DOTALL)
            question_text = question_text_match.group(1).strip() if question_text_match else ""
            
            question = {
                'number': q_num_int,
                'question': question_text[:500] if question_text else "",  # Limit length
                'options': dict(options) if options else {},
                'answer': answer_match.group(1) if answer_match else "",
                'explanation': explanation_match.group(1).strip()[:1000] if explanation_match else ""
            }
            
            if question['answer']:  # Only add if we found an answer
                questions.append(question)
        
        i += 2
    
    return questions

def parse_structured_questions(entries: List[Dict]) -> List[Dict]:
    """Parse entries into structured questions with better logic."""
    questions = []
    seen_numbers = set()
    
    for entry in entries:
        text = clean_text(entry['text'])
        source = entry['image']
        
        # Find question number at the start
        q_num_match = re.match(r'^.*?(\d+)\s*[\-\.]\s*([A-Z])', text)
        
        # Find answer
        answer_match = re.search(r'Answer:\s*([A-E](?:,[A-E])*)', text)
        
        # Find explanation
        explanation_match = re.search(r'Explanation:\s*(.*?)(?=\d+\s*[\-\.]|$)', text, re.DOTALL)
        
        # Extract the question portion (first significant text block before options)
        # Look for text between question number and first option (A., B., etc.)
        q_text_match = re.search(r'^\s*\d+\s*[\-\.]?\s*(.+?)(?=\s*[A-E][\.\)]\s*[A-Z]|A\.\s*Option|$)', text, re.DOTALL)
        
        if answer_match:
            q_num = None
            if q_num_match:
                q_num = int(q_num_match.group(1))
            
            # Try to extract question text
            question_text = ""
            if q_text_match:
                question_text = q_text_match.group(1).strip()
                # Clean up the question text
                question_text = re.sub(r'\s+', ' ', question_text)
            
            question = {
                'number': q_num,
                'source_image': source,
                'question': question_text[:800],
                'answer': answer_match.group(1),
                'explanation': explanation_match.group(1).strip()[:1500] if explanation_match else "",
                'raw_snippet': text[:200]
            }
            
            # Dedupe by question number if we have one
            if q_num and q_num not in seen_numbers:
                seen_numbers.add(q_num)
                questions.append(question)
            elif not q_num:
                questions.append(question)
    
    return questions

def main():
    input_file = 'extracted_text.json'
    output_file = 'parsed_questions.json'
    
    print("Loading extracted text...")
    entries = load_extracted_text(input_file)
    print(f"Loaded {len(entries)} entries")
    
    print("\nParsing structured questions...")
    questions = parse_structured_questions(entries)
    print(f"Found {len(questions)} questions with answers")
    
    # Sort by question number
    questions_with_num = [q for q in questions if q.get('number')]
    questions_without_num = [q for q in questions if not q.get('number')]
    questions_with_num.sort(key=lambda x: x['number'])
    all_questions = questions_with_num + questions_without_num
    
    # Create final output
    output = {
        "exam": "GES-C01 SnowPro Specialty: Generative AI",
        "total_questions": len(all_questions),
        "source": "OCR extracted from TestAssesments images",
        "questions": all_questions
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved parsed questions to: {output_file}")
    
    # Print summary
    print("\n=== Summary ===")
    print(f"Total questions parsed: {len(all_questions)}")
    print(f"Questions with numbers: {len(questions_with_num)}")
    
    # Show first few questions
    print("\n=== Sample Questions ===")
    for q in all_questions[:3]:
        print(f"\nQ{q.get('number', '?')}: {q['question'][:100]}...")
        print(f"Answer: {q['answer']}")

if __name__ == '__main__':
    main()
