"""
GES-C01 Exam Simulator - Pearson VUE Style
==========================================

Aplicación Streamlit que emula la experiencia de examen de Pearson VUE.

Características:
- Modo Exam: Tiempo real (115 min), sin feedback hasta el final
- Modo Practice: Sin tiempo, feedback inmediato
- Navegación entre preguntas
- Marcado de preguntas para revisión
- Resumen de rendimiento por tema
- Diseño profesional estilo Pearson VUE

Best Practices aplicadas:
- Spaced Retrieval: Orden aleatorio para mejor retención
- Immediate Feedback (Practice): Refuerza aprendizaje
- Progress Tracking: Visualización de progreso
- Review Functionality: Permite revisar respuestas marcadas
"""

import streamlit as st
import json
import random
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE PÁGINA
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="GES-C01 Exam Simulator",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════════════════════════
# ESTILOS CSS - PEARSON VUE STYLE
# ═══════════════════════════════════════════════════════════════════════════════

PEARSON_VUE_CSS = """
<style>
    /* Variables de color - Pearson VUE Dark Theme */
    :root {
        --pv-primary: #1a1a2e;
        --pv-secondary: #16213e;
        --pv-accent: #0f3460;
        --pv-highlight: #e94560;
        --pv-success: #00b894;
        --pv-warning: #fdcb6e;
        --pv-text: #ffffff;
        --pv-text-muted: #b2bec3;
        --pv-border: #2d3436;
    }
    
    /* Header principal */
    .exam-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 1rem 2rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        border-left: 4px solid #e94560;
    }
    
    .exam-header h1 {
        color: #ffffff;
        margin: 0;
        font-size: 1.5rem;
    }
    
    .exam-header p {
        color: #b2bec3;
        margin: 0.5rem 0 0 0;
    }
    
    /* Timer */
    .timer-box {
        background: linear-gradient(135deg, #0f3460 0%, #1a1a2e 100%);
        padding: 1rem 1.5rem;
        border-radius: 8px;
        text-align: center;
        border: 2px solid #e94560;
    }
    
    .timer-text {
        font-size: 2rem;
        font-weight: bold;
        color: #ffffff;
        font-family: 'Courier New', monospace;
    }
    
    .timer-warning {
        color: #fdcb6e !important;
    }
    
    .timer-critical {
        color: #e94560 !important;
        animation: pulse 1s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    /* Question Box */
    .question-box {
        background: #232741;
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        margin-bottom: 1rem;
        border-left: 4px solid #29b5e8;
    }
    
    .question-number {
        background: #1a1a2e;
        color: #ffffff;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        margin-bottom: 1rem;
    }
    
    .question-topic {
        background: #e94560;
        color: #ffffff;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.8rem;
        margin-left: 0.5rem;
    }
    
    .question-type {
        background: #00b894;
        color: #ffffff;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.8rem;
        margin-left: 0.5rem;
    }
    
    .question-text {
        font-size: 1.1rem;
        line-height: 1.8;
        color: #e0e6ed;
        margin: 1.5rem 0;
    }
    
    /* Navigation Panel */
    .nav-panel {
        background: #1e2235;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    
    .nav-button {
        width: 36px;
        height: 36px;
        margin: 3px;
        border-radius: 6px;
        border: 1px solid #3a4066;
        cursor: pointer;
        font-weight: bold;
        font-size: 0.85rem;
    }
    
    .nav-answered {
        background: #00b894 !important;
        color: white !important;
    }
    
    .nav-marked {
        background: #f39c12 !important;
        color: #2d3436 !important;
    }
    
    .nav-current {
        border: 3px solid #e94560 !important;
    }
    
    /* Progress Bar */
    .progress-container {
        background: #e0e0e0;
        border-radius: 10px;
        height: 8px;
        margin: 1rem 0;
    }
    
    .progress-bar {
        background: linear-gradient(90deg, #00b894 0%, #00cec9 100%);
        height: 100%;
        border-radius: 10px;
        transition: width 0.3s ease;
    }
    
    /* Explanation Box (Practice Mode) */
    .explanation-box {
        background: #1a3a2e;
        border-left: 4px solid #00b894;
        padding: 1.5rem;
        border-radius: 0 8px 8px 0;
        margin-top: 1rem;
        color: #e0e6ed;
    }
    
    .explanation-box h4 {
        margin: 0 0 0.5rem 0;
        color: #00b894;
    }
    
    .explanation-box p {
        margin: 0.5rem 0;
        line-height: 1.5;
    }
    
    .explanation-box.incorrect {
        background: #3a1a2e;
        border-left-color: #e94560;
    }
    
    .explanation-box.incorrect h4 {
        color: #e94560;
    }
    
    /* Results Panel */
    .results-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #0f3460 100%);
        padding: 2rem;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .results-score {
        font-size: 4rem;
        font-weight: bold;
        color: #ffffff;
    }
    
    .results-passed {
        color: #00b894;
    }
    
    .results-failed {
        color: #e94560;
    }
    
    /* Topic Stats */
    .topic-stat {
        background: #f8f9fa;
        padding: 0.8rem 1rem;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .topic-bar {
        height: 8px;
        background: #e0e0e0;
        border-radius: 4px;
        flex-grow: 1;
        margin: 0 1rem;
    }
    
    .topic-bar-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.5s ease;
    }
    
    /* Buttons */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f1f1;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #888;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #555;
    }
</style>
"""

# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE CARGA DE DATOS
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data
def load_questions():
    """Carga las preguntas desde el JSON"""
    # Intentar múltiples ubicaciones
    possible_paths = [
        Path(r'C:\Users\CarlosCarrillo\IA\dataqbs_IA\certificaciones\snowflakeIA\GES-C01_Exam_Sample_Questions.json'),
        Path(__file__).parent.parent / 'GES-C01_Exam_Sample_Questions.json',
        Path(__file__).parent.parent.parent / 'GES-C01_Exam_Sample_Questions.json',
        Path('GES-C01_Exam_Sample_Questions.json'),
        Path('../GES-C01_Exam_Sample_Questions.json'),
    ]
    
    for path in possible_paths:
        try:
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data
        except Exception as e:
            continue
    
    st.error("❌ No se encontró el archivo de preguntas")
    return None


def initialize_exam_state(questions: List[Dict], mode: str):
    """Inicializa el estado del examen"""
    # Aleatorizar orden de preguntas
    shuffled_questions = questions.copy()
    random.shuffle(shuffled_questions)
    
    st.session_state.questions = shuffled_questions
    st.session_state.current_question = 0
    st.session_state.answers = {}  # {question_id: answer}
    st.session_state.marked = set()  # IDs marcados para revisión
    st.session_state.mode = mode
    st.session_state.exam_started = True
    st.session_state.exam_finished = False
    st.session_state.start_time = time.time()
    st.session_state.time_limit = 115 * 60 if mode == "exam" else None  # 115 min en segundos
    st.session_state.show_explanation = {}  # Para modo práctica


def get_remaining_time() -> Optional[int]:
    """Calcula el tiempo restante en segundos"""
    if st.session_state.time_limit is None:
        return None
    
    elapsed = time.time() - st.session_state.start_time
    remaining = st.session_state.time_limit - elapsed
    return max(0, int(remaining))


def format_time(seconds: int) -> str:
    """Formatea segundos como HH:MM:SS"""
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{int(hours):02d}:{int(minutes):02d}:{int(secs):02d}"
    return f"{int(minutes):02d}:{int(secs):02d}"


def calculate_results() -> Dict:
    """Calcula los resultados del examen"""
    results = {
        "total": len(st.session_state.questions),
        "answered": len(st.session_state.answers),
        "correct": 0,
        "by_topic": {},
        "question_details": []
    }
    
    for q in st.session_state.questions:
        qid = q['id']
        topic = q.get('topic', 'Unknown')
        correct_answer = q.get('correctAnswer', '').upper().replace(' ', '')
        user_answer = st.session_state.answers.get(qid, '').upper().replace(' ', '')
        
        # Normalizar respuestas múltiples
        if ',' in correct_answer:
            correct_set = set(correct_answer.split(','))
            user_set = set(user_answer.split(',')) if user_answer else set()
            is_correct = correct_set == user_set
        else:
            is_correct = correct_answer == user_answer
        
        if is_correct:
            results["correct"] += 1
        
        # Stats por tema
        if topic not in results["by_topic"]:
            results["by_topic"][topic] = {"correct": 0, "total": 0}
        results["by_topic"][topic]["total"] += 1
        if is_correct:
            results["by_topic"][topic]["correct"] += 1
        
        results["question_details"].append({
            "id": qid,
            "topic": topic,
            "correct": is_correct,
            "user_answer": user_answer,
            "correct_answer": correct_answer
        })
    
    results["score_percentage"] = (results["correct"] / results["total"] * 100) if results["total"] > 0 else 0
    results["passed"] = results["score_percentage"] >= 75
    
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENTES DE UI
# ═══════════════════════════════════════════════════════════════════════════════

def render_header():
    """Renderiza el header del examen"""
    st.markdown(PEARSON_VUE_CSS, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.markdown("""
        <div class="exam-header">
            <h1>❄️ GES-C01 Exam Simulator</h1>
            <p>SnowPro Specialty: Generative AI Certification</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if st.session_state.get('exam_started') and not st.session_state.get('exam_finished'):
            remaining = get_remaining_time()
            if remaining is not None:
                time_class = ""
                if remaining < 300:  # < 5 min
                    time_class = "timer-critical"
                elif remaining < 900:  # < 15 min
                    time_class = "timer-warning"
                
                st.markdown(f"""
                <div class="timer-box">
                    <div class="timer-text {time_class}">{format_time(remaining)}</div>
                    <small style="color: #b2bec3;">Time Remaining</small>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="timer-box">
                    <div class="timer-text">∞</div>
                    <small style="color: #b2bec3;">Practice Mode</small>
                </div>
                """, unsafe_allow_html=True)
    
    with col3:
        if st.session_state.get('exam_started') and not st.session_state.get('exam_finished'):
            answered = len(st.session_state.answers)
            total = len(st.session_state.questions)
            progress = answered / total * 100 if total > 0 else 0
            
            st.markdown(f"""
            <div class="timer-box" style="border-color: #00b894;">
                <div class="timer-text" style="font-size: 1.5rem;">{answered}/{total}</div>
                <small style="color: #b2bec3;">Answered</small>
            </div>
            """, unsafe_allow_html=True)


def render_welcome_screen(data: Dict):
    """Renderiza la pantalla de bienvenida"""
    st.markdown(PEARSON_VUE_CSS, unsafe_allow_html=True)
    
    questions = data.get('questions', [])
    
    # Header simple y limpio
    st.markdown("""
    <div class="exam-header">
        <h1>❄️ GES-C01 Exam Simulator</h1>
        <p>SnowPro Specialty: Generative AI</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Información esencial en cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Preguntas", len(questions))
    with col2:
        st.metric("Duración", "115 min")
    with col3:
        st.metric("Aprobación", "75%")
    with col4:
        st.metric("Formato", "Single/Multi")
    
    st.markdown("---")
    
    # Botones de inicio prominentes
    col_exam, col_practice = st.columns(2)
    
    with col_exam:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #29b5e8, #1a8fc4); padding: 2rem; border-radius: 15px; text-align: center; color: white;">
            <h2 style="margin: 0; color: white;">📝 Modo Examen</h2>
            <p style="margin: 0.5rem 0 1rem 0; opacity: 0.9;">Tiempo límite • Sin feedback inmediato</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🎯 Iniciar Examen", type="primary", use_container_width=True, key="btn_exam"):
            initialize_exam_state(questions, "exam")
            st.rerun()
    
    with col_practice:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #00d26a, #00a355); padding: 2rem; border-radius: 15px; text-align: center; color: white;">
            <h2 style="margin: 0; color: white;">📚 Modo Práctica</h2>
            <p style="margin: 0.5rem 0 1rem 0; opacity: 0.9;">Sin tiempo • Feedback inmediato</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("📖 Iniciar Práctica", use_container_width=True, key="btn_practice"):
            initialize_exam_state(questions, "practice")
            st.rerun()
    
    st.markdown("---")
    
    # Distribución de preguntas por tema (compacto)
    with st.expander("📊 Distribución por Tema", expanded=False):
        topics = {}
        for q in questions:
            t = q.get('topic', 'Unknown')
            topics[t] = topics.get(t, 0) + 1
        
        for topic, count in sorted(topics.items(), key=lambda x: -x[1]):
            pct = (count / len(questions)) * 100
            st.progress(pct / 100, text=f"{topic}: {count} ({pct:.0f}%)")


def render_question_navigation():
    """Renderiza el panel de navegación de preguntas"""
    st.markdown("### 📍 Navegación")
    
    questions = st.session_state.questions
    current = st.session_state.current_question
    
    # Estilos CSS para el grid de navegación
    st.markdown("""
    <style>
    .nav-grid {
        display: grid;
        grid-template-columns: repeat(10, 1fr);
        gap: 4px;
        margin-bottom: 1rem;
    }
    .nav-item {
        aspect-ratio: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
    }
    .nav-default { background: #2a2f4a; color: #8892b0; border: 1px solid #3a4066; }
    .nav-answered { background: #00b894; color: white; border: none; }
    .nav-marked { background: #f39c12; color: white; border: none; }
    .nav-current { background: #29b5e8; color: white; border: 2px solid #fff; }
    </style>
    """, unsafe_allow_html=True)
    
    # Crear grid de botones de navegación (5 columnas para mejor ajuste)
    cols_per_row = 5
    for i in range(0, len(questions), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            idx = i + j
            if idx < len(questions):
                qid = questions[idx]['id']
                is_answered = qid in st.session_state.answers
                is_marked = qid in st.session_state.marked
                is_current = idx == current
                
                with col:
                    # Determinar icono/símbolo
                    if is_current:
                        label = f"▶{idx + 1}"
                    elif is_marked:
                        label = f"🔖{idx + 1}"
                    elif is_answered:
                        label = f"✓{idx + 1}"
                    else:
                        label = str(idx + 1)
                    
                    btn_type = "primary" if (is_current or is_answered) else "secondary"
                    
                    if st.button(label, key=f"nav_{idx}", use_container_width=True, type=btn_type):
                        st.session_state.current_question = idx
                        st.rerun()
    
    # Leyenda compacta
    st.markdown("""
    <div style="font-size: 0.75rem; color: #8892b0; margin-top: 0.5rem;">
        ✓ Respondida &nbsp;•&nbsp; 🔖 Revisar &nbsp;•&nbsp; ▶ Actual
    </div>
    """, unsafe_allow_html=True)


def render_question():
    """Renderiza la pregunta actual"""
    questions = st.session_state.questions
    current_idx = st.session_state.current_question
    question = questions[current_idx]
    
    qid = question['id']
    topic = question.get('topic', 'Unknown')
    is_multiple = question.get('multipleSelect', False)
    question_text = question.get('question', '')
    correct_answer = question.get('correctAnswer', '')
    explanation = question.get('explanation', '')
    
    # Extraer opciones - primero del campo options, luego del texto
    options = question.get('options', {})
    clean_question = question_text
    has_valid_options = True
    
    # Si options ya existe como dict con valores, usarlas directamente
    if options and isinstance(options, dict) and len(options) >= 2:
        # Verificar que no son opciones genéricas (placeholders OCR)
        # Solo marcar como inválidas si el texto es EXACTAMENTE un placeholder
        first_val = list(options.values())[0].strip().lower() if options else ""
        # Detectar placeholders genéricos: "Option A", "Option B", "[Ver PDF original]", etc.
        import re
        is_placeholder = bool(re.match(r'^option\s*[a-e]\.?$', first_val)) or first_val.startswith('[ver pdf')
        has_valid_options = not is_placeholder
    else:
        # Intentar extraer del texto de la pregunta
        import re

        # Extrae opciones embebidas del tipo:
        #   "A. ... B. ... C. ..." o "A) ... B) ..."
        # Nota: no podemos usar clases como [^A-E] porque el texto de una opción
        # puede contener letras A-E. En su lugar, capturamos hasta el siguiente
        # marcador de opción.
        option_pattern = r'(?:^|\s)([A-Ea-e])[.\)]\s*(.+?)(?=\s+[A-Ea-e][.\)]\s|\s*$)'
        matches = re.findall(option_pattern, question_text, flags=re.S)
        
        if matches and len(matches) >= 2:
            options = {}
            for letter, text in matches:
                clean_text = re.sub(r'\s+', ' ', text).strip()
                letter_u = letter.upper()
                if clean_text.lower() not in [f"option {letter_u.lower()}", f"option{letter_u.lower()}", ""]:
                    options[letter_u] = clean_text
            
            first_option_match = re.search(r'\s+[A-E][.\)]\s', question_text)
            if first_option_match:
                clean_question = question_text[:first_option_match.start()].strip()
        
        if not options or len(options) < 2:
            has_valid_options = False
    
    # Header de la pregunta con mejor espaciado
    type_badge = "Multiple Select" if is_multiple else "Single Select"
    
    # Si no hay opciones válidas, mostrar advertencia
    warning_html = ""
    if not has_valid_options:
        warning_html = """
        <div style="background: #3a2a1a; border-left: 4px solid #f39c12; padding: 0.8rem; margin-top: 1rem; border-radius: 0 8px 8px 0;">
            ⚠️ <strong>Nota:</strong> Las opciones de esta pregunta no se extrajeron correctamente del PDF original. 
            Consulta el documento fuente para ver las opciones completas.
        </div>
        """
    
    st.markdown(f"""
    <div class="question-box">
        <div style="margin-bottom: 1rem;">
            <span class="question-number">Question {current_idx + 1} of {len(questions)}</span>
            <span class="question-topic">{topic}</span>
            <span class="question-type">{type_badge}</span>
        </div>
        <div class="question-text">{clean_question}</div>
        {warning_html}
    </div>
    """, unsafe_allow_html=True)
    
    # Espaciado antes de opciones
    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
    
    # Si no hay opciones válidas, usar placeholders pero marcar visualmente
    if not has_valid_options:
        options = {"A": "[Ver PDF original]", "B": "[Ver PDF original]", "C": "[Ver PDF original]", "D": "[Ver PDF original]", "E": "[Ver PDF original]"}
    
    current_answer = st.session_state.answers.get(qid, '')
    
    if is_multiple:
        st.markdown("**Selecciona todas las que apliquen:**")
        st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
        selected = []
        current_selections = set(current_answer.split(',')) if current_answer else set()
        
        for letter in sorted(options.keys()):
            text = options[letter]
            checked = letter in current_selections
            if st.checkbox(f"**{letter}.** {text}", value=checked, key=f"opt_{qid}_{letter}"):
                selected.append(letter)
            st.markdown("<div style='margin-bottom: 0.3rem;'></div>", unsafe_allow_html=True)
        
        new_answer = ','.join(sorted(selected))
        if new_answer != current_answer:
            st.session_state.answers[qid] = new_answer
    else:
        st.markdown("**Selecciona una:**")
        st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
        option_list = [f"{letter}. {text}" for letter, text in sorted(options.items())]
        
        # Encontrar índice de la respuesta actual
        current_idx_opt = None
        if current_answer:
            for i, opt in enumerate(option_list):
                if opt.startswith(current_answer + "."):
                    current_idx_opt = i
                    break
        
        selected = st.radio(
            "Selecciona tu respuesta:",
            option_list,
            index=current_idx_opt,
            key=f"radio_{qid}",
            label_visibility="collapsed"
        )
        
        if selected:
            letter = selected.split('.')[0]
            if letter != current_answer:
                st.session_state.answers[qid] = letter
    
    # Espaciado antes de botones
    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
    
    # Botón de marcar para revisión
    is_marked = qid in st.session_state.marked
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("🔖 Mark for Review" if not is_marked else "✓ Unmark", use_container_width=True):
            if is_marked:
                st.session_state.marked.discard(qid)
            else:
                st.session_state.marked.add(qid)
            st.rerun()
    
    # Modo práctica: mostrar respuesta
    if st.session_state.mode == "practice":
        with col2:
            show_key = f"show_{qid}"
            if st.button("👁️ Show Answer", use_container_width=True, key=show_key):
                st.session_state.show_explanation[qid] = not st.session_state.show_explanation.get(qid, False)
                st.rerun()
        
        if st.session_state.show_explanation.get(qid, False):
            user_ans = st.session_state.answers.get(qid, '')
            is_correct = False
            
            if ',' in correct_answer:
                correct_set = set(correct_answer.upper().replace(' ', '').split(','))
                user_set = set(user_ans.upper().split(',')) if user_ans else set()
                is_correct = correct_set == user_set
            else:
                is_correct = user_ans.upper() == correct_answer.upper()
            
            box_class = "explanation-box" if is_correct else "explanation-box incorrect"
            status = "✅ ¡Correcto!" if is_correct else "❌ Incorrecto"
            
            explanation_text = explanation if explanation else "No hay explicación disponible para esta pregunta."
            
            st.markdown(f"""
            <div class="{box_class}">
                <h4>{status}</h4>
                <p><strong>Respuesta correcta:</strong> {correct_answer}</p>
                <p><strong>Explicación:</strong> {explanation_text}</p>
            </div>
            """, unsafe_allow_html=True)


def render_navigation_buttons():
    """Renderiza los botones de navegación"""
    questions = st.session_state.questions
    current = st.session_state.current_question
    
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    
    with col1:
        if current > 0:
            if st.button("⬅️ Previous", use_container_width=True):
                st.session_state.current_question -= 1
                st.rerun()
    
    with col2:
        if current < len(questions) - 1:
            if st.button("Next ➡️", use_container_width=True):
                st.session_state.current_question += 1
                st.rerun()
    
    with col3:
        # Ir a primera sin responder
        unanswered = None
        for i, q in enumerate(questions):
            if q['id'] not in st.session_state.answers:
                unanswered = i
                break
        
        if unanswered is not None:
            if st.button(f"📋 Next Unanswered ({unanswered + 1})", use_container_width=True):
                st.session_state.current_question = unanswered
                st.rerun()
    
    with col4:
        if st.button("🏁 Finish Exam", type="primary", use_container_width=True):
            unanswered_count = len(questions) - len(st.session_state.answers)
            if unanswered_count > 0:
                st.warning(f"⚠️ You have {unanswered_count} unanswered questions!")
            st.session_state.exam_finished = True
            st.rerun()


def render_results():
    """Renderiza la pantalla de resultados"""
    results = calculate_results()
    
    st.markdown(PEARSON_VUE_CSS, unsafe_allow_html=True)
    
    # Header de resultados
    score_class = "results-passed" if results["passed"] else "results-failed"
    status_text = "PASSED ✅" if results["passed"] else "NOT PASSED ❌"
    
    st.markdown(f"""
    <div class="results-header">
        <h1>Exam Complete</h1>
        <div class="results-score {score_class}">{results['score_percentage']:.1f}%</div>
        <h2>{status_text}</h2>
        <p>Passing Score: 75% | Your Score: {results['correct']}/{results['total']} correct</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Stats por tema
    st.markdown("### 📊 Performance by Domain")
    
    for topic, stats in sorted(results["by_topic"].items(), key=lambda x: x[1]["correct"]/max(x[1]["total"],1)):
        pct = stats["correct"] / stats["total"] * 100 if stats["total"] > 0 else 0
        color = "#00b894" if pct >= 75 else "#fdcb6e" if pct >= 50 else "#e94560"
        
        col1, col2, col3 = st.columns([2, 3, 1])
        with col1:
            st.markdown(f"**{topic}**")
        with col2:
            st.progress(pct / 100)
        with col3:
            st.markdown(f"**{stats['correct']}/{stats['total']}** ({pct:.0f}%)")
    
    # Tiempo total
    if st.session_state.time_limit:
        elapsed = time.time() - st.session_state.start_time
        st.markdown(f"### ⏱️ Time: {format_time(int(elapsed))}")
    
    # Revisión de respuestas
    st.markdown("### 📝 Question Review")
    
    show_incorrect = st.checkbox("Show only incorrect answers", value=True)
    
    for detail in results["question_details"]:
        if show_incorrect and detail["correct"]:
            continue
        
        q = next((q for q in st.session_state.questions if q['id'] == detail['id']), None)
        if q:
            status = "✅" if detail["correct"] else "❌"
            with st.expander(f"{status} Q{detail['id']}: {detail['topic']}"):
                st.markdown(f"**Question:** {q.get('question', '')[:200]}...")
                st.markdown(f"**Your Answer:** {detail['user_answer'] or 'Not answered'}")
                st.markdown(f"**Correct Answer:** {detail['correct_answer']}")
                st.markdown(f"**Explanation:** {q.get('explanation', '')}")
    
    # Botones de acción
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Restart Exam", type="primary", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    with col2:
        if st.button("📊 Download Results", use_container_width=True):
            results_json = json.dumps(results, indent=2)
            st.download_button(
                "💾 Download JSON",
                results_json,
                f"exam_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "application/json"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    # Cargar datos
    data = load_questions()
    
    if data is None:
        st.error("Failed to load questions. Please check the file path.")
        return
    
    # Verificar si el examen ha terminado por tiempo
    if st.session_state.get('exam_started') and not st.session_state.get('exam_finished'):
        remaining = get_remaining_time()
        if remaining is not None and remaining <= 0:
            st.session_state.exam_finished = True
            st.warning("⏰ Time's up! Your exam has been automatically submitted.")
    
    # Renderizar la interfaz apropiada
    if not st.session_state.get('exam_started'):
        render_welcome_screen(data)
    
    elif st.session_state.get('exam_finished'):
        render_results()
    
    else:
        render_header()
        
        # Layout principal
        col_main, col_nav = st.columns([3, 1])
        
        with col_main:
            render_question()
            render_navigation_buttons()
        
        with col_nav:
            render_question_navigation()
        
        # Auto-refresh para el timer (cada 30 segundos)
        if st.session_state.time_limit:
            time.sleep(0.1)  # Pequeña pausa para evitar sobrecarga


if __name__ == "__main__":
    main()
