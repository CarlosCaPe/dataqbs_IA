"""
GES-C01 Exam Simulator - Practice Environment
==============================================

Este módulo crea un ambiente de emulación de examen idéntico al real.

Características del examen GES-C01 real:
- 65 preguntas
- 115 minutos
- 750/1000 para aprobar (~75%)
- Single Select y Multiple Select
- $375 USD

Este simulador:
1. Selecciona preguntas aleatorias respetando la distribución de dominios
2. Implementa el mismo formato de respuesta
3. Trackea tiempo por pregunta
4. Genera reportes de rendimiento por tema
"""

import json
import random
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class ExamMode(Enum):
    """Modos de examen disponibles"""
    PRACTICE = "practice"           # Sin límite de tiempo, muestra respuestas
    TIMED_PRACTICE = "timed_practice"  # Con tiempo, muestra respuestas al final
    EXAM_SIMULATION = "exam_simulation"  # Condiciones reales del examen


@dataclass
class ExamConfig:
    """Configuración del examen"""
    total_questions: int = 65
    time_limit_minutes: int = 115
    passing_score: float = 0.75
    
    # Distribución de dominios según el examen real
    domain_weights: Dict[str, Tuple[float, float]] = None
    
    def __post_init__(self):
        if self.domain_weights is None:
            self.domain_weights = {
                "Cortex LLM Functions": (0.15, 0.20),      # 15-20%
                "Cortex Search": (0.15, 0.20),             # 15-20%
                "Document AI": (0.15, 0.20),               # 15-20%
                "Cortex Analyst": (0.10, 0.15),            # 10-15%
                "Vector Embeddings": (0.10, 0.15),         # 10-15%
                "Fine-tuning": (0.10, 0.15),               # 10-15%
                "RAG": (0.10, 0.15),                       # 10-15%
                "General Cortex AI": (0.10, 0.15),         # Cortex AI Foundations
                "Snowpark Container Services": (0.05, 0.10),  # Part of custom models
                "Cost & Governance": (0.05, 0.10),         # AI Observability & Governance
            }


@dataclass
class QuestionResult:
    """Resultado de una pregunta individual"""
    question_id: int
    topic: str
    is_correct: bool
    user_answer: str
    correct_answer: str
    time_spent_seconds: float
    is_multiple_select: bool


@dataclass
class ExamResult:
    """Resultado completo del examen"""
    exam_id: str
    mode: str
    start_time: str
    end_time: str
    total_time_minutes: float
    questions_answered: int
    correct_answers: int
    score_percentage: float
    passed: bool
    results_by_topic: Dict[str, Dict]
    question_results: List[Dict]


class ExamSimulator:
    """Simulador de examen GES-C01"""
    
    def __init__(self, questions_path: str, config: ExamConfig = None):
        """Inicializa el simulador con el banco de preguntas"""
        self.questions_path = Path(questions_path)
        self.config = config or ExamConfig()
        
        with open(self.questions_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.all_questions = data.get('questions', [])
        self.exam_info = data.get('examInfo', {})
        self.study_guide = data.get('studyGuide', {})
        
        # Agrupar preguntas por tema
        self.questions_by_topic = {}
        for q in self.all_questions:
            topic = q.get('topic', 'Unknown')
            if topic not in self.questions_by_topic:
                self.questions_by_topic[topic] = []
            self.questions_by_topic[topic].append(q)
    
    def get_question_bank_stats(self) -> Dict:
        """Obtiene estadísticas del banco de preguntas"""
        stats = {
            "total_questions": len(self.all_questions),
            "by_topic": {},
            "by_type": {"single_select": 0, "multiple_select": 0},
            "coverage_vs_exam": {}
        }
        
        for topic, questions in self.questions_by_topic.items():
            stats["by_topic"][topic] = len(questions)
            for q in questions:
                if q.get('multipleSelect', False):
                    stats["by_type"]["multiple_select"] += 1
                else:
                    stats["by_type"]["single_select"] += 1
        
        # Calcular cobertura vs examen real
        for topic, weight_range in self.config.domain_weights.items():
            min_weight, max_weight = weight_range
            target_questions = int(self.config.total_questions * (min_weight + max_weight) / 2)
            actual_questions = stats["by_topic"].get(topic, 0)
            stats["coverage_vs_exam"][topic] = {
                "target": target_questions,
                "actual": actual_questions,
                "coverage_pct": round(actual_questions / target_questions * 100, 1) if target_questions > 0 else 0
            }
        
        return stats
    
    def select_exam_questions(self, num_questions: int = None) -> List[Dict]:
        """
        Selecciona preguntas para el examen respetando la distribución de dominios
        """
        if num_questions is None:
            num_questions = self.config.total_questions
        
        selected = []
        remaining = num_questions
        
        # Calcular preguntas por tema basándose en pesos
        questions_per_topic = {}
        for topic, weight_range in self.config.domain_weights.items():
            min_weight, max_weight = weight_range
            avg_weight = (min_weight + max_weight) / 2
            target = int(num_questions * avg_weight)
            available = len(self.questions_by_topic.get(topic, []))
            questions_per_topic[topic] = min(target, available)
        
        # Seleccionar preguntas por tema
        for topic, count in questions_per_topic.items():
            if topic in self.questions_by_topic and count > 0:
                available = self.questions_by_topic[topic]
                chosen = random.sample(available, min(count, len(available)))
                selected.extend(chosen)
                remaining -= len(chosen)
        
        # Rellenar con preguntas aleatorias si faltan
        if remaining > 0:
            all_ids = {q['id'] for q in selected}
            available = [q for q in self.all_questions if q['id'] not in all_ids]
            if available:
                extra = random.sample(available, min(remaining, len(available)))
                selected.extend(extra)
        
        # Mezclar el orden
        random.shuffle(selected)
        
        return selected
    
    def format_question_for_display(self, question: Dict, question_num: int) -> str:
        """Formatea una pregunta para mostrar en consola"""
        output = []
        output.append(f"\n{'='*70}")
        output.append(f"Question {question_num} of {self.config.total_questions}")
        output.append(f"Topic: {question.get('topic', 'Unknown')}")
        
        if question.get('multipleSelect', False):
            output.append("(SELECT ALL THAT APPLY)")
        else:
            output.append("(SELECT ONE)")
        
        output.append(f"{'='*70}")
        output.append(f"\n{question.get('question', '')}\n")
        
        # Si tiene opciones estructuradas
        if 'options' in question:
            for letter, text in sorted(question['options'].items()):
                output.append(f"  {letter}. {text}")
        
        return "\n".join(output)
    
    def evaluate_answer(self, question: Dict, user_answer: str) -> bool:
        """Evalúa si la respuesta del usuario es correcta"""
        correct = question.get('correctAnswer', '').upper().replace(' ', '')
        user = user_answer.upper().replace(' ', '')
        
        # Normalizar respuestas múltiples
        if ',' in correct:
            correct_set = set(correct.split(','))
            user_set = set(user.split(','))
            return correct_set == user_set
        
        return correct == user
    
    def run_practice_session(self, num_questions: int = 10) -> ExamResult:
        """
        Ejecuta una sesión de práctica interactiva
        """
        questions = self.select_exam_questions(min(num_questions, len(self.all_questions)))
        results = []
        
        exam_id = f"practice_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()
        
        print("\n" + "="*70)
        print("GES-C01 PRACTICE SESSION")
        print(f"Questions: {len(questions)}")
        print("Mode: Practice (answers shown after each question)")
        print("="*70)
        
        for i, question in enumerate(questions, 1):
            print(self.format_question_for_display(question, i))
            
            q_start = time.time()
            
            # En modo interactivo, pediríamos input
            # Para demo, usamos la respuesta correcta
            user_answer = question.get('correctAnswer', 'A')
            
            q_time = time.time() - q_start
            is_correct = self.evaluate_answer(question, user_answer)
            
            result = QuestionResult(
                question_id=question.get('id', 0),
                topic=question.get('topic', 'Unknown'),
                is_correct=is_correct,
                user_answer=user_answer,
                correct_answer=question.get('correctAnswer', ''),
                time_spent_seconds=q_time,
                is_multiple_select=question.get('multipleSelect', False)
            )
            results.append(result)
            
            # Mostrar feedback
            print(f"\n✅ Correct answer: {question.get('correctAnswer', '')}")
            print(f"📖 Explanation: {question.get('explanation', '')[:200]}...")
        
        end_time = datetime.now()
        
        # Calcular estadísticas
        correct_count = sum(1 for r in results if r.is_correct)
        score_pct = correct_count / len(results) * 100 if results else 0
        
        # Resultados por tema
        topic_results = {}
        for r in results:
            if r.topic not in topic_results:
                topic_results[r.topic] = {"correct": 0, "total": 0}
            topic_results[r.topic]["total"] += 1
            if r.is_correct:
                topic_results[r.topic]["correct"] += 1
        
        for topic in topic_results:
            topic_results[topic]["percentage"] = round(
                topic_results[topic]["correct"] / topic_results[topic]["total"] * 100, 1
            )
        
        exam_result = ExamResult(
            exam_id=exam_id,
            mode="practice",
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            total_time_minutes=round((end_time - start_time).total_seconds() / 60, 2),
            questions_answered=len(results),
            correct_answers=correct_count,
            score_percentage=round(score_pct, 1),
            passed=score_pct >= self.config.passing_score * 100,
            results_by_topic=topic_results,
            question_results=[asdict(r) for r in results]
        )
        
        return exam_result
    
    def generate_score_report(self, result: ExamResult) -> str:
        """Genera un reporte detallado del examen"""
        report = []
        report.append("\n" + "="*70)
        report.append("EXAM RESULTS - GES-C01 SnowPro Specialty: Generative AI")
        report.append("="*70)
        
        report.append(f"\n📊 OVERALL SCORE: {result.score_percentage}%")
        report.append(f"   Correct: {result.correct_answers}/{result.questions_answered}")
        report.append(f"   Passing Score: {self.config.passing_score * 100}%")
        
        if result.passed:
            report.append("   ✅ PASSED")
        else:
            report.append("   ❌ NOT PASSED")
        
        report.append(f"\n⏱️ Time: {result.total_time_minutes} minutes")
        
        report.append("\n📈 PERFORMANCE BY DOMAIN:")
        for topic, stats in sorted(result.results_by_topic.items(), 
                                   key=lambda x: x[1].get('percentage', 0)):
            bar = '█' * int(stats['percentage'] / 10)
            empty = '░' * (10 - len(bar))
            status = '✅' if stats['percentage'] >= 75 else '⚠️' if stats['percentage'] >= 50 else '❌'
            report.append(f"   {status} {topic:30} {stats['percentage']:5.1f}% {bar}{empty} ({stats['correct']}/{stats['total']})")
        
        # Recomendaciones de estudio
        weak_topics = [t for t, s in result.results_by_topic.items() if s['percentage'] < 75]
        if weak_topics:
            report.append("\n📚 STUDY RECOMMENDATIONS:")
            for topic in weak_topics:
                report.append(f"   • Review: {topic}")
                if topic in self.study_guide:
                    report.append(f"     Key points: {', '.join(self.study_guide[topic][:2])}")
        
        report.append("\n" + "="*70)
        
        return "\n".join(report)
    
    def export_simulator_config(self, output_path: str) -> str:
        """
        Exporta la configuración del simulador para uso en otras plataformas
        (ej: Streamlit, Web apps, LMS)
        """
        config = {
            "examInfo": self.exam_info,
            "simulatorConfig": {
                "totalQuestions": self.config.total_questions,
                "timeLimitMinutes": self.config.time_limit_minutes,
                "passingScore": self.config.passing_score,
                "domainWeights": {k: list(v) for k, v in self.config.domain_weights.items()}
            },
            "questionBankStats": self.get_question_bank_stats(),
            "studyGuide": self.study_guide,
            "exportDate": datetime.now().isoformat()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return output_path


def main():
    """Demo del simulador de examen"""
    
    base_path = Path(__file__).parent.parent
    json_path = base_path / 'GES-C01_Exam_Sample_Questions.json'
    
    if not json_path.exists():
        json_path = base_path.parent / 'GES-C01_Exam_Sample_Questions.json'
    
    print("="*70)
    print("GES-C01 EXAM SIMULATOR - Initialization")
    print("="*70)
    
    simulator = ExamSimulator(str(json_path))
    stats = simulator.get_question_bank_stats()
    
    print(f"\n📚 Question Bank Loaded: {stats['total_questions']} questions")
    print(f"   Single Select: {stats['by_type']['single_select']}")
    print(f"   Multiple Select: {stats['by_type']['multiple_select']}")
    
    print(f"\n📊 Topic Coverage vs Real Exam (65 questions):")
    for topic, coverage in sorted(stats['coverage_vs_exam'].items(), key=lambda x: -x[1]['actual']):
        bar = '█' * min(int(coverage['coverage_pct'] / 10), 10)
        status = '✅' if coverage['coverage_pct'] >= 100 else '⚠️'
        print(f"   {status} {topic:30} {coverage['actual']:2}/{coverage['target']:2} ({coverage['coverage_pct']:5.1f}%)")
    
    # Exportar configuración del simulador
    output_path = base_path / 'TestAssesments' / 'data' / 'json' / 'exam_simulator_config.json'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    simulator.export_simulator_config(str(output_path))
    print(f"\n✅ Simulator config exported to: {output_path}")
    
    # Demo de selección de preguntas
    print(f"\n🎯 Sample Exam Selection (10 questions demo):")
    sample_questions = simulator.select_exam_questions(10)
    topics_selected = {}
    for q in sample_questions:
        t = q.get('topic', 'Unknown')
        topics_selected[t] = topics_selected.get(t, 0) + 1
    
    for topic, count in sorted(topics_selected.items()):
        print(f"   {topic}: {count}")
    
    print("\n" + "="*70)
    print("Simulator ready for integration with Streamlit or web apps!")
    print("="*70)


if __name__ == '__main__':
    main()
