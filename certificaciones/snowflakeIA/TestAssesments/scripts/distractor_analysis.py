"""
Automatic Item Generation (AIG) - Distractor Analysis for GES-C01
=====================================================================

Este script implementa las mejores prácticas de Educational Assessment Design:

1. DISTRACTOR ANALYSIS
   - Analiza opciones incorrectas para identificar conocimientos no testeados
   - Los "distractores" (opciones incorrectas) contienen información válida que puede convertirse en nuevas preguntas

2. KNOWLEDGE GAP ANALYSIS  
   - Identifica lagunas de conocimiento basándose en los conceptos en las respuestas incorrectas
   - Usa Official Snowflake Documentation como fuente de verdad

3. AUTOMATIC ITEM GENERATION (AIG)
   - Técnica de Educational Testing para generar nuevas preguntas programáticamente
   - Similar a Data Augmentation en ML pero para assessment items

4. BLOOM'S TAXONOMY COVERAGE
   - Asegura cobertura de diferentes niveles cognitivos:
     * Remember, Understand, Apply, Analyze, Evaluate, Create

Referencias:
- Gierl, M. J., & Haladyna, T. M. (2013). Automatic Item Generation: Theory and Practice
- Snowflake Official Documentation: docs.snowflake.com
"""

import json
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Set


class DistractorAnalyzer:
    """Analiza distractores para generar nuevas preguntas basadas en conocimiento no testeado"""
    
    # Conocimiento clave extraído de documentación oficial de Snowflake
    VERIFIED_KNOWLEDGE_BASE = {
        "warehouse_sizes": {
            "fact": "Snowflake recommends MEDIUM or smaller warehouses for Cortex AI functions",
            "source": "docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions",
            "distractor_concepts": [
                "LARGE warehouses do NOT improve LLM performance",
                "XL and 2XL warehouses waste compute credits for Cortex",
                "LLM inference runs on Snowflake-managed compute, not user warehouse"
            ]
        },
        "vector_dimensions": {
            "fact": "VECTOR data type supports up to 4096 dimensions",
            "source": "docs.snowflake.com/en/sql-reference/data-types-vector",
            "distractor_concepts": [
                "768 dimensions is NOT the maximum (common misconception)",
                "1024 dimensions for snowflake-arctic-embed models",
                "VECTOR not supported in VARIANT columns",
                "VECTOR not supported as primary/clustering keys"
            ]
        },
        "cortex_search_chunking": {
            "fact": "Text should be chunked to 512 tokens or less for optimal Cortex Search results",
            "source": "docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/cortex-search-overview",
            "distractor_concepts": [
                "Larger chunks reduce retrieval quality",
                "8000 token context window models still benefit from 512 token chunks",
                "Hybrid search uses both vector AND keyword matching"
            ]
        },
        "document_ai_requirements": {
            "fact": "Document AI requires SNOWFLAKE_SSE encryption on internal stages",
            "source": "docs.snowflake.com/en/user-guide/snowflake-cortex/document-ai/overview",
            "distractor_concepts": [
                "Maximum 125 pages per document",
                "Maximum 50 MB per document",
                "Maximum 1000 documents per query",
                "Supported formats: PDF, PNG, DOCX, XML, JPEG, HTML, TXT, TIFF"
            ]
        },
        "temperature_setting": {
            "fact": "temperature=0 recommended for deterministic and consistent LLM outputs",
            "source": "docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions",
            "distractor_concepts": [
                "Higher temperature increases randomness (undesirable for extraction)",
                "temperature=1.0 does NOT reduce errors or tokens"
            ]
        },
        "cortex_guard": {
            "fact": "Cortex Guard filters unsafe/harmful responses but does NOT anonymize PII",
            "source": "docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions",
            "distractor_concepts": [
                "guard_tokens field shows tokens consumed by guardrail",
                "PII anonymization requires separate preprocessing"
            ]
        },
        "try_complete": {
            "fact": "TRY_COMPLETE returns NULL on failure instead of raising an error",
            "source": "docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions",
            "distractor_concepts": [
                "Critical for robust data pipelines",
                "Does NOT return structured error objects"
            ]
        },
        "cross_region_inference": {
            "fact": "CORTEX_ENABLED_CROSS_REGION enables inference in other regions when model not available locally",
            "source": "docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions",
            "distractor_concepts": [
                "Does NOT bypass CORTEX_MODELS_ALLOWLIST",
                "May increase latency for cross-region calls"
            ]
        },
        "embedding_models": {
            "fact": "snowflake-arctic-embed-m-v1.5 costs 0.03 credits/million tokens vs voyage-multilingual-2 at 0.07",
            "source": "docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions",
            "distractor_concepts": [
                "Model selection impacts token costs",
                "Arctic models optimized for English",
                "Voyage models support multilingual"
            ]
        },
        "fine_tuning": {
            "fact": "Fine-tuned models are exclusive to your account and not shared",
            "source": "docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-finetuning",
            "distractor_concepts": [
                "Supported: llama3-8b, llama3.1-8b, llama3.1-70b, mistral-7b",
                "Training data stays within your account",
                "Customer data never used to train shared models"
            ]
        },
        "structured_outputs": {
            "fact": "response_format argument enforces JSON schema in AI_COMPLETE outputs",
            "source": "docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions",
            "distractor_concepts": [
                "required array ensures fields are extracted or error raised",
                "additionalProperties: false for strict schema (OpenAI models)",
                "Adding 'Respond in JSON' to prompt improves accuracy"
            ]
        },
        "cortex_search_costs": {
            "fact": "Cortex Search costs: warehouse compute + 6.3 credits/GB/month indexed data + token costs",
            "source": "docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/cortex-search-overview",
            "distractor_concepts": [
                "Volume of indexed data has SIGNIFICANT impact (not minimal)",
                "Cloud services subject to 10% daily adjustment"
            ]
        },
        "dynamic_tables": {
            "fact": "Snowflake Cortex functions do NOT support dynamic tables",
            "source": "docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions",
            "distractor_concepts": [
                "Use streams and tasks for continuous processing instead",
                "Scheduled tasks can call Cortex functions"
            ]
        }
    }
    
    def __init__(self, json_path: str):
        """Inicializa el analizador con el JSON de preguntas existentes"""
        self.json_path = Path(json_path)
        with open(self.json_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        self.questions = self.data.get('questions', [])
        self.topics_covered = self._analyze_topic_coverage()
        self.concepts_tested = self._extract_tested_concepts()
        
    def _analyze_topic_coverage(self) -> Dict[str, int]:
        """Analiza cuántas preguntas hay por tema"""
        topic_counts = defaultdict(int)
        for q in self.questions:
            topic = q.get('topic', 'Unknown')
            topic_counts[topic] += 1
        return dict(topic_counts)
    
    def _extract_tested_concepts(self) -> Set[str]:
        """Extrae conceptos clave ya testeados en las preguntas existentes"""
        concepts = set()
        for q in self.questions:
            # Extraer conceptos del texto de la pregunta y explicación
            text = q.get('question', '') + ' ' + q.get('explanation', '')
            text = text.lower()
            
            # Buscar conceptos clave
            key_patterns = [
                r'vector\s*\(\s*\w+\s*,\s*\d+\s*\)',  # VECTOR(FLOAT, 768)
                r'medium\s+warehouse',
                r'512\s+tokens?',
                r'snowflake[_-]sse',
                r'temperature\s*[=:]\s*0',
                r'try[_]?complete',
                r'response[_]?format',
                r'cortex[_]?guard',
                r'fine[_-]?tun',
                r'arctic[_-]embed',
                r'125\s+pages?',
                r'50\s+mb',
                r'4096\s+dimensions?',
            ]
            
            for pattern in key_patterns:
                if re.search(pattern, text):
                    concepts.add(pattern)
                    
        return concepts
    
    def analyze_distractors(self) -> Dict[str, List[Dict]]:
        """
        Analiza cada pregunta para identificar conocimiento en los distractores
        que podría convertirse en nuevas preguntas
        """
        potential_new_questions = []
        analyzed_count = 0
        
        for q in self.questions:
            explanation = q.get('explanation', '')
            correct_answer = q.get('correctAnswer', '')
            question_text = q.get('question', '')
            
            # Buscar patrones de "Option X is incorrect because..."
            incorrect_patterns = re.findall(
                r'Option\s+([A-E])\s+is\s+(?:incorrect|wrong)\s+(?:because|as|since)[^.]+\.',
                explanation,
                re.IGNORECASE
            )
            
            for option_letter in incorrect_patterns:
                if option_letter.upper() not in correct_answer.upper():
                    # Este distractor contiene conocimiento testeable
                    analyzed_count += 1
                    
                    # Extraer el concepto del distractor
                    match = re.search(
                        rf'Option\s+{option_letter}\s+is\s+(?:incorrect|wrong)[^.]+\.', 
                        explanation,
                        re.IGNORECASE
                    )
                    if match:
                        distractor_reason = match.group(0)
                        potential_new_questions.append({
                            'source_question_id': q.get('id'),
                            'source_topic': q.get('topic'),
                            'distractor_option': option_letter.upper(),
                            'distractor_reason': distractor_reason,
                            'potential_new_question_topic': self._infer_topic_from_distractor(distractor_reason)
                        })
        
        return {
            'analyzed_questions': len(self.questions),
            'distractors_analyzed': analyzed_count,
            'potential_new_questions': potential_new_questions
        }
    
    def _infer_topic_from_distractor(self, distractor_text: str) -> str:
        """Infiere el tema basándose en el contenido del distractor"""
        text = distractor_text.lower()
        
        topic_keywords = {
            'Vector Embeddings': ['vector', 'embed', 'dimension', 'variant'],
            'Cortex Search': ['cortex search', 'chunk', 'token', 'hybrid'],
            'Document AI': ['document', 'stage', 'encryption', 'page', 'predict'],
            'Cortex LLM Functions': ['complete', 'temperature', 'token', 'llm', 'guard'],
            'Cortex Analyst': ['semantic model', 'analyst', 'sql generation'],
            'Fine-tuning': ['fine-tun', 'training', 'model'],
            'Cost & Governance': ['cost', 'credit', 'billing', 'allowlist']
        }
        
        for topic, keywords in topic_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return topic
        
        return 'General Cortex AI'
    
    def identify_knowledge_gaps(self) -> List[Dict]:
        """
        Identifica lagunas de conocimiento comparando el knowledge base
        con los conceptos ya testeados
        """
        gaps = []
        
        for concept_key, concept_data in self.VERIFIED_KNOWLEDGE_BASE.items():
            # Verificar si este concepto está bien cubierto
            fact = concept_data['fact'].lower()
            coverage_score = 0
            
            for q in self.questions:
                q_text = (q.get('question', '') + q.get('explanation', '')).lower()
                # Palabras clave del concepto
                keywords = re.findall(r'\b\w{4,}\b', fact)
                matches = sum(1 for kw in keywords if kw in q_text)
                if matches >= len(keywords) * 0.3:  # 30% coincidencia
                    coverage_score += 1
            
            # Si hay pocos matches, hay una laguna
            if coverage_score < 2:
                gaps.append({
                    'concept': concept_key,
                    'fact': concept_data['fact'],
                    'source': concept_data['source'],
                    'coverage_score': coverage_score,
                    'distractor_concepts': concept_data['distractor_concepts'],
                    'suggested_questions_count': len(concept_data['distractor_concepts'])
                })
        
        return gaps
    
    def plan_new_questions(self) -> Dict:
        """
        Planifica cuántas preguntas nuevas se generarían basándose en:
        1. Distractores analizados
        2. Lagunas de conocimiento
        3. Balance de temas
        """
        distractor_analysis = self.analyze_distractors()
        knowledge_gaps = self.identify_knowledge_gaps()
        
        # Calcular preguntas por fuente
        questions_from_gaps = sum(gap['suggested_questions_count'] for gap in knowledge_gaps)
        
        # Balance de temas - identificar temas sub-representados
        target_per_topic = 10  # Objetivo ideal por tema
        topic_deficit = {}
        for topic, count in self.topics_covered.items():
            if count < target_per_topic:
                topic_deficit[topic] = target_per_topic - count
        
        total_from_deficit = sum(topic_deficit.values())
        
        plan = {
            'current_questions': len(self.questions),
            'topic_coverage': self.topics_covered,
            'knowledge_gaps': knowledge_gaps,
            'topic_deficit': topic_deficit,
            'estimated_new_questions': {
                'from_knowledge_gaps': questions_from_gaps,
                'from_topic_balance': min(total_from_deficit, 15),  # Cap at 15
                'total_estimated': questions_from_gaps + min(total_from_deficit, 15)
            },
            'methodology': {
                'name': 'Automatic Item Generation (AIG)',
                'techniques': [
                    'Distractor Analysis - Convert incorrect options into new questions',
                    'Knowledge Gap Analysis - Test concepts from verified docs not yet covered',
                    'Item Isomorphs - Create variations testing same concept differently',
                    'Bloom\'s Taxonomy Coverage - Ensure multiple cognitive levels tested'
                ],
                'sources': [
                    'Official Snowflake Documentation (docs.snowflake.com)',
                    'Gierl & Haladyna (2013) - Automatic Item Generation Theory',
                    'Educational Testing Service (ETS) Best Practices'
                ]
            }
        }
        
        return plan


def main():
    """Ejecutar análisis de distractores y planificación de AIG"""
    
    # Buscar el JSON de preguntas
    base_path = Path(__file__).parent.parent
    json_path = base_path / 'GES-C01_Exam_Sample_Questions.json'
    
    if not json_path.exists():
        # Buscar en ubicación alternativa
        json_path = base_path.parent / 'GES-C01_Exam_Sample_Questions.json'
    
    print("=" * 70)
    print("AUTOMATIC ITEM GENERATION (AIG) - Distractor Analysis")
    print("=" * 70)
    
    analyzer = DistractorAnalyzer(str(json_path))
    plan = analyzer.plan_new_questions()
    
    print(f"\n📊 ANÁLISIS DEL BANCO DE PREGUNTAS ACTUAL")
    print(f"   Preguntas existentes: {plan['current_questions']}")
    print(f"\n📈 COBERTURA POR TEMA:")
    for topic, count in sorted(plan['topic_coverage'].items(), key=lambda x: -x[1]):
        bar = '█' * count
        print(f"   {topic:30} {count:2} {bar}")
    
    print(f"\n🔍 LAGUNAS DE CONOCIMIENTO IDENTIFICADAS:")
    for i, gap in enumerate(plan['knowledge_gaps'], 1):
        print(f"\n   {i}. {gap['concept'].upper()}")
        print(f"      Hecho clave: {gap['fact'][:80]}...")
        print(f"      Cobertura actual: {gap['coverage_score']} preguntas")
        print(f"      Preguntas sugeridas: {gap['suggested_questions_count']}")
        print(f"      Conceptos de distractores:")
        for concept in gap['distractor_concepts'][:2]:
            print(f"         → {concept}")
    
    print(f"\n📊 TEMAS SUB-REPRESENTADOS (déficit vs objetivo de 10):")
    for topic, deficit in plan['topic_deficit'].items():
        print(f"   {topic}: necesita +{deficit} preguntas")
    
    print(f"\n🎯 PLAN DE GENERACIÓN DE NUEVAS PREGUNTAS:")
    est = plan['estimated_new_questions']
    print(f"   Desde lagunas de conocimiento: {est['from_knowledge_gaps']} preguntas")
    print(f"   Desde balance de temas: {est['from_topic_balance']} preguntas")
    print(f"   ═══════════════════════════════════════")
    print(f"   TOTAL ESTIMADO: {est['total_estimated']} nuevas preguntas")
    
    print(f"\n📚 METODOLOGÍA: {plan['methodology']['name']}")
    print(f"   Técnicas utilizadas:")
    for tech in plan['methodology']['techniques']:
        print(f"      • {tech}")
    
    print(f"\n   Fuentes verificables:")
    for src in plan['methodology']['sources']:
        print(f"      • {src}")
    
    # Guardar el plan
    output_path = base_path / 'TestAssesments' / 'data' / 'json' / 'aig_generation_plan.json'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Plan guardado en: {output_path}")
    
    return plan


if __name__ == '__main__':
    main()
