# Hexaware Technologies — Freeport-McMoRan Mining Data Engineering

Carlos Carrillo works at Hexaware Technologies (full-time) as a Data Integration Lead on the Freeport-McMoRan mining operations project.

## Role & Responsibilities

- Data engineering for mining operations across 7 sites
- Snowflake SQL refactoring with regression validation
- Azure Data Explorer (ADX/KQL) integration for real-time sensor data
- Production dashboard and chatbot development
- Ore tracing and stockpile simulation platform

## Key Projects

### Snowflake Query Refactor Regression Harness (snowrefactor)
- Python CLI tool for refactoring Snowflake SQL with baseline vs refactor validation
- PM-friendly reports for stakeholder communication
- Works with Snowflake browser SSO (externalbrowser authentication)
- Supports versioned baseline/refactor configs

### Incremental ETL Pipeline
- 14 Snowflake stored procedures for incremental ETL
- Source: SQL Server → Target: Snowflake cloud data warehouse
- Incremental window with automated task scheduling
- Multi-environment deployment (DEV → TEST → PROD) with CI/CD pipelines
- Semantic model YAML files for source and target architectures
- E2E verification test script for deployment validation

### Ore Tracing & Stockpile Simulation Platform
- Physics-based 3D stockpile simulation with block-level mass tracking
- Ore tracing through full comminution circuit: secondary/tertiary crushers → mills → flotation
- Predictive mineralogy tracking with lag-based propagation models (20+ mineral attributes traced)
- Belt-scale correction with Kalman filtering and inertia weighting
- Crush-out time estimation and nowcast simulation for operational planning
- Config-driven YAML architecture with multi-site support
- Data pipeline reads sensor data at 1-minute resolution, runs simulations, writes traced mineral states back
- Deployed via Azure ML Pipelines and Dagster orchestration

### IROC Video Wall Dashboard
- Streamlit-based production monitoring for IROC operations
- 34 KPIs covering: Dig (compliance, truck counts, cycle times), Processing (crusher rates, feed rates), Lbs on Ground (ROM tons, stockpile levels)
- Multi-site switching across 7 mining sites
- AI Chat Assistant with RAG architecture using GitHub Copilot SDK (GPT-4o)
- Knowledge base with 16 business outcomes per site
- Real-time auto-refresh every 60 seconds
- Docker-ready with Azure Container App deployment

### Mining Operations Chatbot
- Natural-language interface to ADX and Snowflake data
- Supports queries for production KPIs (stockpile levels, crusher rates, truck counts, cycle times)
- 7 mining sites with 16 outcomes each
- Dual data sources: ADX for real-time sensor data, Snowflake for operational cycle data
- Rule-based fallback mode when AI is unavailable

### SQL Azure Schema Repository
- DDL extraction from Azure SQL databases across DEV/TEST/PROD
- Browser SSO authentication (azure-identity)
- Organized by environment/database/schema/object type

### ADX/KQL Integration
- Integration with Azure Data Explorer for real-time sensor data
- 20+ databases including site-specific and regional
- Real-time snapshot and historical query functions for sensor data
- Sensor registry and PI tag mapping across all sites

## Technologies
- Snowflake, Azure Data Explorer (KQL), SQL Server, SQL Azure
- Python, Streamlit, Docker, Dagster, Azure ML Pipelines
- Azure Functions, Azure Container Apps
- GitHub Copilot SDK, GitHub Models (GPT-4o)
- NumPy, SciPy, Dynaconf
- YAML semantic models
- Azure AD / Managed Identity authentication

## GitHub Repository
https://github.com/CarlosCaPe/HXW
