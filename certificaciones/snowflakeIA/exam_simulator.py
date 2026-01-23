import json
import random
import time
from datetime import datetime

def load_questions(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['questions']

def run_exam(questions, num_questions=65, time_limit_minutes=115):
    """Run a simulated GES-C01 exam"""
    
    print("\n" + "="*70)
    print("     SNOWFLAKE SNOWPRO GEN AI (GES-C01) CERTIFICATION EXAM")
    print("="*70)
    print(f"\n📋 Questions: {num_questions}")
    print(f"⏱️  Time Limit: {time_limit_minutes} minutes")
    print(f"✅ Passing Score: 75%")
    print("\n" + "-"*70)
    print("Instructions:")
    print("- Enter your answer(s) as letters (e.g., 'A' or 'A,C,D' for multi-select)")
    print("- Type 'skip' to skip a question")
    print("- Type 'quit' to end the exam early")
    print("- Type 'time' to check remaining time")
    print("-"*70)
    
    input("\nPress ENTER to start the exam...")
    
    # Select random questions
    exam_questions = random.sample(questions, min(num_questions, len(questions)))
    
    start_time = time.time()
    end_time = start_time + (time_limit_minutes * 60)
    
    score = 0
    answered = 0
    skipped = 0
    results = []
    
    for i, q in enumerate(exam_questions, 1):
        # Check time
        remaining = end_time - time.time()
        if remaining <= 0:
            print("\n⏰ TIME'S UP!")
            break
        
        remaining_mins = int(remaining // 60)
        remaining_secs = int(remaining % 60)
        
        print(f"\n{'='*70}")
        print(f"Question {i}/{num_questions}  |  Time: {remaining_mins}:{remaining_secs:02d}  |  Score: {score}/{answered}")
        print(f"Category: {q.get('category', 'General')}  |  Difficulty: {q.get('difficulty', 'Medium')}")
        print("="*70)
        
        # Show question
        print(f"\n{q['question']}")
        
        if q.get('multiSelect'):
            print("\n(Select ALL that apply)")
        
        # Show options
        print()
        for letter, text in sorted(q['options'].items()):
            print(f"  {letter}. {text}")
        
        # Get answer
        print()
        while True:
            user_input = input("Your answer: ").strip().upper()
            
            if user_input == 'QUIT':
                print("\nExam ended early.")
                break
            elif user_input == 'SKIP':
                skipped += 1
                results.append({'question': i, 'correct': False, 'skipped': True})
                break
            elif user_input == 'TIME':
                remaining = end_time - time.time()
                print(f"⏱️  Remaining: {int(remaining//60)}:{int(remaining%60):02d}")
                continue
            elif user_input:
                # Parse answer
                user_answers = set(a.strip() for a in user_input.replace(' ', '').split(','))
                
                # Get correct answer
                correct = q['correctAnswer']
                if isinstance(correct, list):
                    correct_set = set(correct)
                else:
                    correct_set = {correct}
                
                # Check if correct
                is_correct = user_answers == correct_set
                answered += 1
                
                if is_correct:
                    score += 1
                    print("✅ Correct!")
                else:
                    print(f"❌ Incorrect. Correct answer: {', '.join(sorted(correct_set))}")
                
                # Show explanation
                if q.get('explanation'):
                    print(f"\n📖 Explanation: {q['explanation']}")
                
                results.append({
                    'question': i,
                    'correct': is_correct,
                    'user_answer': user_input,
                    'correct_answer': ', '.join(sorted(correct_set)),
                    'category': q.get('category', 'General')
                })
                break
        
        if user_input == 'QUIT':
            break
        
        input("\nPress ENTER for next question...")
    
    # Calculate final results
    total_time = time.time() - start_time
    total_answered = answered + skipped
    percentage = (score / total_answered * 100) if total_answered > 0 else 0
    passed = percentage >= 75
    
    print("\n" + "="*70)
    print("                         EXAM RESULTS")
    print("="*70)
    print(f"\n📊 Final Score: {score}/{total_answered} ({percentage:.1f}%)")
    print(f"⏱️  Time Used: {int(total_time//60)} minutes {int(total_time%60)} seconds")
    print(f"📝 Questions Answered: {answered}")
    print(f"⏭️  Questions Skipped: {skipped}")
    
    if passed:
        print(f"\n🎉 CONGRATULATIONS! You PASSED! 🎉")
    else:
        print(f"\n📚 You did not pass. Keep studying! Required: 75%")
    
    # Category breakdown
    print("\n" + "-"*70)
    print("Performance by Category:")
    print("-"*70)
    
    category_stats = {}
    for r in results:
        if not r.get('skipped'):
            cat = r.get('category', 'General')
            if cat not in category_stats:
                category_stats[cat] = {'correct': 0, 'total': 0}
            category_stats[cat]['total'] += 1
            if r['correct']:
                category_stats[cat]['correct'] += 1
    
    for cat, stats in sorted(category_stats.items()):
        pct = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
        bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        print(f"  {cat:25} {bar} {stats['correct']}/{stats['total']} ({pct:.0f}%)")
    
    print("\n" + "="*70)
    return percentage >= 75

def main():
    print("\n🎓 GES-C01 Exam Simulator")
    print("-"*40)
    
    questions = load_questions('GES-C01_Exam_Sample_Questions.json')
    print(f"Loaded {len(questions)} questions")
    
    print("\nSelect exam mode:")
    print(f"1. ALL Questions ({len(questions)} questions, 200 minutes)")
    print("2. Real Exam Simulation (65 questions, 115 minutes)")
    print("3. Quick Practice (20 questions, 30 minutes)")
    print("4. Category Focus (10 questions from one category)")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == '1':
        run_exam(questions, len(questions), 200)
    elif choice == '2':
        run_exam(questions, 65, 115)
    elif choice == '3':
        run_exam(questions, 20, 30)
    elif choice == '4':
        # Show categories
        categories = list(set(q.get('category', 'General') for q in questions))
        print("\nAvailable categories:")
        for i, cat in enumerate(sorted(categories), 1):
            count = sum(1 for q in questions if q.get('category') == cat)
            print(f"  {i}. {cat} ({count} questions)")
        
        cat_choice = input("\nEnter category number: ").strip()
        try:
            selected_cat = sorted(categories)[int(cat_choice) - 1]
            cat_questions = [q for q in questions if q.get('category') == selected_cat]
            run_exam(cat_questions, len(cat_questions), 60)
        except:
            print("Invalid choice")
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()
