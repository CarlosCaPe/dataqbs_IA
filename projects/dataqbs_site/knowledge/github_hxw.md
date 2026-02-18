# Hexaware Technologies — Freeport-McMoRan Mining Data Engineering

Carlos Carrillo worked at Hexaware Technologies as a Senior Data Engineer on the Freeport-McMoRan (FMI) mining operations project.

## Role & Responsibilities

- Data engineering for mining operations across 7 sites: Morenci, Bagdad, Sierrita, Safford/Miami, Climax, Henderson, Cerro Verde
- Snowflake SQL refactoring with regression validation
- Azure Data Explorer (ADX/KQL) integration for real-time sensor data
- Production dashboard and chatbot development

## Key Projects

### Snowflake Query Refactor Regression Harness (snowrefactor)
- Python CLI tool for refactoring Snowflake SQL with baseline vs refactor validation
- PM-friendly reports for stakeholder communication
- Works with Snowflake browser SSO (externalbrowser authentication)
- Supports QUERIES/ folder structure with versioned baseline/refactor configs

### DRILLBLAST INCR Pipeline
- 14 Snowflake stored procedures for incremental ETL
- Source: SQL Server (SNOWFLAKE_WG database) → Target: Snowflake ({env}_API_REF.FUSE schema)
- Incremental window: 3 days, task schedule: every 15 minutes
- Environments: DEV → TEST → PROD with ADO Pipeline deployment
- Semantic model YAML files for both Snowflake and SQL Server architectures
- E2E verification test script for deployment validation

### IROC Video Wall Dashboard
- Streamlit-based production monitoring for IROC operations
- 34 KPIs covering: Dig (compliance, truck counts, cycle times), Processing (crusher rates, feed rates), Lbs on Ground (ROM tons, stockpile levels)
- Multi-site switching: Morenci, Bagdad, Sierrita, Safford, Climax, Henderson, Cerro Verde
- AI Chat Assistant with RAG architecture using GitHub Copilot SDK (GPT-4o)
- Knowledge base: semantic_model.yaml with 16 business outcomes per site
- Real-time auto-refresh every 60 seconds
- Docker-ready with Azure Container App deployment
- 100% KPI-to-query coverage

### Mining Operations Chatbot
- Natural-language interface to ADX and Snowflake data
- Supports queries like "ios level morenci", "crusher rate MOR", "truck count bagdad"
- 7 mining sites with 16 outcomes each
- Dual data sources: ADX for real-time PI tags, Snowflake for load-haul cycle data
- Rule-based fallback mode when AI is unavailable

### SQL Azure Schema Repository
- DDL extraction from Azure SQL databases across DEV/TEST/PROD
- Browser SSO authentication (azure-identity)
- Organized by environment/database/schema/object type

### ADX/KQL Integration
- Cluster: fctsnaproddatexp02.westus2.kusto.windows.net
- 20+ databases including site-specific and regional
- Functions: FCTSCURRENT() for snapshots, FCTS() for historical
- Stream registry (RegistryStreams) for sensor lookups
- PI tag mapping across all sites

## Technologies
- Snowflake, Azure Data Explorer (KQL), SQL Server, SQL Azure
- Python, Streamlit, Docker
- Azure Functions, Azure Container Apps
- GitHub Copilot SDK, GitHub Models (GPT-4o)
- Optuna (hyperparameter optimization)
- YAML semantic models
- Azure AD / Managed Identity authentication

## GitHub Repository
https://github.com/CarlosCaPe/HXW
