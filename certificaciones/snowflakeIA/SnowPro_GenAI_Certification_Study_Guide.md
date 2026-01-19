# SnowPro® Specialty: Gen AI (GES-C01) - Complete Study Guide

## 📋 Certification Overview

The **SnowPro® Specialty: Gen AI Certification Exam** validates specialized knowledge, skills, and best practices for leveraging Gen AI methodologies in Snowflake, including key concepts, features, and programming constructs.

### Exam Details
| Attribute | Details |
|-----------|---------|
| **Exam Code** | GES-C01 |
| **Cost** | $375 USD per attempt |
| **Format** | Multiple choice / Multiple select |
| **Duration** | 115 minutes |
| **Passing Score** | ~750/1000 (estimated) |
| **Prerequisites** | 1+ years of Gen AI experience with Snowflake in enterprise environments |

### Target Candidate Profile
- Experience writing code in Python
- Previous data engineering and SQL knowledge
- Familiarity with LLM concepts and architectures
- Hands-on experience with Snowflake Cortex AI features

---

## 🎯 What This Certification Tests

1. **Define and implement Snowflake Gen AI principles, capabilities, and best practices**
2. **Leverage Snowflake Cortex AI features, LLMs, and offerings to meet customer use cases**
3. **Build open-source models with Snowpark Container Services and Snowflake Model Registry**
4. **Use Document AI to train and troubleshoot models specific to customer use cases**

---

## 📚 Domain 1: Snowflake Cortex AI Functions (LLM Functions)

### 1.1 Core AI Functions

Snowflake Cortex AI provides SQL functions and Python APIs for unstructured analytics on text and images with industry-leading LLMs from OpenAI, Anthropic, Meta, Mistral AI, and DeepSeek.

#### Primary Cortex AI Functions

| Function | Description | Use Case |
|----------|-------------|----------|
| **AI_COMPLETE** | Generates completions for text/image using selected LLM | General generative AI tasks, chat completions |
| **AI_CLASSIFY** | Classifies text/images into user-defined categories | Text categorization, content classification |
| **AI_FILTER** | Returns True/False for text/image input | Filtering results in SELECT/WHERE/JOIN |
| **AI_AGG** | Aggregates text column with natural language instructions | Summarizing grouped data |
| **AI_EMBED** | Generates embedding vectors for text/images | Similarity search, clustering |
| **AI_EXTRACT** | Extracts information from strings/files/documents | Entity extraction, data parsing |
| **AI_SENTIMENT** | Extracts sentiment from text (-1 to 1 score) | Customer feedback analysis |
| **AI_SUMMARIZE_AGG** | Aggregates text column and returns summary | Multi-row summarization |
| **AI_SIMILARITY** | Calculates embedding similarity between inputs | Finding similar documents |
| **AI_TRANSCRIBE** | Transcribes audio/video files | Speech-to-text |
| **AI_PARSE_DOCUMENT** | Extracts text/layout from documents | OCR, document processing |
| **AI_REDACT** | Redacts PII from text | Privacy compliance |
| **AI_TRANSLATE** | Translates text between languages | Localization |

#### Legacy Functions (Still Supported)
```sql
-- These SNOWFLAKE.CORTEX.* functions are still available
SNOWFLAKE.CORTEX.COMPLETE()
SNOWFLAKE.CORTEX.SENTIMENT()
SNOWFLAKE.CORTEX.SUMMARIZE()
SNOWFLAKE.CORTEX.TRANSLATE()
SNOWFLAKE.CORTEX.CLASSIFY_TEXT()
SNOWFLAKE.CORTEX.EXTRACT_ANSWER()
SNOWFLAKE.CORTEX.EMBED_TEXT_768()
SNOWFLAKE.CORTEX.EMBED_TEXT_1024()
```

### 1.2 Helper Functions

| Function | Description |
|----------|-------------|
| **AI_COUNT_TOKENS** | Returns token count for input text based on model |
| **TO_FILE** | Creates reference to file in stage for AI functions |
| **PROMPT** | Builds prompt objects for AI_COMPLETE |
| **TRY_COMPLETE** | Like COMPLETE but returns NULL on error instead of error code |

### 1.3 Cortex Guard

Cortex Guard filters unsafe/harmful responses using Meta's Llama Guard 3:

```sql
SELECT AI_COMPLETE(
    'llama3.1-405b',
    [
        {'role': 'user', 'content': 'Your question here'}
    ],
    {'guardrails': True}  -- Enable Cortex Guard
);
```

**Key Points:**
- Filters violent crimes, hate, sexual content, self-harm
- Incurs additional compute charges based on input tokens
- Works by evaluating responses before returning to application

### 1.4 Model Selection Guide

#### Large Models (Complex Tasks)
| Model | Context Window | Best For |
|-------|---------------|----------|
| claude-3-7-sonnet | 200,000 | General reasoning, multimodal, agentic workflows |
| mistral-large2 | 128,000 | Code generation, mathematics, multilingual |
| llama3.1-405b | 128,000 | Long document processing, synthetic data generation |
| deepseek-r1 | 32,768 | Math, code, reasoning tasks |

#### Medium Models (Balanced Performance)
| Model | Context Window | Best For |
|-------|---------------|----------|
| llama3.1-70b | 128,000 | Chat apps, content creation, enterprise apps |
| snowflake-llama3.3-70b | 128,000 | SwiftKV optimized - 75% lower inference cost |
| snowflake-arctic | 4,096 | SQL generation, coding, enterprise tasks |
| mixtral-8x7b | 32,000 | Text generation, classification, Q&A |

#### Small Models (Fast, Simple Tasks)
| Model | Context Window | Best For |
|-------|---------------|----------|
| llama3.1-8b | 128,000 | Low-moderate reasoning, ultra-fast |
| mistral-7b | 32,000 | Simple summarization, quick Q&A |

### 1.5 Key Configuration Options

```python
options = {
    'temperature': 0.7,      # Creativity (0-1)
    'top_p': 0.9,            # Nucleus sampling
    'max_tokens': 100,       # Max output length
    'guardrails': True       # Enable safety filtering
}
```

### 1.6 Multi-turn Conversations

```python
messages = [
    {'role': 'system', 'content': 'You are a helpful assistant.'},
    {'role': 'user', 'content': 'First question'},
    {'role': 'assistant', 'content': 'First response'},
    {'role': 'user', 'content': 'Follow-up question'}
]

response = Complete("llama3.1-405b", messages, options={'guardrails': True})
```

### 1.7 Access Control

```sql
-- CORTEX_USER role is granted to PUBLIC by default
-- To restrict access:
REVOKE DATABASE ROLE SNOWFLAKE.CORTEX_USER FROM ROLE PUBLIC;

-- Grant to specific role:
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE analyst;

-- Control model access via allowlist:
ALTER ACCOUNT SET CORTEX_MODELS_ALLOWLIST = 'mistral-large2,llama3.1-70b';
```

---

## 📚 Domain 2: Cortex Search (RAG)

### 2.1 Overview

Cortex Search enables low-latency, high-quality hybrid search (vector + keyword) for RAG applications.

### 2.2 Creating a Cortex Search Service

```sql
CREATE OR REPLACE CORTEX SEARCH SERVICE transcript_search_service
  ON transcript_text                    -- Column to search
  ATTRIBUTES region                     -- Filter columns
  WAREHOUSE = cortex_search_wh          -- Refresh warehouse
  TARGET_LAG = '1 day'                  -- Refresh frequency
  EMBEDDING_MODEL = 'snowflake-arctic-embed-l-v2.0'
  AS (
    SELECT transcript_text, region, agent_id
    FROM support_transcripts
);
```

### 2.3 Embedding Models for Cortex Search

| Model | Dimensions | Context | Language | Credits/1M tokens |
|-------|-----------|---------|----------|-------------------|
| snowflake-arctic-embed-m-v1.5 (default) | 768 | 512 | English-only | 0.03 |
| snowflake-arctic-embed-l-v2.0 | 1024 | 512 | Multilingual | 0.05 |
| snowflake-arctic-embed-l-v2.0-8k | 1024 | 8192 | Multilingual | 0.05 |
| voyage-multilingual-2 | 1024 | 32,000 | Multilingual | 0.07 |

### 2.4 Querying Cortex Search

```python
from snowflake.core import Root

root = Root(session)
search_service = (root
    .databases["db"]
    .schemas["schema"]
    .cortex_search_services["service_name"]
)

resp = search_service.search(
    query="internet issues",
    columns=["transcript_text", "region"],
    filter={"@eq": {"region": "North America"}},
    limit=5
)
```

### 2.5 Key Concepts

- **Hybrid Search**: Combines vector (semantic) and keyword (lexical) search
- **Semantic Reranking**: Reranks results for relevance
- **TARGET_LAG**: Controls refresh frequency (minimum: near-real-time)
- **Chunk Size**: Recommended 512 tokens for optimal quality

---

## 📚 Domain 3: Cortex Fine-Tuning

### 3.1 Overview

Fine-tuning allows customizing LLMs for domain-specific tasks using PEFT (Parameter-Efficient Fine-Tuning).

### 3.2 Available Base Models for Fine-Tuning

| Model | Row Limit (3 epochs) | Best For |
|-------|---------------------|----------|
| llama3-8b | 62k | Low-moderate reasoning |
| llama3-70b | 7k | Chat, content creation |
| llama3.1-8b | 50k | Fast inference |
| llama3.1-70b | 4.5k | Enterprise applications |
| mistral-7b | 15k | Simple tasks, high throughput |
| mixtral-8x7b | 9k | Text generation, classification |

### 3.3 Fine-Tuning Workflow

```sql
-- 1. Prepare training data with 'prompt' and 'completion' columns
-- 2. Create fine-tuning job
SELECT SNOWFLAKE.CORTEX.FINETUNE(
    'CREATE',
    'my_tuned_model',
    'mistral-7b',
    'SELECT prompt, completion FROM my_training_data',
    'SELECT prompt, completion FROM my_validation_data'
);

-- 3. Monitor job status
SELECT SNOWFLAKE.CORTEX.FINETUNE('SHOW');
SELECT SNOWFLAKE.CORTEX.FINETUNE('DESCRIBE', 'job_id');

-- 4. Use fine-tuned model
SELECT SNOWFLAKE.CORTEX.COMPLETE('my_tuned_model', 'Your prompt here');
```

### 3.4 Training Data Requirements

- Start with a few hundred examples
- Prompt + Completion must fit within context window:
  - mistral-7b: 28k prompt + 4k completion
  - llama3.1-70b: 6k prompt + 2k completion
- Use structured outputs for schema-defined responses

### 3.5 Access Control

```sql
-- Grant CREATE MODEL privilege
GRANT CREATE MODEL ON SCHEMA my_schema TO ROLE my_role;

-- Grant SNOWFLAKE.CORTEX_USER database role
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE my_role;
```

---

## 📚 Domain 4: Vector Embeddings & Similarity Search

### 4.1 VECTOR Data Type

```sql
-- Define vector columns
VECTOR(FLOAT, 256)  -- 256-dimensional float vector
VECTOR(INT, 16)     -- 16-dimensional integer vector

-- Maximum dimension: 4096
```

### 4.2 Creating and Using Embeddings

```sql
-- Create embeddings
ALTER TABLE myissues ADD COLUMN issue_vec VECTOR(FLOAT, 768);

UPDATE myissues
SET issue_vec = SNOWFLAKE.CORTEX.EMBED_TEXT_768('e5-base-v2', issue_text);

-- Similarity search
SELECT *,
    VECTOR_COSINE_SIMILARITY(query_vec, issue_vec) as similarity
FROM myissues
ORDER BY similarity DESC
LIMIT 10;
```

### 4.3 Embedding Models

| Function | Model Options | Dimensions |
|----------|--------------|------------|
| EMBED_TEXT_768 | e5-base-v2, snowflake-arctic-embed-m | 768 |
| EMBED_TEXT_1024 | multilingual-e5-large, voyage-multilingual-2 | 1024 |
| AI_EMBED | Multiple models | Varies |

### 4.4 Vector Functions

- `VECTOR_COSINE_SIMILARITY(v1, v2)` - Cosine similarity (-1 to 1)
- `VECTOR_INNER_PRODUCT(v1, v2)` - Dot product
- `VECTOR_L2_DISTANCE(v1, v2)` - Euclidean distance

---

## 📚 Domain 5: Snowpark Container Services & Model Registry

### 5.1 Model Registry

Store and manage ML models in Snowflake:

```python
from snowflake.ml.registry import Registry

# Create registry
registry = Registry(session)

# Log model
model = registry.log_model(
    model=my_model,
    model_name="my_model",
    version_name="v1"
)

# Deploy for inference
model.deploy(
    stage_name="@model_stage",
    target_warehouse="MODEL_WH"
)
```

### 5.2 Snowpark Container Services

Run custom containers in Snowflake for:
- Open-source models
- Custom inference services
- GPU workloads

---

## 📚 Domain 6: Cost Management & Best Practices

### 6.1 Token-Based Billing

- **AI_COMPLETE**: Input + Output tokens billed
- **AI_EMBED**: Input tokens only
- **Cortex Guard**: Additional input tokens
- **AI_PARSE_DOCUMENT**: Pages processed

### 6.2 Warehouse Sizing

**Important**: Use warehouse size **no larger than MEDIUM** for Cortex AI Functions - larger warehouses do NOT increase performance.

### 6.3 Track Costs

```sql
-- AI Services daily consumption
SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_DAILY_HISTORY
WHERE SERVICE_TYPE = 'AI_SERVICES';

-- Per-query token consumption
SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_FUNCTIONS_QUERY_USAGE_HISTORY;

-- Fine-tuning costs
SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_FINE_TUNING_USAGE_HISTORY;
```

---

## 📚 Domain 7: Python Integration

### 7.1 Snowpark Python API

```python
from snowflake.snowpark.functions import ai_complete, ai_classify, ai_filter, col

# AI Complete
df = df.select(
    ai_complete("llama3.1-8b", col("prompt")).alias("response")
)

# AI Classify
df = df.select(
    ai_classify(col("text"), ["category1", "category2"]).alias("class")
)

# AI Filter
df = df.filter(ai_filter(prompt("Is {0} in Asia?", col("country"))))
```

### 7.2 Snowflake ML Python

```python
from snowflake.cortex import complete, sentiment, summarize, translate

# Process single values
print(complete("llama3.1-8b", "Your prompt"))
print(sentiment("Great product!"))
print(summarize(long_text))
print(translate(text, "en", "fr"))

# With options
from snowflake.cortex import CompleteOptions

options = CompleteOptions({'max_tokens': 30})
response = complete("llama3.1-8b", "Your prompt", options=options)
```

---

## 🔑 Key Exam Tips

### Must-Know Facts

1. **Warehouse Size**: Always use MEDIUM or smaller for Cortex AI Functions
2. **Context Windows**: Know the limits for each model (e.g., llama3.1-405b = 128k)
3. **CORTEX_USER Role**: Granted to PUBLIC by default
4. **Cortex Guard**: Uses Llama Guard 3 for content filtering
5. **Fine-tuning**: Requires prompt + completion columns
6. **Cortex Search**: Hybrid search = vector + keyword + reranking
7. **TARGET_LAG**: Controls refresh frequency for Cortex Search
8. **VECTOR max dimension**: 4096

### Common Patterns

```sql
-- Sentiment Analysis
SELECT text, SNOWFLAKE.CORTEX.SENTIMENT(text) as score FROM reviews;

-- Translation with auto-detect
SELECT SNOWFLAKE.CORTEX.TRANSLATE(text, '', 'en') as english_text FROM docs;

-- Classification with examples
SELECT SNOWFLAKE.CORTEX.CLASSIFY_TEXT(
    text,
    [
        {'label': 'Category1', 'description': '...', 'examples': [...]},
        {'label': 'Category2', 'description': '...', 'examples': [...]}
    ]
) FROM support_tickets;

-- Token counting before API call
SELECT SNOWFLAKE.CORTEX.COUNT_TOKENS('llama3.1-70b', text) as tokens FROM docs;
```

---

## 📖 Study Resources

1. **Official Documentation**:
   - [Cortex AI Functions](https://docs.snowflake.com/en/user-guide/snowflake-cortex/aisql)
   - [Cortex Search](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/cortex-search-overview)
   - [Cortex Fine-tuning](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-finetuning)

2. **Hands-On Practice**:
   - Complete the notebooks in this repository
   - Use the Cortex Playground in Snowsight
   - Build a RAG application with Cortex Search

3. **Coursera/LinkedIn Learning**:
   - "Introduction to Generative AI with Snowflake" course

---

## 📁 Repository Contents

This repository (`generativeai-with-snowflake`) contains practical examples:

| Module | Content |
|--------|---------|
| **module-1** | Call transcript analysis with Cortex AI functions |
| **module-2** | Advanced LLM functions, Streamlit apps |
| **module-3** | Fine-tuning Mistral-7b, support ticket automation |
| **additional-demos** | Medical notes extraction |

---

*Last Updated: January 2026*
*Exam Version: GES-C01*
