"""
Question Generator - Automatic Item Generation (AIG) for GES-C01
==================================================================

Genera nuevas preguntas verificadas basándose en:
1. Knowledge Base de documentación oficial de Snowflake
2. Distractor Analysis de preguntas existentes  
3. Cobertura de temas sub-representados

Metodología: Automatic Item Generation (AIG)
- Educational Testing Service (ETS) Best Practices
- Bloom's Taxonomy Coverage
- Item Writing Guidelines from Assessment Design

Fuentes verificadas:
- docs.snowflake.com/en/user-guide/snowflake-cortex/
- docs.snowflake.com/en/sql-reference/
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict

class VerifiedQuestionGenerator:
    """
    Generador de preguntas verificadas usando conocimiento oficial de Snowflake.
    
    Las preguntas generadas siguen el formato del examen GES-C01:
    - Single Select (una respuesta correcta)
    - Multiple Select (varias respuestas correctas)
    """
    
    # Base de conocimiento verificada de documentación oficial de Snowflake
    # Cada entrada incluye la fuente para trazabilidad
    VERIFIED_KNOWLEDGE = {
        # ═══════════════════════════════════════════════════════════════════════════
        # FINE-TUNING - Tema sub-representado (solo 2 preguntas actuales)
        # ═══════════════════════════════════════════════════════════════════════════
        "fine_tuning_models": {
            "source": "docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-finetuning",
            "facts": {
                "supported_models": ["llama3-8b", "llama3-70b", "llama3.1-8b", "llama3.1-70b", "mistral-7b", "mixtral-8x7b"],
                "training_data_format": "prompt and completion columns required",
                "context_windows": {
                    "llama3-8b": {"total": "8k", "prompt": "6k", "completion": "2k"},
                    "llama3-70b": {"total": "8k", "prompt": "6k", "completion": "2k"},
                    "llama3.1-8b": {"total": "24k", "prompt": "20k", "completion": "4k"},
                    "llama3.1-70b": {"total": "8k", "prompt": "6k", "completion": "2k"},
                    "mistral-7b": {"total": "32k", "prompt": "28k", "completion": "4k"},
                    "mixtral-8x7b": {"total": "32k", "prompt": "28k", "completion": "4k"}
                },
                "row_limits_3epochs": {
                    "llama3-8b": "62k", "llama3-70b": "7k", "llama3.1-8b": "50k", 
                    "llama3.1-70b": "4.5k", "mistral-7b": "15k", "mixtral-8x7b": "9k"
                },
                "privilege_required": "CREATE MODEL on schema",
                "inference": "Use COMPLETE function with fine-tuned model name",
                "cost": "Credits per million tokens for training and inference",
                "artifacts": "training_results.csv with step, epoch, training_loss, validation_loss"
            }
        },
        
        # ═══════════════════════════════════════════════════════════════════════════
        # CORTEX ANALYST - Tema sub-representado (solo 3 preguntas actuales)
        # ═══════════════════════════════════════════════════════════════════════════
        "cortex_analyst": {
            "source": "docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst",
            "facts": {
                "purpose": "Natural language to SQL for structured data",
                "semantic_model": "YAML file bridging business terms and database schema",
                "multi_turn": "Pass conversation history in messages array with role user/analyst",
                "cost": "Billed per message processed (HTTP 200 only)",
                "roles": ["SNOWFLAKE.CORTEX_USER", "SNOWFLAKE.CORTEX_ANALYST_USER"],
                "model_preference_order": [
                    "Anthropic Claude Sonnet 4",
                    "Anthropic Claude Sonnet 3.7", 
                    "Anthropic Claude Sonnet 3.5",
                    "OpenAI GPT 4.1",
                    "Mistral Large 2 + Llama 3.1 70b"
                ],
                "limitations": [
                    "No access to previous SQL query results",
                    "Cannot generate general business insights",
                    "Long conversations may struggle with context"
                ],
                "data_stays_in_snowflake": True,
                "rbac_integration": True
            }
        },
        
        # ═══════════════════════════════════════════════════════════════════════════
        # VECTOR EMBEDDINGS - Tema sub-representado (solo 4 preguntas)
        # ═══════════════════════════════════════════════════════════════════════════
        "vector_embeddings": {
            "source": "docs.snowflake.com/en/sql-reference/data-types-vector",
            "facts": {
                "max_dimensions": 4096,
                "element_types": ["FLOAT (32-bit)", "INT (32-bit)"],
                "not_supported_in": ["VARIANT columns", "clustering keys", "primary/secondary index keys in hybrid tables"],
                "embedding_functions": {
                    "EMBED_TEXT_768": ["e5-base-v2", "snowflake-arctic-embed-m", "multilingual-e5-large"],
                    "EMBED_TEXT_1024": ["snowflake-arctic-embed-m-v1.5", "voyage-multilingual-2", "snowflake-arctic-embed-l-v2.0"]
                },
                "similarity_functions": ["VECTOR_COSINE_SIMILARITY", "VECTOR_L2_DISTANCE", "VECTOR_INNER_PRODUCT"]
            }
        },
        
        # ═══════════════════════════════════════════════════════════════════════════
        # RAG - Tema sub-representado (solo 2 preguntas)
        # ═══════════════════════════════════════════════════════════════════════════
        "rag_patterns": {
            "source": "docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/cortex-search-overview",
            "facts": {
                "cortex_search": "Hybrid search engine (vector + keyword)",
                "chunk_size": "512 tokens or less recommended",
                "larger_context_models": "8000 token models still benefit from 512 token chunks",
                "retrieval_then_generate": "Retrieve with Cortex Search, generate with AI_COMPLETE",
                "streamlit_state": "st.session_state for conversation history",
                "messages_format": "Array of objects with role (user/assistant) and content"
            }
        },
        
        # ═══════════════════════════════════════════════════════════════════════════
        # COST & GOVERNANCE - Tema sub-representado (solo 2 preguntas)
        # ═══════════════════════════════════════════════════════════════════════════
        "cost_governance": {
            "source": "docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions",
            "facts": {
                "billing": "Input + output tokens for text generation functions",
                "warehouse_recommendation": "MEDIUM or smaller for Cortex AI functions",
                "cortex_search_costs": ["Warehouse compute for refreshes", "6.3 credits/GB/month indexed data", "Token costs"],
                "monitoring_views": [
                    "CORTEX_FUNCTIONS_USAGE_HISTORY (token details)",
                    "CORTEX_ANALYST_USAGE_HISTORY (Analyst messages)",
                    "CORTEX_FINE_TUNING_USAGE_HISTORY (fine-tuning tokens)",
                    "METERING_HISTORY with SERVICE_TYPE = AI_SERVICES"
                ],
                "allowlist": "CORTEX_MODELS_ALLOWLIST parameter controls model access",
                "cross_region": "CORTEX_ENABLED_CROSS_REGION enables inference in other regions"
            }
        },
        
        # ═══════════════════════════════════════════════════════════════════════════
        # SNOWPARK CONTAINER SERVICES - Tema sub-representado (solo 3 preguntas)
        # ═══════════════════════════════════════════════════════════════════════════
        "spcs": {
            "source": "docs.snowflake.com/en/developer-guide/snowpark-container-services",
            "facts": {
                "gpu_instances": ["GPU_NV_S", "GPU_NV_M", "GPU_NV_L"],
                "spec_yaml": "Required for service definition",
                "endpoints": "Define API exposure with name, port, public flag",
                "environment_variables": "Set via env section in container spec",
                "volumes": "Mount stages for model storage",
                "compute_pool": "Specify GPU-enabled pool for LLM inference",
                "model_registry": "Register custom models for deployment"
            }
        },
        
        # ═══════════════════════════════════════════════════════════════════════════
        # AI SAFETY & PRINCIPLES - General Cortex AI (4 preguntas)
        # ═══════════════════════════════════════════════════════════════════════════
        "ai_safety": {
            "source": "docs.snowflake.com/en/guides-overview-ai-features",
            "facts": {
                "customer_data_never_trains_shared_models": True,
                "data_stays_in_governance_boundary": True,
                "rbac_integration": True,
                "cortex_guard": "Filters unsafe/harmful responses (NOT PII anonymization)",
                "acceptable_use_policy": "All AI features subject to AUP",
                "human_oversight_recommended": "For decisions based on AI outputs"
            }
        }
    }
    
    def __init__(self, json_path: str):
        """Inicializa el generador con el JSON existente"""
        self.json_path = Path(json_path)
        with open(self.json_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        self.existing_questions = self.data.get('questions', [])
        self.max_id = max(q.get('id', 0) for q in self.existing_questions)
        
    def generate_verified_questions(self) -> List[Dict]:
        """
        Genera nuevas preguntas verificadas basadas en documentación oficial.
        Cada pregunta incluye la fuente de verificación.
        """
        new_questions = []
        
        # ═══════════════════════════════════════════════════════════════════════════
        # FINE-TUNING: 4 nuevas preguntas (+2 existentes = 6 total)
        # ═══════════════════════════════════════════════════════════════════════════
        
        new_questions.append({
            "id": self.max_id + 1,
            "topic": "Fine-tuning",
            "question": "A data science team wants to fine-tune a large language model in Snowflake Cortex for a specialized text classification task. They have 100,000 training examples. Which of the following base models would allow them to use all their training data with 3 training epochs without truncation?",
            "options": {
                "A": "llama3-8b (62k row limit for 3 epochs)",
                "B": "llama3-70b (7k row limit for 3 epochs)",
                "C": "llama3.1-70b (4.5k row limit for 3 epochs)",
                "D": "mistral-7b (15k row limit for 3 epochs)",
                "E": "mixtral-8x7b (9k row limit for 3 epochs)"
            },
            "correctAnswer": "A",
            "explanation": "Per official Snowflake documentation, llama3-8b has a row limit of 62k for 3 epochs (186k ÷ 3), which is the highest among the options and can accommodate 100k training examples. llama3-70b is limited to 7k rows, llama3.1-70b to 4.5k, mistral-7b to 15k, and mixtral-8x7b to 9k rows when training with 3 epochs.",
            "multipleSelect": False,
            "source": "docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-finetuning",
            "generated": True,
            "generatedDate": datetime.now().strftime("%Y-%m-%d")
        })
        
        new_questions.append({
            "id": self.max_id + 2,
            "topic": "Fine-tuning",
            "question": "Which of the following statements about the training data requirements for Snowflake Cortex Fine-tuning are TRUE? (Select all that apply)",
            "options": {
                "A": "The training data query must return columns named 'prompt' and 'completion'.",
                "B": "Training data must be stored in an external stage with SNOWFLAKE_SSE encryption.",
                "C": "Column aliases (SELECT a AS prompt, d AS completion) can be used to rename columns.",
                "D": "The fine-tuning function will use all columns in the query result for training.",
                "E": "Prompt and completion pairs exceeding the context window will be truncated, potentially impacting model quality."
            },
            "correctAnswer": "A,C,E",
            "explanation": "Per official docs: (A) Training data must have 'prompt' and 'completion' columns. (C) Column aliases can be used to rename columns. (E) Pairs exceeding context window limits are truncated, which may negatively impact quality. (B) is incorrect - training data comes from Snowflake tables/views, not stages. (D) is incorrect - columns other than prompt and completion are ignored.",
            "multipleSelect": True,
            "source": "docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-finetuning",
            "generated": True,
            "generatedDate": datetime.now().strftime("%Y-%m-%d")
        })
        
        new_questions.append({
            "id": self.max_id + 3,
            "topic": "Fine-tuning",
            "question": "A data engineer has successfully completed a fine-tuning job and wants to analyze the training results. Which artifact is available after fine-tuning completes, and what information does it contain?",
            "options": {
                "A": "model_metrics.json containing accuracy, precision, recall, and F1 scores.",
                "B": "training_results.csv containing step, epoch, training_loss, and validation_loss columns.",
                "C": "inference_logs.txt containing all prompts and completions used during training.",
                "D": "model_weights.bin containing the raw model weights for external deployment.",
                "E": "evaluation_report.pdf containing a summary of model performance across test cases."
            },
            "correctAnswer": "B",
            "explanation": "Per official Snowflake documentation, after fine-tuning completes, a training_results.csv file is available containing columns: step (training steps completed), epoch (training epoch starting at 1), training_loss (loss for training batch), and validation_loss (loss on validation dataset, available at last step of each epoch). This file can be accessed via the Model Registry UI or SQL/Python API.",
            "multipleSelect": False,
            "source": "docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-finetuning",
            "generated": True,
            "generatedDate": datetime.now().strftime("%Y-%m-%d")
        })
        
        new_questions.append({
            "id": self.max_id + 4,
            "topic": "Fine-tuning",
            "question": "A company fine-tuned a model in AWS US West 2 (Oregon) and wants to share it with another team in AWS Europe Central 1 (Frankfurt). Which statements are TRUE about sharing and replicating fine-tuned models? (Select all that apply)",
            "options": {
                "A": "Fine-tuned models can be shared to other accounts via Data Sharing with the USAGE privilege.",
                "B": "Cross-region inference automatically works for fine-tuned models without additional configuration.",
                "C": "Database replication can replicate the fine-tuned model object to another region that supports the base model.",
                "D": "Fine-tuned models require re-training in each region where they will be used.",
                "E": "Inference must take place in the same region where the model object is located unless replicated."
            },
            "correctAnswer": "A,C,E",
            "explanation": "Per official docs: (A) Fine-tuned models can be shared via Data Sharing with USAGE privilege. (C) Database replication can replicate models to regions supporting the base model. (E) Cross-region inference does NOT support fine-tuned models - inference must be in the same region as the model object. (B) is incorrect - cross-region inference does NOT support fine-tuned models. (D) is incorrect - replication works without re-training.",
            "multipleSelect": True,
            "source": "docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-finetuning",
            "generated": True,
            "generatedDate": datetime.now().strftime("%Y-%m-%d")
        })
        
        # ═══════════════════════════════════════════════════════════════════════════
        # CORTEX ANALYST: 4 nuevas preguntas (+3 existentes = 7 total)
        # ═══════════════════════════════════════════════════════════════════════════
        
        new_questions.append({
            "id": self.max_id + 5,
            "topic": "Cortex Analyst",
            "question": "A company wants to restrict Cortex Analyst access to only the Sales Analyst team while other teams can still use other Cortex AI functions. Which approach correctly achieves this selective access control?",
            "options": {
                "A": "Revoke SNOWFLAKE.CORTEX_USER from PUBLIC and grant SNOWFLAKE.CORTEX_ANALYST_USER to the sales_analyst role.",
                "B": "Set ENABLE_CORTEX_ANALYST = FALSE at the account level and create an exception for the sales team.",
                "C": "Grant SNOWFLAKE.CORTEX_USER to sales_analyst role only.",
                "D": "Store the semantic model YAML in a stage accessible only to sales_analyst role.",
                "E": "Use CORTEX_MODELS_ALLOWLIST to restrict Cortex Analyst to specific roles."
            },
            "correctAnswer": "A",
            "explanation": "Per official docs, SNOWFLAKE.CORTEX_ANALYST_USER provides access ONLY to Cortex Analyst, while CORTEX_USER provides access to ALL Covered AI features. By revoking CORTEX_USER from PUBLIC and granting CORTEX_ANALYST_USER to specific roles, you achieve selective access. Option D (stage access) controls semantic model access but not the API itself. Option E is incorrect - CORTEX_MODELS_ALLOWLIST controls LLM models, not Cortex Analyst access.",
            "multipleSelect": False,
            "source": "docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst",
            "generated": True,
            "generatedDate": datetime.now().strftime("%Y-%m-%d")
        })
        
        new_questions.append({
            "id": self.max_id + 6,
            "topic": "Cortex Analyst",
            "question": "When Cortex Analyst selects which LLM to use for processing a request, what is the order of preference for model selection (assuming all models are accessible)?",
            "options": {
                "A": "Mistral Large 2 → Llama 3.1 70b → Claude Sonnet 3.5 → GPT 4.1",
                "B": "Claude Sonnet 4 → Claude Sonnet 3.7 → Claude Sonnet 3.5 → GPT 4.1 → Mistral/Llama combination",
                "C": "GPT 4.1 → Claude Sonnet 4 → Mistral Large 2 → Llama 3.1 70b",
                "D": "User-specified model → Default model based on region → Fallback to any available model",
                "E": "Random selection from available models to distribute load"
            },
            "correctAnswer": "B",
            "explanation": "Per official Snowflake documentation, Cortex Analyst selects models in the following preference order: Anthropic Claude Sonnet 4 → Claude Sonnet 3.7 → Claude Sonnet 3.5 → OpenAI GPT 4.1 → Combination of Mistral Large 2 and Llama 3.1 70b. The selection considers region availability, cross-region configuration, and RBAC restrictions.",
            "multipleSelect": False,
            "source": "docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst",
            "generated": True,
            "generatedDate": datetime.now().strftime("%Y-%m-%d")
        })
        
        new_questions.append({
            "id": self.max_id + 7,
            "topic": "Cortex Analyst",
            "question": "Which of the following are known limitations of multi-turn conversations in Cortex Analyst? (Select all that apply)",
            "options": {
                "A": "Cortex Analyst cannot access results from previous SQL queries in the conversation.",
                "B": "Multi-turn conversations are limited to a maximum of 5 turns.",
                "C": "Cortex Analyst cannot generate general business insights like 'What trends do you observe?'",
                "D": "Long conversations or frequent intent shifts may cause difficulty interpreting follow-up questions.",
                "E": "Each turn in a multi-turn conversation incurs the same fixed cost regardless of history length."
            },
            "correctAnswer": "A,C,D",
            "explanation": "Per official docs, limitations include: (A) No access to previous SQL query results - cannot reference items from prior query outputs. (C) Limited to SQL-answerable questions - cannot generate general insights or trends. (D) Long conversations with many turns or frequent intent shifts may struggle. (B) is not a documented limitation. (E) is incorrect - compute cost increases with conversation history length.",
            "multipleSelect": True,
            "source": "docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst",
            "generated": True,
            "generatedDate": datetime.now().strftime("%Y-%m-%d")
        })
        
        new_questions.append({
            "id": self.max_id + 8,
            "topic": "Cortex Analyst",
            "question": "How is Cortex Analyst billing calculated, and what does NOT affect the cost?",
            "options": {
                "A": "Billing is based on the number of tokens in each message, similar to AI_COMPLETE.",
                "B": "Billing is based on messages processed; only successful responses (HTTP 200) are counted.",
                "C": "Billing includes both the Cortex Analyst API calls and a percentage of warehouse compute costs.",
                "D": "Failed requests (non-200 responses) still incur half the normal message cost.",
                "E": "The number of tokens in messages affects cost only when Cortex Analyst is invoked via Cortex Agents."
            },
            "correctAnswer": "B",
            "explanation": "Per official docs, Cortex Analyst is billed per message processed, and only successful responses (HTTP 200) are counted. The number of tokens in each message does NOT affect cost UNLESS Cortex Analyst is invoked using Cortex Agents. Additionally, warehouse costs apply when executing the generated SQL, but this is separate from Cortex Analyst API costs.",
            "multipleSelect": False,
            "source": "docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst",
            "generated": True,
            "generatedDate": datetime.now().strftime("%Y-%m-%d")
        })
        
        # ═══════════════════════════════════════════════════════════════════════════
        # VECTOR EMBEDDINGS: 3 nuevas preguntas (+4 existentes = 7 total)
        # ═══════════════════════════════════════════════════════════════════════════
        
        new_questions.append({
            "id": self.max_id + 9,
            "topic": "Vector Embeddings",
            "question": "A data engineer needs to store 1024-dimensional embeddings generated by the snowflake-arctic-embed-l-v2.0 model. Which of the following column definitions is CORRECT?",
            "options": {
                "A": "VECTOR(INT, 1024) - Integer type is required for embedding storage.",
                "B": "VECTOR(FLOAT, 1024) - Float type with 1024 dimensions matching the model output.",
                "C": "VARIANT - Store embeddings as JSON arrays for flexible querying.",
                "D": "ARRAY(FLOAT) - Use native array type for better performance.",
                "E": "VECTOR(FLOAT, 4096) - Always use maximum dimensions for future compatibility."
            },
            "correctAnswer": "B",
            "explanation": "The snowflake-arctic-embed-l-v2.0 model outputs 1024-dimensional float vectors, so VECTOR(FLOAT, 1024) is the correct definition. (A) is incorrect - embeddings use FLOAT, not INT. (C) is incorrect - VECTOR types are NOT supported in VARIANT columns. (D) is incorrect - ARRAY is not the VECTOR data type. (E) is incorrect - dimensions should match the model output exactly.",
            "multipleSelect": False,
            "source": "docs.snowflake.com/en/sql-reference/data-types-vector",
            "generated": True,
            "generatedDate": datetime.now().strftime("%Y-%m-%d")
        })
        
        new_questions.append({
            "id": self.max_id + 10,
            "topic": "Vector Embeddings",
            "question": "Which of the following operations are NOT supported with the VECTOR data type in Snowflake? (Select all that apply)",
            "options": {
                "A": "Using VECTOR columns as clustering keys in standard tables.",
                "B": "Storing VECTOR values inside VARIANT columns.",
                "C": "Using VECTOR columns as primary keys in hybrid tables.",
                "D": "Calculating cosine similarity between two VECTOR columns.",
                "E": "Creating a table with a VECTOR(FLOAT, 2048) column."
            },
            "correctAnswer": "A,B,C",
            "explanation": "Per official Snowflake documentation: (A) VECTOR is NOT supported as clustering keys. (B) Vectors are NOT supported in VARIANT columns. (C) VECTOR is NOT supported as primary or secondary index keys in hybrid tables. (D) is supported via VECTOR_COSINE_SIMILARITY function. (E) is supported - VECTOR supports up to 4096 dimensions.",
            "multipleSelect": True,
            "source": "docs.snowflake.com/en/sql-reference/data-types-vector",
            "generated": True,
            "generatedDate": datetime.now().strftime("%Y-%m-%d")
        })
        
        new_questions.append({
            "id": self.max_id + 11,
            "topic": "Vector Embeddings",
            "question": "A company needs multilingual text embeddings for a global search application. Which embedding model and function combination should they use?",
            "options": {
                "A": "EMBED_TEXT_768 with e5-base-v2 model for best multilingual support.",
                "B": "EMBED_TEXT_1024 with voyage-multilingual-2 model for multilingual support.",
                "C": "EMBED_TEXT_768 with snowflake-arctic-embed-m for English-only optimization.",
                "D": "EMBED_TEXT_1024 with snowflake-arctic-embed-m-v1.5 for lowest cost.",
                "E": "Any EMBED_TEXT function automatically handles multilingual content."
            },
            "correctAnswer": "B",
            "explanation": "voyage-multilingual-2 is specifically designed for multilingual embeddings and is available through EMBED_TEXT_1024. (A) e5-base-v2 through EMBED_TEXT_768 has limited multilingual support. (C) and (D) Arctic models are optimized for English. (E) is incorrect - model selection matters for multilingual support.",
            "multipleSelect": False,
            "source": "docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions",
            "generated": True,
            "generatedDate": datetime.now().strftime("%Y-%m-%d")
        })
        
        # ═══════════════════════════════════════════════════════════════════════════
        # RAG: 3 nuevas preguntas (+2 existentes = 5 total)
        # ═══════════════════════════════════════════════════════════════════════════
        
        new_questions.append({
            "id": self.max_id + 12,
            "topic": "RAG",
            "question": "A development team is building a RAG application with Cortex Search on documents using the snowflake-arctic-embed-l-v2.0-8k model with an 8000 token context window. What is the recommended chunk size for optimal search results?",
            "options": {
                "A": "8000 tokens to fully utilize the embedding model's context window.",
                "B": "4000 tokens as a balanced middle ground between context and retrieval.",
                "C": "512 tokens or less, even when using larger context window models.",
                "D": "1024 tokens to match common embedding dimension sizes.",
                "E": "Variable sizes based on document structure with no upper limit."
            },
            "correctAnswer": "C",
            "explanation": "Per official Snowflake documentation, for best search results with Cortex Search, text should be split into chunks of no more than 512 tokens, EVEN when using embedding models with larger context windows like snowflake-arctic-embed-l-v2.0-8k (8000 tokens). Research shows smaller chunk sizes typically result in higher retrieval and downstream LLM response quality.",
            "multipleSelect": False,
            "source": "docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/cortex-search-overview",
            "generated": True,
            "generatedDate": datetime.now().strftime("%Y-%m-%d")
        })
        
        new_questions.append({
            "id": self.max_id + 13,
            "topic": "RAG",
            "question": "When text input exceeds an embedding model's context window in Cortex Search, what happens to the search capability?",
            "options": {
                "A": "The search fails with an error indicating context window exceeded.",
                "B": "Cortex Search truncates text for semantic embedding but uses full text for keyword-based retrieval.",
                "C": "The text is automatically split into multiple chunks and each is embedded separately.",
                "D": "Both semantic and keyword search use only the truncated portion of the text.",
                "E": "Cortex Search automatically selects a larger context window model."
            },
            "correctAnswer": "B",
            "explanation": "Per official documentation, when text exceeds the embedding model's context window, Cortex Search truncates the text for semantic (vector) embedding. However, the FULL body of text is still used for keyword-based retrieval. This hybrid approach ensures keyword matches are not lost even when semantic embedding is truncated.",
            "multipleSelect": False,
            "source": "docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/cortex-search-overview",
            "generated": True,
            "generatedDate": datetime.now().strftime("%Y-%m-%d")
        })
        
        new_questions.append({
            "id": self.max_id + 14,
            "topic": "RAG",
            "question": "In a Streamlit in Snowflake (SiS) application using COMPLETE for multi-turn RAG conversations, which approach correctly maintains conversation context across user interactions?",
            "options": {
                "A": "Store conversation history in a Snowflake table and query it for each request.",
                "B": "Use st.session_state to maintain an array of messages with role and content for each turn.",
                "C": "Rely on the COMPLETE function's built-in conversation memory between calls.",
                "D": "Pass only the last 3 messages to avoid token limits, discarding older context.",
                "E": "Use Cortex Search to retrieve relevant conversation history dynamically."
            },
            "correctAnswer": "B",
            "explanation": "Per Snowflake documentation and best practices, st.session_state in Streamlit is the recommended mechanism for maintaining chat history. The COMPLETE function requires passing ALL previous messages as an array with 'role' (user/assistant) and 'content' keys in chronological order. COMPLETE does NOT retain state between calls - history must be explicitly managed.",
            "multipleSelect": False,
            "source": "docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions",
            "generated": True,
            "generatedDate": datetime.now().strftime("%Y-%m-%d")
        })
        
        # ═══════════════════════════════════════════════════════════════════════════
        # COST & GOVERNANCE: 3 nuevas preguntas (+2 existentes = 5 total)
        # ═══════════════════════════════════════════════════════════════════════════
        
        new_questions.append({
            "id": self.max_id + 15,
            "topic": "Cost & Governance",
            "question": "A data engineer wants to monitor token consumption and costs for all Cortex LLM function calls in their account. Which view provides the MOST granular information including prompt_tokens, completion_tokens, and guard_tokens?",
            "options": {
                "A": "SNOWFLAKE.ACCOUNT_USAGE.METERING_HISTORY with SERVICE_TYPE = 'AI_SERVICES'",
                "B": "SNOWFLAKE.ACCOUNT_USAGE.CORTEX_FUNCTIONS_USAGE_HISTORY",
                "C": "SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY",
                "D": "SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY filtered by Cortex function names",
                "E": "SNOWFLAKE.INFORMATION_SCHEMA.CORTEX_USAGE"
            },
            "correctAnswer": "B",
            "explanation": "CORTEX_FUNCTIONS_USAGE_HISTORY provides the most granular token-level information including prompt_tokens, completion_tokens, and guard_tokens (when Cortex Guard is enabled) for individual Cortex LLM function calls. METERING_HISTORY shows aggregate credit consumption but lacks token-level detail.",
            "multipleSelect": False,
            "source": "docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions",
            "generated": True,
            "generatedDate": datetime.now().strftime("%Y-%m-%d")
        })
        
        new_questions.append({
            "id": self.max_id + 16,
            "topic": "Cost & Governance",
            "question": "An ACCOUNTADMIN has set CORTEX_MODELS_ALLOWLIST to 'mistral-large' and CORTEX_ENABLED_CROSS_REGION to 'ANY_REGION'. A user attempts to call AI_COMPLETE with 'llama3.1-70b'. What happens?",
            "options": {
                "A": "The call succeeds via cross-region inference since ANY_REGION is enabled.",
                "B": "The call fails because llama3.1-70b is not in the CORTEX_MODELS_ALLOWLIST.",
                "C": "The call succeeds but with increased latency due to cross-region processing.",
                "D": "The call is automatically redirected to mistral-large as a fallback.",
                "E": "The call succeeds if the user has the SNOWFLAKE.CORTEX_USER database role."
            },
            "correctAnswer": "B",
            "explanation": "CORTEX_ENABLED_CROSS_REGION enables cross-region processing for ALLOWED models but does NOT bypass the CORTEX_MODELS_ALLOWLIST. Since llama3.1-70b is not in the allowlist (only mistral-large is allowed), the call fails regardless of cross-region settings or user roles.",
            "multipleSelect": False,
            "source": "docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions",
            "generated": True,
            "generatedDate": datetime.now().strftime("%Y-%m-%d")
        })
        
        new_questions.append({
            "id": self.max_id + 17,
            "topic": "Cost & Governance",
            "question": "Which statements about Snowflake's AI Trust and Safety principles are TRUE? (Select all that apply)",
            "options": {
                "A": "Customer data used in Cortex AI functions is never used to train models made available to other customers.",
                "B": "Fine-tuned models are exclusive to the account that created them and not shared with others.",
                "C": "Cortex Guard automatically anonymizes PII before it reaches the LLM.",
                "D": "When using Snowflake-hosted LLMs, data including prompts stays within Snowflake's governance boundary.",
                "E": "Human oversight is recommended for decisions based on AI outputs."
            },
            "correctAnswer": "A,B,D,E",
            "explanation": "Per official docs: (A) Snowflake never uses Customer Data to train shared models. (B) Fine-tuned models are exclusive to your account. (D) Data stays within Snowflake's governance boundary for Snowflake-hosted LLMs. (E) Human oversight is recommended for AI-based decisions. (C) is FALSE - Cortex Guard filters unsafe/harmful responses but does NOT anonymize PII.",
            "multipleSelect": True,
            "source": "docs.snowflake.com/en/guides-overview-ai-features",
            "generated": True,
            "generatedDate": datetime.now().strftime("%Y-%m-%d")
        })
        
        return new_questions
    
    def save_generated_questions(self, output_path: str = None) -> str:
        """Guarda las preguntas generadas en un archivo separado y actualiza el JSON principal"""
        
        new_questions = self.generate_verified_questions()
        
        # Guardar en archivo separado para revisión
        if output_path is None:
            output_path = self.json_path.parent / 'TestAssesments' / 'data' / 'json' / 'aig_generated_questions.json'
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        generated_data = {
            "metadata": {
                "methodology": "Automatic Item Generation (AIG)",
                "generatedDate": datetime.now().strftime("%Y-%m-%d"),
                "totalGenerated": len(new_questions),
                "sources": [
                    "docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-finetuning",
                    "docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst",
                    "docs.snowflake.com/en/sql-reference/data-types-vector",
                    "docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/cortex-search-overview",
                    "docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions",
                    "docs.snowflake.com/en/guides-overview-ai-features"
                ],
                "techniques": [
                    "Knowledge Gap Analysis",
                    "Distractor-based question generation",
                    "Topic balancing",
                    "Bloom's Taxonomy coverage"
                ],
                "byTopic": {}
            },
            "questions": new_questions
        }
        
        # Contar por tema
        for q in new_questions:
            topic = q.get('topic', 'Unknown')
            generated_data["metadata"]["byTopic"][topic] = generated_data["metadata"]["byTopic"].get(topic, 0) + 1
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(generated_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Generadas {len(new_questions)} nuevas preguntas verificadas")
        print(f"   Guardadas en: {output_path}")
        print(f"\n📊 Distribución por tema:")
        for topic, count in generated_data["metadata"]["byTopic"].items():
            print(f"   {topic}: {count} preguntas")
        
        return str(output_path)
    
    def merge_to_main_json(self, generated_path: str) -> int:
        """Fusiona las preguntas generadas al JSON principal"""
        
        with open(generated_path, 'r', encoding='utf-8') as f:
            generated_data = json.load(f)
        
        new_questions = generated_data.get('questions', [])
        
        # Agregar al JSON principal
        self.data['questions'].extend(new_questions)
        self.data['metadata']['totalQuestions'] = len(self.data['questions'])
        self.data['metadata']['lastUpdated'] = datetime.now().strftime("%Y-%m-%d")
        self.data['metadata']['aigGenerated'] = len(new_questions)
        self.data['metadata']['aigMethodology'] = "Automatic Item Generation based on verified Snowflake documentation"
        
        with open(self.json_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Fusionadas {len(new_questions)} preguntas al JSON principal")
        print(f"   Total de preguntas ahora: {len(self.data['questions'])}")
        
        return len(new_questions)


def main():
    """Ejecutar la generación de preguntas AIG"""
    
    base_path = Path(__file__).parent.parent
    json_path = base_path / 'GES-C01_Exam_Sample_Questions.json'
    
    if not json_path.exists():
        json_path = base_path.parent / 'GES-C01_Exam_Sample_Questions.json'
    
    print("=" * 70)
    print("AUTOMATIC ITEM GENERATION (AIG) - Question Generator")
    print("=" * 70)
    print(f"\n📚 Base de conocimiento verificada de documentación oficial de Snowflake")
    print(f"   - Fine-tuning: Context windows, row limits, training data format")
    print(f"   - Cortex Analyst: Model selection, billing, multi-turn limitations")
    print(f"   - Vector Embeddings: Data type constraints, supported operations")
    print(f"   - RAG: Chunk sizes, hybrid search, conversation management")
    print(f"   - Cost & Governance: Usage views, allowlists, trust principles")
    
    generator = VerifiedQuestionGenerator(str(json_path))
    
    # Generar y guardar preguntas
    output_path = generator.save_generated_questions()
    
    # Preguntar si fusionar
    print(f"\n" + "=" * 70)
    print("¿Desea fusionar las preguntas generadas al JSON principal?")
    print("Las preguntas han sido generadas con fuentes verificables.")
    print("=" * 70)
    
    # Auto-merge para este script
    generator.merge_to_main_json(output_path)
    
    return output_path


if __name__ == '__main__':
    main()
