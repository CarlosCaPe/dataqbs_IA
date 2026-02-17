## Plan: dataqbs.com Portfolio + Chatbot RAG

### Objetivo

Reemplazar el WordPress actual en dataqbs.com por un sitio estilo LinkedIn, con tu CV al centro y un chatbot RAG que responde sobre tu perfil usando como conocimiento:

- Tu CV (PDF en `/home/carloscarrillo/Downloads/Profile*.pdf`)
- Foto de perfil (`/home/carloscarrillo/Downloads/yo.jpeg`)
- READMEs y docs relevantes de tus repos de GitHub (empezando por `CarlosCaPe/dataqbs_IA`)
- Tus certificaciones (Azure, Snowflake GenAI, Azure Data, MCSA SQL)

Todo hospedado como sitio estático moderno, con RAG en el cliente y LLM externo gratuito, apuntando el dominio `www.dataqbs.com` al nuevo sitio.

---

### 1. Stack Técnico

- **Frontend**: Astro + Svelte (islas interactivas, SSG, soporte sencillo de dark/light mode)
- **Layout**: Estilo LinkedIn
  - Columna izquierda: tarjeta de perfil (foto, headline, certificaciones)
  - Columna central: timeline de experiencia (CV expandible)
  - Columna derecha: chatbot fijo (drawer en mobile)
- **RAG**:
  - Embeddings: `all-MiniLM-L6-v2` (384 dims) u otro modelo ligero compatible con uso en navegador o precomputado
  - Vector store: LanceDB (WASM) o alternativa similar para búsqueda vectorial en el navegador
  - Retrieval: cosine similarity (top-k, p.ej. k=5) con posible MMR para diversidad
  - LLM: Groq API (Llama 3.1 70B) u otro modelo gratuito de alta calidad
- **Conocimiento**:
  - CV parseado a JSON (experiencia, skills, educación)
  - Certificaciones a JSON
  - READMEs de GitHub y docs seleccionados
- **i18n**:
  - Idiomas: ES, EN, DE
  - Idioma por defecto: `navigator.language` → `es` / `en` / `de`; si no es uno de estos tres, usar EN
- **Seguridad / Anti-bot**:
  - Cloudflare Turnstile como CAPTCHA invisible antes del primer mensaje de chat
  - Rate limiting básico por sesión (ej. 10 mensajes/minuto)
  - Sanitización de inputs y bloqueo de URLs/inputs potencialmente maliciosos
- **Hosting**:
  - Cloudflare Pages (gratis, CDN global) para el sitio estático
  - DNS en Hostinger apuntando `www.dataqbs.com` a Cloudflare Pages
  - WordPress actual de Hostinger se reemplaza como front principal (opcionalmente relegado a subdominio si se desea conservar)
- **CI/CD y sincronización de conocimiento**:
  - GitHub Actions para build y deploy a Cloudflare Pages
  - Workflow de reindexación cuando cambien READMEs (`**/README.md`) u otros docs clave

---

### 2. Modelo Semántico (semantic_model.yaml)

Definir un modelo semántico en YAML para estructurar el conocimiento:

```yaml
entities:
  - name: Experience
    attributes:
      - company: string
      - role: string
      - period: daterange
      - skills: list[string]
      - achievements: list[string]
    relationships:
      - uses: Technology
      - certified_by: Certification

  - name: Technology
    attributes:
      - name: string
      - category: enum[database, cloud, language, tool]
      - proficiency: enum[expert, advanced, intermediate]

  - name: Project
    attributes:
      - name: string
      - description: string
      - technologies: list[Technology]
      - github_path: string

  - name: Certification
    attributes:
      - name: string
      - issuer: string
      - year: int

query_expansion:
  "Snowflake":
    - "data warehouse"
    - "cloud analytics"
    - "SQL optimization"
  "Azure":
    - "Microsoft cloud"
    - "Azure SQL"
    - "Azure Data Factory"
```

Usos del modelo semántico:

- Guiar el chunking semántico (respetar límites por experiencia/proyecto)
- Enriquecer queries del usuario (query expansion)
- Facilitar filtros futuros (p.ej. "solo experiencia como Data Engineer")

---

### 3. Pipeline de Conocimiento y Embeddings

#### 3.1. Fuentes de conocimiento

- CV (PDF) → extracción a texto → estructura JSON (`cv.json`)
- Certificaciones → JSON (`certs.json`)
- READMEs y docs de GitHub:
  - `README.md` del monorepo
  - `projects/arbitraje/README.md`
  - `projects/oai_code_evaluator/README.md`
  - `projects/supplier_verifier/README.md`
  - `projects/real_estate/README.md`
  - `projects/tls_compara_imagenes/README.md`
  - Otros repos relevantes en GitHub (a futuro)

#### 3.2. Chunking

- Usar un splitter tipo `RecursiveCharacterTextSplitter` o similar:
  - `chunk_size` ~ 512 tokens
  - `chunk_overlap` ~ 50 tokens
- Respetar en lo posible entidades lógicas (por job, por sección de README, etc.)

#### 3.3. Embeddings

- Modelo: `all-MiniLM-L6-v2` u otro modelo pequeño multi-idioma
- Generar embeddings para cada chunk de texto
- Guardar en un formato adecuado para LanceDB (o similar), p.ej.:

```json
{
  "id": "readme-arbitraje-chunk-3",
  "text": "Crypto price arbitrage scanner using ccxt...",
  "embedding": [0.023, -0.156, ...],
  "metadata": {
    "source": "github",
    "repo": "CarlosCaPe/dataqbs_IA",
    "file": "projects/arbitraje/README.md",
    "commit_sha": "abc123",
    "indexed_at": "2026-02-17T18:30:00Z",
    "chunk_index": 3
  }
}
```

#### 3.4. Vector Store

- LanceDB (WASM) o equivalente para uso en navegador:
  - Permite búsqueda por similitud de vectores (cosine similarity)
  - Compacto y eficiente para un conjunto moderado de chunks (CV + READMEs)
- Estructura esperada:

```
knowledge/
  semantic_model.yaml
  sources/
    cv.json
    certs.json
    github/...
  chunks.json
  knowledge.lance/   # o formato equivalente
  version.json       # commit SHA, timestamp
```

---

### 4. Chatbot RAG en el Cliente

#### 4.1. Flujo de consulta

1. Usuario pregunta (en ES/EN/DE)
2. Validación anti-bot (Cloudflare Turnstile) si es el primer mensaje
3. Detectar idioma por `navigator.language` o selector manual
4. Generar embedding de la query
5. Buscar en el vector store (top-k chunks relevantes)
6. Construir prompt para LLM con:
   - System prompt (políticas de respuesta, profesional, no revelar clientes no incluidos explícitamente)
   - Contexto: chunks recuperados
   - Historial corto de conversación (ventana deslizante + resumen)
7. Mandar a Groq API (Llama 3.x) y mostrar la respuesta

#### 4.2. Prompt base

Ejemplo de prompt:

```text
You are Carlos Carrillo answering questions about your professional experience, skills, and projects.
Use ONLY the provided context. If the information is not present in the context, say you don't have that detail in your public profile.

Policies:
- Never invent client names or companies not listed in the CV or provided context.
- Hide or generalize sensitive client information unless explicitly present in the context.
- Answer in the requested language: {locale} (es/en/de).
- Be concise, professional, and focused.
- If user asks "¿puedes hacer X?" / "can you do X?", answer positively and propose a reasonable approach using the context.

Context:
{retrieved_chunks}

Conversation history (last turns or summary):
{history}

User question: {user_query}

Answer in {locale}:
```

#### 4.3. Memoria de conversación

- Ventana deslizante de N últimos turnos (p.ej. 4)
- Resumen de historial largo cuando exceda cierto tamaño
- No almacenar datos sensibles ni PII; evitar eco de inputs peligrosos

---

### 5. i18n (ES/EN/DE)

- Detectar idioma por navegador:

```js
const browserLang = navigator.language.slice(0, 2);
const supported = ["en", "es", "de"];
const locale = supported.includes(browserLang) ? browserLang : "en";
```

- Textos de la UI (labels, headings, botones) en archivos de traducción
- El chatbot se guía por el locale seleccionado pero puede permitir override manual

---

### 6. Seguridad y Anti-bot

- **Cloudflare Turnstile** como CAPTCHA invisible:
  - Requerido antes del primer mensaje de chat
  - Validar token en el backend (si eventual backend) o en un edge function
- **Rate limiting**:
  - Por sesión en el navegador (ej. 10 mensajes/minuto)
  - Posible extensión futura con limite por IP a través de edge functions
- **Sanitización de inputs**:
  - Bloquear inputs con scripts, HTML, o patrones de ataque típicos
  - Filtrar URLs sospechosas o de phishing
- **Políticas de respuesta**:
  - Nunca revelar nombres de clientes que no estén explícitamente en el CV/data
  - No exponer tokens, secretos, ni credenciales aunque aparezcan en texto crudo (filtro adicional)

---

### 7. Hosting y DNS

- **Hosting principal**: Cloudflare Pages
  - Integración directa con GitHub (`CarlosCaPe/dataqbs_IA` o repo separado `dataqbs_site`)
  - Build command: `npm run build` (Astro)
  - Output dir: `dist/`
- **DNS en Hostinger**:
  - Configurar `www.dataqbs.com` para que apunte al sitio de Cloudflare Pages (CNAME/A según documentación)
  - Opcional: redirigir `dataqbs.com` → `www.dataqbs.com`
- **WordPress actual**:
  - Reemplazado como landing principal
  - Opcional: mover a subdominio `blog.dataqbs.com` si se desea conservar

---

### 8. CI/CD y Auto-sync de READMEs

- **GitHub Actions**:
  - Workflow para build + deploy automático al hacer push a la rama principal
  - Workflow de reindexación de conocimiento:
    - Trigger en cambios a `**/README.md` y otros docs clave
    - Re-generar embeddings
    - Publicar embeddings y metadatos junto con el build o como asset independiente accesible por el frontend

Ejemplo (esquema alto nivel):

```yaml
on:
  push:
    paths:
      - "**/README.md"
      - "docs/**/*.md"
      - "knowledge/semantic_model.yaml"

jobs:
  reindex_and_deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: 20
      - name: Install deps
        run: npm install
      - name: Generate embeddings
        run: npm run gen-embeddings
      - name: Build
        run: npm run build
      - name: Deploy to Cloudflare Pages
        # usar acción oficial de Cloudflare
        run: |
          # ...
```

---

### 9. Verificación y Calidad

- **Local**:
  - `npm run dev` → validar layout, chat, i18n, dark/light
- **Rendimiento**:
  - Lighthouse > 90 en performance, accessibility, best practices, SEO
- **Funcionalidad del chatbot**:
  - Preguntas de prueba:
    - "¿Qué experiencia tienes con Snowflake?"
    - "What Azure certifications do you have?"
    - "Welche Technologien verwenden Sie für Datenpipelines?"
  - Verificar que las respuestas estén siempre ancladas en el contexto
- **Seguridad**:
  - Probar inputs maliciosos / URLs / prompts raros para asegurar que no filtra info sensible

---

### 10. Resumen de Decisiones Clave

- **RAG real** (no simulado): embeddings + vector search + LLM con contexto recuperado
- **Embeddings** y **semantic_model.yaml**: núcleo del conocimiento estructurado
- **LanceDB/Vector store en el cliente**: evita necesidad de VPS/backend, gratis y suficiente para este caso
- **Groq API** (u otro LLM gratuito de alta calidad): equilibrio coste/calidad
- **Cloudflare Pages + DNS Hostinger**: hosting moderno, rápido y sin coste adicional

Este plan queda listo para implementación futura y se puede refinar en detalles (nombres exactos de scripts, estructura final de carpetas, elección definitiva de modelos y librerías) cuando se inicie la fase de desarrollo.