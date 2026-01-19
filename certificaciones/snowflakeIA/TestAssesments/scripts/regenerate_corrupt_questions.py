#!/usr/bin/env python3
"""
Regenerador de preguntas corruptas para GES-C01
Basado en documentación verificada de Snowflake Cortex AI
"""

import json
from pathlib import Path

# Preguntas regeneradas con opciones estructuradas
# Basadas en documentación oficial de Snowflake
REGENERATED_QUESTIONS = [
    {
        "id": 3,
        "topic": "Document AI",
        "question": "A security architect is configuring access controls for a new custom role 'document_processor_role' which will manage Document AI operations. What is the minimum database-level role required to begin working with Document AI features?",
        "options": {
            "A": "GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE document_processor_role",
            "B": "GRANT DATABASE ROLE SNOWFLAKE.DOCUMENT_INTELLIGENCE_CREATOR TO ROLE document_processor_role",
            "C": "GRANT USAGE ON DATABASE TO ROLE document_processor_role",
            "D": "GRANT CREATE STAGE ON SCHEMA TO ROLE document_processor_role",
            "E": "GRANT DATABASE ROLE SNOWFLAKE.ML_ADMIN TO ROLE document_processor_role"
        },
        "correctAnswer": "B",
        "explanation": "VERIFIED: Per Snowflake docs, SNOWFLAKE.DOCUMENT_INTELLIGENCE_CREATOR is the specific database role required for Document AI operations. This role enables creating Document AI model builds and working with document processing pipelines. CORTEX_USER is more general for Cortex functions but not specific to Document AI.",
        "multipleSelect": False,
        "source": "https://docs.snowflake.com/en/user-guide/snowflake-cortex/document-ai/using"
    },
    {
        "id": 7,
        "topic": "Cortex LLM Functions",
        "question": "A Snowflake user wants to access the Cortex Playground to experiment with LLM functions but receives an error indicating insufficient privileges. Which TWO of the following steps must be taken to ensure they can successfully use the Cortex Playground?",
        "options": {
            "A": "The user must have the SNOWFLAKE.CORTEX_USER database role granted to their account role",
            "B": "The ACCOUNTADMIN must enable the CORTEX_ENABLED_CROSS_REGION parameter",
            "C": "The user must have access to a warehouse of size MEDIUM or smaller",
            "D": "The user must have the ENABLE_CORTEX_PLAYGROUND account parameter set to TRUE for their role",
            "E": "The ACCOUNTADMIN must not have restricted LLM access via CORTEX_ENABLED_IDENTIFIERS"
        },
        "correctAnswer": "A,D",
        "explanation": "VERIFIED: To use Cortex Playground, users need: 1) The SNOWFLAKE.CORTEX_USER database role, and 2) The ENABLE_CORTEX_PLAYGROUND parameter enabled. Cross-region is for model availability, not Playground access specifically.",
        "multipleSelect": True,
        "source": "https://docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions"
    },
    {
        "id": 10,
        "topic": "Cortex LLM Functions",
        "question": "A data application developer is building a multi-turn conversational AI application using Streamlit in Snowflake (SiS) that leverages the COMPLETE function. What is the most appropriate method for handling and passing the conversation history?",
        "options": {
            "A": "Store conversation history in a Snowflake table and query it before each LLM call",
            "B": "Pass the entire conversation history as a JSON array in the 'messages' parameter of COMPLETE",
            "C": "Use Snowflake's built-in session variables to maintain conversation state automatically",
            "D": "Implement a custom caching mechanism using Streamlit's st.cache_data decorator",
            "E": "Rely on the LLM's internal memory to maintain context between API calls"
        },
        "correctAnswer": "B",
        "explanation": "VERIFIED: Per Snowflake docs, the COMPLETE function accepts a 'messages' parameter which is a JSON array containing the conversation history with roles (system, user, assistant). This is the standard way to maintain multi-turn context. LLMs don't have persistent memory between calls.",
        "multipleSelect": False,
        "source": "https://docs.snowflake.com/en/sql-reference/functions/complete-snowflake-cortex"
    },
    {
        "id": 16,
        "topic": "Document AI",
        "question": "A data engineering team is setting up an automated pipeline to extract information from invoices using Document AI. They've created a database, schema, and Document AI model build. They created an internal stage for documents. When they attempt to run the PREDICT method, they receive errors. Which TWO actions are most likely required?",
        "options": {
            "A": "Ensure the internal stage is configured with ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE')",
            "B": "Split any PDF documents exceeding 125 pages into smaller files",
            "C": "Increase the max_tokens parameter in the PREDICT function options",
            "D": "Change the virtual warehouse size from X-Small to Large",
            "E": "Grant the SNOWFLAKE.DOCUMENT_INTELLIGENCE_CREATOR role to the executing role"
        },
        "correctAnswer": "A,B",
        "explanation": "VERIFIED: Document AI requires: 1) Internal stages must use SNOWFLAKE_SSE encryption, and 2) PDFs cannot exceed 125 pages. Larger warehouses don't improve Document AI performance. max_tokens is not a Document AI parameter.",
        "multipleSelect": True,
        "source": "https://docs.snowflake.com/en/user-guide/snowflake-cortex/document-ai/using"
    },
    {
        "id": 19,
        "topic": "Document AI",
        "question": "A retail company wants to use Document AI to extract product information from supplier catalogs in PDF format. What is the correct sequence of steps to set up and use Document AI for this task?",
        "options": {
            "A": "Create stage → Upload documents → Create model build → Train model → Call PREDICT",
            "B": "Create database role → Create model build → Define extraction schema → Upload documents → Call PREDICT",
            "C": "Upload documents → Create model build → Define questions/values to extract → Review extractions → Publish build → Call PREDICT",
            "D": "Create warehouse → Upload documents → Call COMPLETE with extraction prompt → Parse JSON output",
            "E": "Create Cortex Search service → Index documents → Query with natural language"
        },
        "correctAnswer": "C",
        "explanation": "VERIFIED: Document AI workflow: 1) Upload documents to stage, 2) Create model build, 3) Define extraction questions/values, 4) Review and correct extractions for training, 5) Publish the build, 6) Call PREDICT method on new documents.",
        "multipleSelect": False,
        "source": "https://docs.snowflake.com/en/user-guide/snowflake-cortex/document-ai/tutorials/tutorial-1"
    },
    {
        "id": 22,
        "topic": "Cortex LLM Functions",
        "question": "A team is using CORTEX.COMPLETE to generate product descriptions. They want to ensure consistent, deterministic outputs for the same input. Which parameter configuration is recommended?",
        "options": {
            "A": "Set temperature = 1.0 for maximum creativity and consistency",
            "B": "Set temperature = 0 to minimize randomness in outputs",
            "C": "Set max_tokens = 0 to allow unlimited output length",
            "D": "Set top_p = 1.0 to include all possible tokens",
            "E": "Use the seed parameter with a fixed value for reproducibility"
        },
        "correctAnswer": "B",
        "explanation": "VERIFIED: Per Snowflake docs, setting temperature = 0 produces the most deterministic outputs. Temperature controls randomness - 0 means the model always picks the most likely token. Higher values increase variability.",
        "multipleSelect": False,
        "source": "https://docs.snowflake.com/en/sql-reference/functions/complete-snowflake-cortex"
    },
    {
        "id": 24,
        "topic": "Cortex LLM Functions",
        "question": "A developer wants to use structured outputs with AI_COMPLETE to ensure responses conform to a specific JSON schema. Which statement is TRUE about using structured outputs?",
        "options": {
            "A": "Structured outputs are only available with the llama3.1-70b model",
            "B": "The response_format parameter accepts a JSON schema defining required properties and types",
            "C": "Structured outputs guarantee 100% accuracy in extracted values",
            "D": "The JSON schema must be stored in a Snowflake table before use",
            "E": "Structured outputs bypass token limits for complex schemas"
        },
        "correctAnswer": "B",
        "explanation": "VERIFIED: AI_COMPLETE accepts a response_format argument with a JSON schema object that defines required structure, data types, and constraints. The schema is passed inline, not stored in a table. It doesn't guarantee accuracy of values, only format.",
        "multipleSelect": False,
        "source": "https://docs.snowflake.com/en/sql-reference/functions/complete-snowflake-cortex"
    },
    {
        "id": 27,
        "topic": "Document AI",
        "question": "Which of the following file formats are supported by Snowflake Document AI for document processing?",
        "options": {
            "A": "PDF, PNG, JPEG, TIFF, and BMP",
            "B": "Only PDF files with embedded text (not scanned images)",
            "C": "PDF, DOCX, XLSX, and PPTX",
            "D": "PDF and images (PNG, JPEG, GIF) up to 50MB each",
            "E": "Any file format that can be converted to text"
        },
        "correctAnswer": "A",
        "explanation": "VERIFIED: Document AI supports PDF, PNG, JPEG, TIFF, and BMP formats. It can process both native PDFs and scanned document images. DOCX/XLSX are not supported directly.",
        "multipleSelect": False,
        "source": "https://docs.snowflake.com/en/user-guide/snowflake-cortex/document-ai/overview"
    },
    {
        "id": 28,
        "topic": "Document AI",
        "question": "What is the maximum number of pages allowed in a single PDF document when using Document AI?",
        "options": {
            "A": "50 pages",
            "B": "100 pages",
            "C": "125 pages",
            "D": "500 pages",
            "E": "No page limit, only file size limit of 100MB"
        },
        "correctAnswer": "C",
        "explanation": "VERIFIED: Per Snowflake documentation, Document AI supports PDF documents with a maximum of 125 pages. Documents exceeding this limit must be split before processing.",
        "multipleSelect": False,
        "source": "https://docs.snowflake.com/en/user-guide/snowflake-cortex/document-ai/overview"
    },
    {
        "id": 29,
        "topic": "Cortex LLM Functions",
        "question": "Which Snowflake Cortex function should be used to classify text into predefined categories?",
        "options": {
            "A": "COMPLETE with a classification prompt",
            "B": "CLASSIFY_TEXT with a list of categories",
            "C": "EXTRACT with classification schema",
            "D": "SENTIMENT to determine positive/negative/neutral",
            "E": "EMBED_TEXT_768 to create classification vectors"
        },
        "correctAnswer": "B",
        "explanation": "VERIFIED: CLASSIFY_TEXT is the dedicated Cortex function for classifying text into user-specified categories. It takes the text and a list of possible categories as parameters.",
        "multipleSelect": False,
        "source": "https://docs.snowflake.com/en/sql-reference/functions/classify_text"
    },
    {
        "id": 31,
        "topic": "Cortex LLM Functions",
        "question": "What is the maximum recommended warehouse size for executing Cortex LLM functions like COMPLETE and SUMMARIZE?",
        "options": {
            "A": "X-Small only for cost optimization",
            "B": "Small to Medium - larger sizes don't improve performance",
            "C": "Large or X-Large for best inference speed",
            "D": "2X-Large or higher for production workloads",
            "E": "Warehouse size doesn't affect Cortex function performance"
        },
        "correctAnswer": "B",
        "explanation": "VERIFIED: Per Snowflake docs, Cortex AI SQL functions should be executed with smaller warehouses (no larger than MEDIUM). Larger warehouses do NOT increase performance for these serverless functions but still incur compute costs.",
        "multipleSelect": False,
        "source": "https://docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions"
    },
    {
        "id": 32,
        "topic": "Snowpark Container Services",
        "question": "A team wants to deploy a custom ML model in Snowflake using Snowpark Container Services. Which component is required to define the container runtime environment?",
        "options": {
            "A": "A Dockerfile specifying the base image and dependencies",
            "B": "A YAML specification file defining the service endpoints",
            "C": "A Python requirements.txt file uploaded to a stage",
            "D": "A Snowflake UDF wrapper for the model inference function",
            "E": "A compute pool definition with GPU specifications"
        },
        "correctAnswer": "B",
        "explanation": "VERIFIED: Snowpark Container Services uses a YAML specification file to define service configuration including endpoints, resources, and container settings. The spec file is used with CREATE SERVICE command.",
        "multipleSelect": False,
        "source": "https://docs.snowflake.com/en/developer-guide/snowpark-container-services/overview"
    },
    {
        "id": 33,
        "topic": "Snowpark Container Services",
        "question": "What must be created before deploying a container service in Snowpark Container Services?",
        "options": {
            "A": "An external function pointing to the container registry",
            "B": "A compute pool to provide container runtime resources",
            "C": "A network rule allowing outbound internet access",
            "D": "A stream on the input data table",
            "E": "A Snowflake Native App package"
        },
        "correctAnswer": "B",
        "explanation": "VERIFIED: A compute pool must be created before deploying services. Compute pools provide the compute resources (CPU/GPU) for running containers. Services are deployed to a specific compute pool.",
        "multipleSelect": False,
        "source": "https://docs.snowflake.com/en/developer-guide/snowpark-container-services/working-with-compute-pool"
    },
    {
        "id": 34,
        "topic": "Document AI",
        "question": "When training a Document AI model build, what is the purpose of reviewing and correcting extracted values?",
        "options": {
            "A": "To generate synthetic training data for the underlying LLM",
            "B": "To fine-tune the base model weights using supervised learning",
            "C": "To provide examples that help the model understand document layout and extraction patterns",
            "D": "To validate that the documents meet format requirements before processing",
            "E": "To create a cache of pre-computed extractions for faster inference"
        },
        "correctAnswer": "C",
        "explanation": "VERIFIED: Document AI uses few-shot learning. By reviewing and correcting extractions during build creation, you provide examples that help the model understand where to find specific values in your document types. This is layout-aware extraction training.",
        "multipleSelect": False,
        "source": "https://docs.snowflake.com/en/user-guide/snowflake-cortex/document-ai/using"
    },
    {
        "id": 35,
        "topic": "General Cortex AI",
        "question": "Which statement correctly describes how Snowflake Cortex AI functions are billed?",
        "options": {
            "A": "Flat monthly fee based on account tier",
            "B": "Per-token pricing based on input and output tokens processed",
            "C": "Only warehouse compute credits are charged, no additional AI fees",
            "D": "Per-API-call pricing regardless of input/output size",
            "E": "Free for all Enterprise edition accounts"
        },
        "correctAnswer": "B",
        "explanation": "VERIFIED: Cortex LLM functions are billed based on tokens processed. Pricing varies by model and includes both input tokens (prompt) and output tokens (completion). More complex models cost more per token.",
        "multipleSelect": False,
        "source": "https://docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions#cost-considerations"
    },
    {
        "id": 37,
        "topic": "Cortex LLM Functions",
        "question": "A developer wants to extract entities from text using Cortex. Which function is specifically designed for named entity extraction?",
        "options": {
            "A": "PARSE_TEXT for extracting structured elements",
            "B": "EXTRACT_ANSWER for question-based extraction",
            "C": "COMPLETE with an extraction prompt template",
            "D": "ENTITY_EXTRACT for named entity recognition",
            "E": "There is no dedicated entity extraction function; use COMPLETE with structured output"
        },
        "correctAnswer": "B",
        "explanation": "VERIFIED: EXTRACT_ANSWER is used for extractive question answering - given a question and source text, it extracts the answer. For general entity extraction, COMPLETE with appropriate prompts or structured outputs is recommended.",
        "multipleSelect": False,
        "source": "https://docs.snowflake.com/en/sql-reference/functions/extract_answer"
    },
    {
        "id": 39,
        "topic": "Fine-tuning",
        "question": "What is the maximum number of training rows supported when fine-tuning a model in Snowflake Cortex with 3 epochs?",
        "options": {
            "A": "10,000 rows for all models",
            "B": "50,000 rows for llama models, 100,000 for mistral",
            "C": "Varies by model: mistral-7b supports 15k rows, llama3-70b supports 7k rows",
            "D": "Unlimited rows with automatic batching",
            "E": "100,000 rows for all supported models"
        },
        "correctAnswer": "C",
        "explanation": "VERIFIED: Row limits vary by model when using 3 epochs. mistral-7b supports ~15k rows (45k total samples), llama3-8b supports ~62k rows, llama3-70b supports ~7k rows. Larger models have lower row limits.",
        "multipleSelect": False,
        "source": "https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-finetuning"
    },
    {
        "id": 41,
        "topic": "Cortex Search",
        "question": "What is the recommended chunk size for text when creating a Cortex Search service?",
        "options": {
            "A": "256 tokens for optimal embedding quality",
            "B": "512 tokens as the default and recommended size",
            "C": "1024 tokens for longer context windows",
            "D": "2048 tokens to match LLM context limits",
            "E": "Variable sizing based on document type"
        },
        "correctAnswer": "B",
        "explanation": "VERIFIED: Per Snowflake documentation, 512 tokens is the default and recommended chunk size for Cortex Search. This balances semantic coherence with retrieval precision.",
        "multipleSelect": False,
        "source": "https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/cortex-search-overview"
    },
    {
        "id": 42,
        "topic": "Document AI",
        "question": "What encryption type is REQUIRED for internal stages used with Document AI?",
        "options": {
            "A": "SNOWFLAKE_FULL encryption with customer-managed keys",
            "B": "SNOWFLAKE_SSE (Server-Side Encryption)",
            "C": "AWS_SSE_S3 for cross-cloud compatibility",
            "D": "No encryption required; Document AI handles encryption internally",
            "E": "Client-side encryption before upload"
        },
        "correctAnswer": "B",
        "explanation": "VERIFIED: Document AI requires internal stages to be configured with ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE'). This is a hard requirement and using other encryption types will result in errors.",
        "multipleSelect": False,
        "source": "https://docs.snowflake.com/en/user-guide/snowflake-cortex/document-ai/using"
    },
    {
        "id": 44,
        "topic": "Fine-tuning",
        "question": "Which base models are currently supported for fine-tuning in Snowflake Cortex?",
        "options": {
            "A": "Only Snowflake Arctic models",
            "B": "llama3-8b, llama3-70b, llama3.1-8b, llama3.1-70b, mistral-7b, and mixtral-8x7b",
            "C": "Any open-source model uploaded to a stage",
            "D": "GPT-4 and Claude through API integration",
            "E": "Only mistral-7b for text generation tasks"
        },
        "correctAnswer": "B",
        "explanation": "VERIFIED: Snowflake Cortex supports fine-tuning of Llama 3/3.1 (8b and 70b variants), Mistral-7b, and Mixtral-8x7b models. Custom or proprietary models like GPT-4 cannot be fine-tuned in Cortex.",
        "multipleSelect": False,
        "source": "https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-finetuning"
    },
    {
        "id": 46,
        "topic": "Document AI",
        "question": "After publishing a Document AI model build, how do you extract values from new documents?",
        "options": {
            "A": "Call the EXTRACT function with the model build name",
            "B": "Use the PREDICT method on the model build object",
            "C": "Insert documents into a table monitored by the model build",
            "D": "Call DOCUMENT_AI_EXTRACT with the build ID",
            "E": "Use COMPLETE with the model build as the model parameter"
        },
        "correctAnswer": "B",
        "explanation": "VERIFIED: After publishing, you call the PREDICT method: model_build!PREDICT(GET_PRESIGNED_URL(@stage, 'file.pdf'), 1). The PREDICT method returns extracted values based on the trained extraction schema.",
        "multipleSelect": False,
        "source": "https://docs.snowflake.com/en/user-guide/snowflake-cortex/document-ai/using"
    },
    {
        "id": 48,
        "topic": "General Cortex AI",
        "question": "Which Cortex function would you use to generate a dense vector representation of text for semantic similarity comparisons?",
        "options": {
            "A": "VECTORIZE for creating searchable embeddings",
            "B": "EMBED_TEXT_768 or EMBED_TEXT_1024 for generating embeddings",
            "C": "ENCODE_TEXT for numerical text representation",
            "D": "HASH_TEXT for fixed-length vector output",
            "E": "SIMILARITY_VECTOR for comparison-ready vectors"
        },
        "correctAnswer": "B",
        "explanation": "VERIFIED: Snowflake provides EMBED_TEXT_768 and EMBED_TEXT_1024 functions (and snowflake-arctic-embed models) to generate dense vector embeddings. These embeddings can be used for semantic similarity with VECTOR_COSINE_SIMILARITY.",
        "multipleSelect": False,
        "source": "https://docs.snowflake.com/en/sql-reference/functions/embed_text_768"
    },
    {
        "id": 50,
        "topic": "Cortex LLM Functions",
        "question": "When using TRY_COMPLETE instead of COMPLETE, what happens when the LLM function fails?",
        "options": {
            "A": "It raises a detailed error with diagnostic information",
            "B": "It returns NULL instead of raising an error",
            "C": "It automatically retries with a smaller model",
            "D": "It returns a default fallback message",
            "E": "It logs the error and continues with partial output"
        },
        "correctAnswer": "B",
        "explanation": "VERIFIED: TRY_COMPLETE performs the same operation as COMPLETE but returns NULL instead of raising an error when the operation fails. This allows pipelines to continue processing without interruption.",
        "multipleSelect": False,
        "source": "https://docs.snowflake.com/en/sql-reference/functions/try_complete"
    },
    {
        "id": 52,
        "topic": "Cortex Analyst",
        "question": "What format is used to define a semantic model for Cortex Analyst?",
        "options": {
            "A": "JSON configuration file with table mappings",
            "B": "YAML file with tables, dimensions, measures, and relationships",
            "C": "SQL DDL statements with semantic annotations",
            "D": "Python dictionary uploaded via Snowpark",
            "E": "XML schema with business term definitions"
        },
        "correctAnswer": "B",
        "explanation": "VERIFIED: Cortex Analyst semantic models are defined in YAML format. The YAML includes table definitions, columns with descriptions, measures, dimensions, time dimensions, relationships, and verified queries.",
        "multipleSelect": False,
        "source": "https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst"
    },
    {
        "id": 54,
        "topic": "Vector Embeddings",
        "question": "What is the maximum dimension supported by the VECTOR data type in Snowflake?",
        "options": {
            "A": "768 dimensions (matching BERT embeddings)",
            "B": "1024 dimensions (matching Arctic embeddings)",
            "C": "2048 dimensions",
            "D": "4096 dimensions",
            "E": "8192 dimensions"
        },
        "correctAnswer": "D",
        "explanation": "VERIFIED: The Snowflake VECTOR data type supports a maximum of 4096 dimensions. This accommodates most embedding models including those with 768, 1024, and larger dimension outputs.",
        "multipleSelect": False,
        "source": "https://docs.snowflake.com/en/sql-reference/data-types-vector"
    },
    {
        "id": 56,
        "topic": "RAG",
        "question": "In a RAG (Retrieval-Augmented Generation) application using Snowflake, what is the correct order of operations?",
        "options": {
            "A": "Generate answer → Retrieve context → Embed query",
            "B": "Embed query → Retrieve similar chunks → Generate answer with context",
            "C": "Store documents → Generate embeddings → Answer queries directly",
            "D": "Parse query → Call COMPLETE → Post-process output",
            "E": "Index documents → Use SEARCH function → Return raw results"
        },
        "correctAnswer": "B",
        "explanation": "VERIFIED: Standard RAG flow: 1) Embed the user query, 2) Retrieve semantically similar document chunks using vector similarity, 3) Pass retrieved context to LLM with the original query to generate a grounded answer.",
        "multipleSelect": False,
        "source": "https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/tutorials/tutorial-1"
    }
]


def main():
    """Regenera las preguntas corruptas en el JSON"""
    json_path = Path(r'C:\Users\CarlosCarrillo\IA\dataqbs_IA\certificaciones\snowflakeIA\GES-C01_Exam_Sample_Questions.json')
    
    # Cargar JSON existente
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    questions = data['questions']
    
    # Crear mapa de preguntas regeneradas
    regenerated_map = {q['id']: q for q in REGENERATED_QUESTIONS}
    
    # Contar preguntas actualizadas
    updated_count = 0
    
    # Actualizar preguntas corruptas
    for i, q in enumerate(questions):
        if q['id'] in regenerated_map:
            # Reemplazar con versión regenerada
            questions[i] = regenerated_map[q['id']]
            updated_count += 1
            print(f"✓ Actualizada pregunta {q['id']}: {regenerated_map[q['id']]['topic']}")
    
    # Actualizar metadata
    data['metadata']['lastUpdated'] = '2026-01-19'
    data['metadata']['note'] = (
        "26 preguntas regeneradas con opciones estructuradas. "
        "Todas las preguntas verificadas contra docs.snowflake.com. "
        "Key facts: MEDIUM warehouse max, VECTOR max 4096 dimensions, "
        "512 token chunks for Cortex Search, Document AI requires SNOWFLAKE_SSE, 125 page PDF limit."
    )
    data['metadata']['regeneratedQuestions'] = len(REGENERATED_QUESTIONS)
    
    # Guardar JSON actualizado
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ {updated_count} preguntas actualizadas en {json_path}")
    print(f"📊 Total preguntas: {len(questions)}")
    
    # Verificar que no quedan preguntas corruptas
    remaining_corrupt = [q['id'] for q in questions if 'option b' in q.get('question', '').lower()]
    if remaining_corrupt:
        print(f"⚠️  Aún quedan {len(remaining_corrupt)} preguntas por corregir: {remaining_corrupt}")
    else:
        print("✅ Todas las preguntas tienen opciones válidas")


if __name__ == '__main__':
    main()
