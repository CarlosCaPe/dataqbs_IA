import type { Experience, Education, SkillGroup, SocialLink } from '../lib/types';

// ══════════════════════════════════════════════════════
//  Profile
// ══════════════════════════════════════════════════════
export const profile = {
  name: 'Carlos Carrillo',
  pronouns: 'He/Him',
  headline: 'AI-Driven Engineer | Data · Developer · DBA | Snowflake · Azure SQL · ADX/KQL · Python | Remote (EN/ES)',
  summary:
    "I'm a Senior Data Engineer and Cloud Data Consultant with 20+ years of experience modernizing analytics ecosystems " +
    'with Snowflake, Microsoft Fabric, Azure SQL, and SQL Server. ' +
    'I build automated, scalable pipelines and resilient data models that turn raw data into reliable, actionable insight — ' +
    'especially in high-volume, mission-critical environments where performance, cost efficiency, and long-term maintainability are survival. ' +
    'My toolkit is deep SQL + Python, paired with AI-assisted development (GitHub Copilot, ChatGPT, Claude) ' +
    'to deliver solutions that are cloud-native, operationally practical, and designed to evolve beyond prototypes.',
  vision:
    'To live in peace, free from rigid structures — building projects that flow naturally ' +
    'through intelligence and awareness. Technology should serve life, not the other way around.',
    location: 'Mexico · Remote (Worldwide)',
  photo: '/yo.jpeg',
  banner: '/banner.jpeg',
  cvUrl: '/Profile.pdf',
  cvUrls: {
    en: '/Profile.pdf',
    es: '/Profile_es.pdf',
    de: '/Profile_de.pdf',
  } as Record<string, string>,
  connections: '500+',
  openToWork: [
    'SQL Developer', 'ETL Developer', 'Data Engineer',
    'Integration Lead', 'AI Engineer',
  ],
};

export const socialLinks: SocialLink[] = [
  {
    platform: 'GitHub',
    url: 'https://github.com/CarlosCaPe',
    icon: 'github',
    label: 'CarlosCaPe',
  },
  {
    platform: 'LinkedIn',
    url: 'https://linkedin.com/in/carlosalbertocarrillo',
    icon: 'linkedin',
    label: 'Carlos Carrillo',
  },
  {
    platform: 'Email',
    url: 'mailto:carlos.carrillo@dataqbs.com',
    icon: 'email',
    label: 'carlos.carrillo@dataqbs.com',
  },
  {
    platform: 'Website',
    url: 'https://www.dataqbs.com',
    icon: 'globe',
    label: 'dataqbs.com',
  },
];

// ══════════════════════════════════════════════════════
//  Experience  — Full career history (20+ years)
// ══════════════════════════════════════════════════════
export const experience: Experience[] = [
  // ── Current roles ──────────────────────────────────
  {
    company: 'Hexaware Technologies',
    role: 'Data Integration Lead',
    period: { start: '2025-03', end: null },
    location: 'Mexico · Remote',
    type: 'contract',
    description:
      'Led Snowflake → Azure SQL integration for Freeport-McMoRan mining operations. ' +
      'Deployed incremental sync pipelines, built regression testing CLI, optimized Snowflake views, ' +
      'and developed production dashboards and AI chatbots for 7 mining sites.',
    achievements: [
      'Led Snowflake → Azure SQL integration; deployed 14-table incremental sync pipeline with MERGE procedures, 15-min scheduling, HASH delta detection, E2E verification (~590K rows) across DEV→TEST→PROD',
      'Designed watermark-based incremental loads using business timestamps and DW_MODIFY_TS fallbacks for Connected Operations dashboards',
      'Built snowrefactor, Python CLI for Snowflake view regression testing: automated DDL pull, deployment, schema comparison, and benchmarking in dbt-style CTE workflows',
      'Optimized Snowflake views via deep CTE-pushdown across UNION ALL architectures (65s→9.7s, 5×). Benchmarked Snowflake→ADX migration: SENSOR_SNAPSHOT_GET 30s→0.15s (200×)',
      'Developed IROC Video Wall (Streamlit, 7 mining sites, 60s auto-refresh, AI chat) and Mining Operations Chatbot (NL queries across ADX+Snowflake). Docker, Azure App Service, Azure AD SSO',
      'Built schema extraction across 3 Azure SQL environments, KQL/ADX infrastructure (2 clusters, 20+ site DBs), config-driven execution with Entra ID/Kerberos auth',
      'Leveraged GitHub Copilot (Enterprise) for pipeline architecture, SQL generation, benchmarking, and dashboard development',
    ],
    technologies: [
      'Snowflake', 'Azure SQL', 'ADX/KQL', 'Azure Functions', 'App Service',
      'Python', 'Streamlit', 'Docker', 'GitHub Enterprise', 'Copilot',
      'MERGE/Upsert', 'CDC/Delta', 'CTE Refactoring', 'ETL/ELT',
      'IoT Sensor Data', 'Mining Analytics', 'Entra ID/Kerberos', 'CI/CD',
    ],
  },
  {
    company: 'FussionHit',
    role: 'Senior Database Engineer',
    period: { start: '2025-01', end: null },
    location: 'Remote',
    type: 'contract',
    description:
      'Database engineer for VCA Animal Hospitals on Azure Database for PostgreSQL. Built a full auditing ' +
      'and DDL export framework, performed schema performance reviews, and delivered ticket-based database ' +
      'remediation with TDD-quality documentation across multiple production databases.',
    achievements: [
      'Built PostgreSQL audit framework with per-object templated DDL exports (Nunjucks/Jinja)',
      'Delivered 20+ database tickets (index optimization, FK remediation, schema renames, timestamp normalization)',
      'Authored Technical Design Documents for Student Concierge, Relief Vet, VWR, Appointment Waitlist, and Feature Flags databases',
      'Created regression test suite for all critical tickets with offline validation',
      'Developed PostgreSQL Best Practices guide for Azure Flexible Server',
      'Integrated Jira, Harvest API, and Microsoft Graph API workflows',
    ],
    technologies: [
      'PostgreSQL', 'Azure Database for PostgreSQL', 'Node.js', 'JavaScript',
      'Nunjucks', 'pg_stat_statements', 'EXPLAIN', 'Jira', 'Harvest API',
      'GitHub Copilot',
    ],
  },
  {
    company: 'dataqbs',
    role: 'Data Engineer & AI Developer',
    period: { start: '2011-01', end: null },
    location: 'Guadalajara, Mexico · Remote',
    type: 'self-employed',
    description:
      'Independent consultancy providing BI, data engineering, and database solutions for US and LATAM clients. ' +
      'Also building internal R&D projects: crypto arbitrage scanner, grid trading bots, LLM evaluation engine, ' +
      'email classification system, and this portfolio site with RAG chatbot.',
    achievements: [
      'Delivered data engineering for VCA Animal Hospitals, C&A México, BCG, Moviro, Svitla, Quesos Navarro',
      'Built MEMO-GRID: advanced grid trading bot with Optuna HPO (50K trials), 23× BTC multiplier, attribution analysis (95.7% alpha)',
      'Designed Bellman-Ford & triangular crypto arbitrage scanner across 9 exchanges with live swap execution',
      'Built declarative YAML-driven rule engine for LLM response auditing with 5-dimension scoring',
      'Implemented multi-account IMAP email collector with 5-label classifier (anti-phishing, domain scoring)',
      'Created this portfolio site (dataqbs.com) with RAG chatbot, vector embeddings, and Groq LLM streaming',
    ],
    technologies: [
      'Python', 'SQL Server', 'PostgreSQL', 'Snowflake', 'SSIS/SSRS/SSAS',
      'Tableau', 'Power BI', 'Dataiku DSS', 'Azure Data Factory',
      'Node.js', 'ccxt', 'pandas', 'Astro', 'Svelte',
    ],
  },
  // ── Previous roles ─────────────────────────────────
  {
    company: 'SVAM International Inc.',
    role: 'ETL Engineer',
    period: { start: '2022-11', end: '2024-09' },
    location: 'Mexico · Remote',
    type: 'contract',
    description:
      'Led migration from on-prem SQL Server and SSIS to Snowflake for student certification analytics.',
    achievements: [
      'Led migration from on-prem SQL Server and SSIS to Snowflake, designing new fact/dimension models for student certification analytics',
      'Automated JSON ingestion from Salesforce APIs into Snowflake using Python',
      'Built data validation and reconciliation tests, ensuring end-to-end load accuracy',
      'Delivered curated datasets via SharePoint, improving visibility for academic stakeholders',
      'Supported data transformation and scheduling through custom scripts and CI-controlled processes',
    ],
    technologies: ['Snowflake', 'SQL Server', 'SSIS', 'Python', 'Salesforce API', 'SharePoint'],
  },
  {
    company: 'Svitla Systems, Inc.',
    role: 'Senior ETL Developer',
    period: { start: '2021-05', end: '2023-10' },
    location: 'Mexico · Remote',
    type: 'contract',
    description:
      'Designed and deployed the company\'s first Azure SQL data warehouse, enabling cloud-based sales analytics.',
    achievements: [
      'Designed and deployed the company\'s first Azure SQL data warehouse for cloud-based sales analytics',
      'Developed SSIS packages for on-prem extractions and orchestrated updates with Azure Data Factory',
      'Built flexible star-schema data models to scale as reporting needs grew',
      'Partnered with BI teams to publish Power BI dashboards on Azure',
    ],
    technologies: ['Azure SQL', 'SSIS', 'Azure Data Factory', 'Power BI', 'SQL Server'],
  },
  {
    company: 'Epikso Mexico',
    role: 'Snowflake Administrator',
    period: { start: '2022-01', end: '2023-01' },
    location: 'Mexico · Remote',
    type: 'contract',
    description:
      'Managed Snowflake security, performance tuning, and Infrastructure-as-Code for automated environment setup.',
    achievements: [
      'Managed Snowflake security, role-based access, and performance tuning',
      'Implemented Infrastructure-as-Code for automated environment setup',
      'Monitored query performance and optimized storage/micro-partitioning',
      'Integrated CI/CD pipelines via Bitbucket, improving deployment control',
    ],
    technologies: ['Snowflake', 'Bitbucket', 'CI/CD', 'Infrastructure-as-Code'],
  },
  {
    company: 'Jabil',
    role: 'Data Technical Lead',
    period: { start: '2018-01', end: '2022-03' },
    location: 'Guadalajara, Mexico',
    type: 'full-time',
    description:
      'Directed migration from Hadoop + Impala + SQL Server PDW to Snowflake on AWS for manufacturing analytics.',
    achievements: [
      'Directed migration from Hadoop + Impala + SQL Server PDW to Snowflake on AWS, enabling faster analytics',
      'Built streaming and task-based orchestration using native Snowflake automation features',
      'Designed landing, staging, and refined zones for scalable ingestion and transformation',
      'Supported distributed teams in manufacturing analytics modernization',
    ],
    technologies: ['Snowflake', 'AWS', 'Hadoop', 'Impala', 'SQL Server PDW', 'Python'],
  },
  {
    company: '3Pillar Global',
    role: 'Software Engineer Lead',
    period: { start: '2016-06', end: '2018-01' },
    location: 'Guadalajara, Mexico',
    type: 'full-time',
    description:
      'Developed EDI data integrations and reporting layers for enterprise clients.',
    achievements: [
      'Developed EDI data integrations and reporting layers with SQL Server, SSIS, and SSRS',
      'Maintained reliable data synchronization across multiple external partners',
    ],
    technologies: ['SQL Server', 'SSIS', 'SSRS', 'EDI'],
  },
  {
    company: 'HCL Technologies',
    role: 'SQL SSRS Consultant',
    period: { start: '2014-08', end: '2016-06' },
    location: 'Guadalajara, Mexico',
    type: 'full-time',
    description:
      'Migrated and optimized Actuate Reports into SSRS and SharePoint for enterprise reporting.',
    achievements: [
      'Migrated and optimized Actuate Reports into SSRS and SharePoint',
      'Developed performant SQL logic for enterprise reporting',
    ],
    technologies: ['SQL Server', 'SSRS', 'SharePoint', 'Actuate'],
  },
  {
    company: 'Jabil',
    role: 'Database Analyst II',
    period: { start: '2011-08', end: '2014-08' },
    location: 'Guadalajara, Mexico',
    type: 'full-time',
    description:
      'Created and maintained ETL workflows integrating Oracle, SAP, and MySQL systems with 24/7 database reliability.',
    achievements: [
      'Created and maintained ETL workflows using SSIS, integrating Oracle, SAP, and MySQL systems',
      'Ensured 24/7 database reliability and performance optimization',
    ],
    technologies: ['SQL Server', 'SSIS', 'Oracle', 'SAP', 'MySQL'],
  },
  {
    company: 'C&A México',
    role: 'BI Developer',
    period: { start: '2005-09', end: '2011-08' },
    location: 'Guadalajara, Mexico',
    type: 'full-time',
    description:
      'Designed OLAP cubes and interactive reports for retail analytics across business units.',
    achievements: [
      'Designed OLAP cubes (SSAS) and interactive SSRS reports for retail analytics',
      'Built ETL workflows from mainframes and regional stores to centralized data warehouse',
      'Maintained high-performance SQL environments across business units',
    ],
    technologies: ['SQL Server', 'SSAS', 'SSRS', 'SSIS', 'OLAP'],
  },
  {
    company: 'FIRMEPLUS',
    role: 'Developer',
    period: { start: '2004-04', end: '2005-05' },
    location: 'Guadalajara, Mexico',
    type: 'full-time',
    description:
      'Software and database development with PHP, SQL Server, and MySQL.',
    achievements: [
      'Software and database development (PHP, SQL Server, MySQL)',
    ],
    technologies: ['PHP', 'SQL Server', 'MySQL'],
  },
  {
    company: 'Jabil Circuit de México',
    role: 'Developer Trainee',
    period: { start: '2003-08', end: '2004-05' },
    location: 'Guadalajara, Mexico',
    type: 'full-time',
    description:
      'Supported database and web application development.',
    achievements: [
      'Supported database and web app development',
    ],
    technologies: ['SQL Server', 'Web Development'],
  },
];

// ══════════════════════════════════════════════════════
//  Education
// ══════════════════════════════════════════════════════
export const education: Education[] = [
  {
    institution: 'Universidad de Guadalajara',
    degree: 'Master',
    field: 'Business Administration (MBA)',
    period: { start: '2008', end: '2010' },
    location: 'Guadalajara, Jalisco, Mexico',
    note: 'Degree in process',
    logo: '/udg-logo.jpeg',
  },
  {
    institution: 'Universidad de Guadalajara',
    degree: 'Bachelor Degree',
    field: 'Computing Science',
    period: { start: '1999', end: '2003' },
    location: 'Guadalajara, Jalisco, Mexico',
    logo: '/udg-logo.jpeg',
  },
];

// ══════════════════════════════════════════════════════
//  Skills — derived from actual monorepo technologies
// ══════════════════════════════════════════════════════
export const skills: SkillGroup[] = [
  {
    category: 'Languages',
    icon: '💻',
    skills: [
      { name: 'Python', level: 'expert' },
      { name: 'SQL', level: 'expert' },
      { name: 'JavaScript / TypeScript', level: 'advanced' },
      { name: 'KQL (Kusto)', level: 'advanced' },
      { name: 'Bash', level: 'advanced' },
      { name: 'Node.js', level: 'advanced' },
      { name: 'PowerShell', level: 'intermediate' },
    ],
  },
  {
    category: 'Data & Cloud',
    icon: '☁️',
    skills: [
      { name: 'Snowflake', level: 'expert' },
      { name: 'Azure (SQL, ADF, Functions)', level: 'advanced' },
      { name: 'Azure Data Explorer (ADX)', level: 'advanced' },
      { name: 'Microsoft Fabric', level: 'intermediate' },
      { name: 'Cloudflare (Pages, Workers, AI)', level: 'intermediate' },
    ],
  },
  {
    category: 'AI & ML',
    icon: '🤖',
    skills: [
      { name: 'LLM Evaluation & Prompt Eng.', level: 'advanced' },
      { name: 'RAG (Retrieval-Augmented Gen.)', level: 'advanced' },
      { name: 'Snowflake Cortex AI', level: 'advanced' },
      { name: 'Vector Embeddings & Search', level: 'advanced' },
      { name: 'GitHub Copilot SDK', level: 'advanced' },
      { name: 'Optuna (HPO)', level: 'advanced' },
      { name: 'Fine-Tuning (PEFT / LoRA)', level: 'intermediate' },
    ],
  },
  {
    category: 'Libraries & Frameworks',
    icon: '📦',
    skills: [
      { name: 'pandas / NumPy', level: 'expert' },
      { name: 'ccxt (crypto exchanges)', level: 'expert' },
      { name: 'Streamlit', level: 'advanced' },
      { name: 'Playwright', level: 'advanced' },
      { name: 'Astro / Svelte', level: 'intermediate' },
      { name: 'Nunjucks / Jinja2', level: 'advanced' },
      { name: 'Rich / rapidfuzz', level: 'advanced' },
    ],
  },
  {
    category: 'DevOps & Tools',
    icon: '🔧',
    skills: [
      { name: 'GitHub Actions CI/CD', level: 'advanced' },
      { name: 'Poetry / pip', level: 'expert' },
      { name: 'ruff / pre-commit / pytest', level: 'advanced' },
      { name: 'Docker', level: 'intermediate' },
      { name: 'QEMU / KVM', level: 'intermediate' },
      { name: 'Linux (Pop!_OS)', level: 'advanced' },
    ],
  },
  {
    category: 'Databases',
    icon: '🗄️',
    skills: [
      { name: 'SQL Server', level: 'expert' },
      { name: 'Snowflake', level: 'expert' },
      { name: 'PostgreSQL', level: 'expert' },
      { name: 'Azure SQL / Azure PostgreSQL', level: 'advanced' },
      { name: 'SQLite', level: 'advanced' },
    ],
  },
];
