# FussionHit — VCA PostgreSQL Audits & Schema Management

Carlos Carrillo worked at FussionHit as a Senior Database Engineer on the VCA (Veterinary Centres of America) project.

## Role & Responsibilities

- Database Engineer for VCA on Azure Database for PostgreSQL
- Built a complete audit framework for PostgreSQL database analysis
- Performed schema performance reviews and optimizations
- Delivered ticket-based database remediation with TDD-quality documentation

## Key Deliverables

### Audit Framework
- PostgreSQL auditor tool (single-file, Node.js) covering tables, views, functions, procedures, triggers, indexes, constraints, sequences, extensions
- Per-object templated DDL exporter using Nunjucks (Jinja-style) for CI/CD-friendly schema snapshots
- Multi-server/multi-database orchestrator for templated DDL export
- LLM-friendly `schema_knowledge.json` generator from DDL snapshots
- Automated `schema_broken_objects_report.json` with heuristic scanning

### Database Tickets (20+)
- DA-16: Primary key audit and remediation
- DA-20: Index strategy optimization for Scribe table (reduce over-indexing)
- DA-22: Add missing foreign keys (idempotent single script)
- DA-43: Table rename (Scribe/Transcription → Recording)
- DA-54: Feature Flags procedures & views discovery
- DA-62: Student Concierge / Relief Vet DB optimization review
- DA-73: Serial → Identity conversion
- DA-78: Rename Scribe → Recording
- DA-80: Appointment Waitlist DB review (16 tables, 9 findings)
- DA-83: VWR (Virtual Waiting Room) DB review (3 functions, anti-patterns)
- DA-84: EC Database Views/Procedures review

### DA-147 — Voyager Health Migration Evaluation
- Ticket DA-147: Deep Dive Discovery into Mars Veterinary Health (MVH) / Voyager Health Documentation and Requirements
- 4,100-line Technical Design Document evaluating SQL Managed Instance (SQL MI) vs PostgreSQL migration feasibility
- Voyager Health is the production platform of Mars Veterinary Health (MVH), running on Azure SQL Managed Instance
- Analysis covered: Cosmos DB dependencies (deeply embedded), 50+ active microservices, SignalR real-time, Azure DevOps CI/CD
- Conclusion: migration not recommended due to 200+ Cosmos DB integration points across the Voyager Health platform
- Epic DA-145 — Voyager Health Collaboration

### Technical Design Documents
- DA-147 Voyager Health migration evaluation (4,100 lines — largest TDD)
- Student Concierge & Relief Vet DB review (858 lines, full architecture)
- VWR DB Performance, Observability, and Schema Design Audit
- Appointment Waitlist DB Review (16 tables, 1 procedure)
- Feature Flags DB review with lifecycle analysis

### Testing & Validation
- Regression test suite: smoke tests + per-ticket offline regressions (DA-16, DA-61, DA-78, DA-83)
- Idempotent SQL scripts (dry-run default, --execute flag for production)
- Evidence-based closure notes with execution logs

## Technologies
- PostgreSQL, Azure Database for PostgreSQL
- Node.js, JavaScript
- Nunjucks (Jinja-style templates)
- pg_stat_statements, EXPLAIN plans
- Jira, Harvest API
- VS Code Tasks

## GitHub Repository
https://github.com/CarlosCaPe/FSH
