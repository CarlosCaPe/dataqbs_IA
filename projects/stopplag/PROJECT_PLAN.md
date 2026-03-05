# StopPlag — Project Plan

> **Client:** Stoplag Fumigación Ecológica (Guadalajara, Jalisco, México)
> **Scope:** Full e-commerce improvements + AI chatbot assistant
> **Date:** 2026-03-04
> **Status:** Planning phase — returning to this later for Description, Discernment, and Diligence practice

---

## 1. Business Understanding (from research)

**What the business is:**
- Ecological pest control company based in ZMG (Zona Metropolitana de Guadalajara)
- Cofepris-licensed (Mexican sanitary authority)
- Two revenue streams:
  1. **Services** — On-site fumigation (cucarachas, chinches, ratas, moscas, termitas, arañas, pulgas, hormigas)
  2. **Products** — E-commerce via Shopify store (3 products currently):
     - Insecticida para Moscas (Stopflies) — $280 MXN
     - H5 Cleaner Desengrasante — $280 MXN
     - Diatomega Fertilizante — $320 MXN
- Key brand pillars: Ecológico, Pet Safe, Servicio al Cliente, Productos Biodegradables
- Current contact channels: WhatsApp (33 3074 0140), phone (33 1754 2697), email (stoplag.contacto@gmail.com)
- Existing social: Facebook (StopfliesMexico), Instagram (@stoplagfumigacion)

**What the interview revealed (end-user pain points):**
1. Has a Shopify store with cart and products — **hasn't sold anything from it**
2. Doesn't know if the site is properly set up (sequencing, programming)
3. Campaigns launched but no conversion
4. Wants a **chatbot/AI assistant** loaded with his business knowledge that handles customer inquiries autonomously
5. Team would only fulfill services and handle shipping
6. Also wants point-of-sale functionality and basic analytics ("se vendió tantas mesas")
7. Sees himself as an "asesor" (advisor), not a salesperson — the chatbot should be the asesor

---

## 2. Major Tasks

### Task 1: E-Commerce Audit & Optimization (Shopify)

**Goal:** Diagnose why the current Shopify store has zero sales and fix it.

**Skills/Knowledge needed:**
- Shopify store management and theme configuration
- E-commerce conversion optimization (CRO)
- SEO for Spanish-language markets
- Payment gateway setup for Mexico (Visa, MC, Amex, Apple Pay are already listed)
- Shipping and fulfillment configuration for Mexico

**Human strengths (Carlos / end-user):**
- **End-user must explain** current Shopify admin access, what theme they're using, what payment gateways are active, what shipping zones are configured
- **End-user decides** pricing strategy, shipping costs, return policy specifics — these are business decisions, not technical ones
- **Carlos can audit** the Shopify admin panel directly — AI cannot access Shopify admin APIs without credentials
- **Carlos has relationship context** to understand the client's technical literacy and communicate changes effectively

**AI strengths:**
- Scrape and analyze the public-facing store for UX/conversion issues (already done above)
- Generate SEO-optimized product descriptions in Spanish
- Analyze competitor fumigation company websites for benchmarking
- Generate a structured checklist of common Shopify conversion killers (checkout flow, trust badges, shipping clarity, etc.)

**Collaboration sweet spot:**
- AI generates the audit checklist and initial findings; Carlos validates against the actual Shopify admin and prioritizes fixes with the client

**Delegation:** 70% Human (requires Shopify admin access + client decisions) / 30% AI (analysis, content generation, benchmarking)

---

### Task 2: Knowledge Base Construction

**Goal:** Build a structured knowledge base of the business's expertise to power the chatbot.

**Skills/Knowledge needed:**
- Domain knowledge of ecological pest control (types of pests, treatment methods, safety, product usage)
- Technical writing and knowledge structuring
- Spanish-language content creation

**Human strengths:**
- **The end-user is the domain expert** — he knows fumigation, his products, service areas, pricing, guarantees, and typical customer questions. This knowledge lives in his head and can only come from him.
- **Carlos conducts follow-up interviews** — structured interviews to extract FAQ-style knowledge, pricing rules, service area boundaries, guarantees
- Nuance, tone, and trust — the client knows how he talks to his customers and what advice is safe to give vs. what requires a professional visit

**AI strengths:**
- Structure raw interview transcripts into organized knowledge categories
- Generate initial FAQ drafts from existing website content (already scraped above)
- Identify gaps in knowledge coverage (e.g., "what do you do about termites?" — no detail on the current site)
- Translate unstructured client knowledge into JSON/Markdown knowledge store format (like the `dataqbs_site` project's `knowledge.json`)

**Collaboration sweet spot:**
- AI drafts knowledge base from scraped content + transcripts; end-user reviews and fills gaps in live sessions; AI restructures the final result

**Delegation:** 50% Human (knowledge extraction, validation) / 50% AI (structuring, gap analysis, formatting)

---

### Task 3: AI Chatbot Development (RAG)

**Goal:** Build a conversational AI assistant that answers customer questions using the knowledge base, running on the Shopify store or as a standalone widget.

**Skills/Knowledge needed:**
- RAG (Retrieval-Augmented Generation) architecture
- LLM API integration (OpenAI, Anthropic, or local models)
- Embedding and vector search (or KV-based retrieval like dataqbs_site)
- Web widget development (JavaScript, embeddable in Shopify)
- Prompt engineering for Spanish-language customer support
- Safety guardrails (don't give medical/pesticide safety advice beyond what's certified)

**Human strengths:**
- **Carlos has built this before** — the `dataqbs_site` project already has a working RAG chatbot (Astro/Svelte on Cloudflare Pages with KV-based knowledge). Architecture decisions draw on this experience.
- **System prompt design** requires human judgment about brand voice, safety boundaries (e.g., "when should the bot say 'call us' vs. answering directly?")
- **Testing with real customer scenarios** — only the end-user knows what actual customers ask
- **Deployment decisions** — Shopify Liquid theme injection vs. external widget, hosting costs, API usage limits

**AI strengths:**
- Write the RAG pipeline code (embedding, retrieval, generation)
- Generate the system prompt in Spanish with appropriate guardrails
- Build the chat widget UI component
- Implement conversation logging and analytics
- Suggest optimal chunk sizes, retrieval strategies, and model selection for cost/quality tradeoff

**Collaboration sweet spot:**
- This is the core engineering task where AI does the heavy lifting on implementation, but Carlos makes architectural decisions and the end-user defines the chatbot persona. Integration testing requires human judgment.

**Delegation:** 30% Human (architecture, persona, testing) / 70% AI (implementation, prompt engineering, widget code)

---

### Task 4: Point-of-Sale & Analytics Dashboard

**Goal:** Give the client visibility into sales, inquiries, and chatbot interactions.

**Skills/Knowledge needed:**
- Dashboard/reporting UI development
- Shopify API or analytics integration
- Data visualization
- Understanding of the client's KPIs (what "mesas" = months of sales he wants to track)

**Human strengths:**
- **Client defines KPIs** — what metrics matter? Product sales? Service quote requests? Chatbot conversation counts? Conversion from chat to WhatsApp?
- **Carlos decides the tech stack** — standalone dashboard vs. Shopify analytics vs. Cloudflare-hosted dashboard
- **Data privacy** — ensuring customer interaction logs comply with Mexican privacy law (LFPDPPP)

**AI strengths:**
- Build the dashboard once requirements are clear (charts, tables, filters)
- Generate API integration code for Shopify or chatbot analytics
- Create summary reports and automated email digests

**Collaboration sweet spot:**
- Human defines what to measure and why; AI builds the measurement infrastructure

**Delegation:** 40% Human (requirements, privacy review, KPI definition) / 60% AI (dashboard code, API integration)

---

### Task 5: Content & Marketing Optimization

**Goal:** Improve the website's content, SEO, and campaign effectiveness to actually drive sales.

**Skills/Knowledge needed:**
- Spanish-language SEO (local, for Guadalajara/Jalisco)
- Content marketing strategy for service businesses
- Social media content (Facebook, Instagram)
- Google My Business / Maps optimization

**Human strengths:**
- **The end-user knows his market** — what neighborhoods, what types of clients (residential vs. commercial), seasonal patterns
- **Carlos can bring marketing strategy** — he understands what campaigns the client tried that failed
- **Photography and video** — the client needs real photos of his work (the existing WhatsApp photos on the site are a start, but more are needed)
- **Client testimonials** — only humans can collect and verify genuine testimonials from real customers

**AI strengths:**
- Rewrite product descriptions for SEO
- Generate blog post drafts about pest control tips (great for organic traffic)
- Analyze competitors' Google presence
- Draft social media content calendar
- Generate meta descriptions, alt text, structured data markup

**Collaboration sweet spot:**
- AI generates content at scale; human reviews for accuracy, tone, and authenticity. Photography and testimonials are purely human contributions.

**Delegation:** 40% Human (strategy, photography, testimonials, review) / 60% AI (content generation, SEO optimization, research)

---

### Task 6: Deployment & Client Training

**Goal:** Ship the solution and ensure the client can use it independently.

**Skills/Knowledge needed:**
- Shopify theme integration
- Cloudflare Pages deployment (or similar hosting)
- Client communication and training
- Documentation and runbooks

**Human strengths:**
- **Only Carlos can train the client** — the end-user needs hands-on guidance, in Spanish, at his technical level
- **Relationship management** — setting expectations about what the chatbot can and can't do, ongoing costs, maintenance
- **Ongoing support agreement** — defining what happens when the knowledge base needs updating, pricing changes, etc.

**AI strengths:**
- Generate documentation and user guides in Spanish
- Create screen-recording scripts or step-by-step tutorials
- Automate deployment pipelines
- Create monitoring alerts for chatbot health

**Collaboration sweet spot:**
- AI prepares all the documentation and deployment automation; Carlos delivers the human training and relationship management

**Delegation:** 60% Human (training, relationship, support agreement) / 40% AI (docs, automation, monitoring)

---

## 3. Summary — Task Delegation Matrix

| # | Task | Human % | AI % | Where collaboration has most impact |
|---|------|---------|------|-------------------------------------|
| 1 | E-Commerce Audit & Optimization | 70% | 30% | AI finds issues, human has Shopify admin access to fix them |
| 2 | Knowledge Base Construction | 50% | 50% | Human extracts domain knowledge, AI structures it |
| 3 | AI Chatbot Development (RAG) | 30% | 70% | Human defines persona/guardrails, AI implements the stack |
| 4 | POS & Analytics Dashboard | 40% | 60% | Human defines KPIs, AI builds measurement tools |
| 5 | Content & Marketing Optimization | 40% | 60% | AI scales content production, human ensures authenticity |
| 6 | Deployment & Client Training | 60% | 40% | AI automates, human trains and manages relationship |

---

## 4. Key Risks & Assumptions

| Risk | Mitigation |
|------|-----------|
| Shopify admin access not shared | Request credentials or collaborator access early |
| Client knowledge gaps | Schedule 2-3 structured interview sessions, not just WhatsApp audios |
| Chatbot gives unsafe advice (pesticide safety) | Hard guardrails in system prompt: "para recomendaciones específicas de seguridad, contacte a un profesional" |
| Low traffic to begin with | Marketing/SEO task must precede chatbot value — chatbot is useless without visitors |
| API costs (LLM inference) | Start with cost-efficient model (e.g., GPT-4o-mini or Claude Haiku), monitor usage |
| End-user technical adoption | Keep UI extremely simple; WhatsApp integration may be more natural than web chat |

---

## 5. Suggested Sequencing

```
Phase 1 (Week 1-2):  E-Commerce Audit + Knowledge Base interviews
Phase 2 (Week 2-4):  Knowledge Base construction + Chatbot RAG development
Phase 3 (Week 3-5):  Content/SEO optimization + Dashboard MVP
Phase 4 (Week 5-6):  Integration, testing, deployment + Client training
```

---

## 6. Discussion Notes — AI vs. Human Strengths

### Where AI capabilities are strongest:
- **Code generation for RAG pipeline** — this is well-trodden ground. AI can produce a working chatbot in hours.
- **Content generation at scale** — rewriting product descriptions, blog posts, SEO metadata in Spanish.
- **Structured analysis** — auditing the website for conversion issues against known best practices.
- **Data transformation** — turning messy interview transcripts into clean knowledge base entries.

### Where uniquely human strengths matter most:
- **Domain knowledge extraction** — the client's expertise about fumigation can't be generated; it must be interviewed out of him.
- **Trust and relationship** — the client said "le voy a echar coquita" (I'll give it a try) — he's cautiously optimistic. Maintaining that trust requires human empathy and follow-through.
- **Judgment calls on safety** — what pest control advice is safe to automate vs. what requires a trained professional? This is a liability decision.
- **Photography and real-world evidence** — no AI can go take photos of the client's fumigation work.
- **Training and handoff** — the client's technical level requires patient, human-led onboarding.

### Challenge to assumptions:
- **Should this even be a web chatbot?** The client's customers already reach out via WhatsApp (the site has a WhatsApp CTA everywhere). A **WhatsApp Business API chatbot** might have 10x more impact than a web widget. This deserves serious discussion.
- **Does the Shopify store need a full rebuild?** Possibly not — it might just need proper configuration (SEO, checkout flow, shipping), not a new platform. Check the admin first.
- **Is the "no sales" problem a traffic problem or a conversion problem?** If no one visits the site, even a perfect checkout won't help. Google Analytics data is needed.

---

## 7. Artifacts Produced So Far

| Artifact | Location |
|----------|----------|
| Audio transcripts (3 parts) | `transcripts/entrevista_completa.md` |
| Individual transcripts | `transcripts/entrevista_parte_{1,2,3}.txt` |
| Business images (28 files) | `inputImages/` |
| Transcription tool | `src/stopplag/transcribe.py` |
| This project plan | `PROJECT_PLAN.md` |

---

## 8. Next Steps (for return visit)

- [ ] Get Shopify admin access and review store configuration
- [ ] Schedule structured knowledge extraction interview with the end-user
- [ ] Check Google Analytics / Shopify analytics for traffic vs. conversion data
- [ ] Decide: web chatbot vs. WhatsApp Business API chatbot (or both?)
- [ ] Prototype the RAG architecture (reuse dataqbs_site patterns if viable)
- [ ] Explore Instagram scraping for additional product photos and customer interactions
