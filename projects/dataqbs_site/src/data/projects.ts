import type { Project } from '../lib/types';

export const projects: Project[] = [
  {
    name: 'Crypto Arbitrage Scanner',
    slug: 'arbitraje',
    description:
      'Multi-exchange cryptocurrency arbitrage detector with Bellman-Ford and triangular modes, plus a live swap executor.',
    longDescription:
      'Scans 9 exchanges (Binance, Bitget, Bybit, Coinbase, OKX, KuCoin, Kraken, Gate.io, MEXC) for price inefficiencies. ' +
      'Uses Bellman-Ford shortest-path algorithm and triangular arbitrage detection. Includes a Swapper module for executing trades, ' +
      'WebSocket L2 order-book feeds, SDK bootstrapping for native exchange integrations, and a real-time balance monitor.',
    technologies: ['Python', 'ccxt', 'pandas', 'WebSocket', 'PyYAML', 'Binance SDK', 'ujson'],
    github: 'https://github.com/CarlosCaPe/dataqbs_IA/tree/main/projects/arbitraje',
    highlights: [
      '4,000+ LOC scanner with graph-based arbitrage detection',
      '9 exchange integrations with 4 balance provider backends',
      'Live swap executor with dry-run and production modes',
      'WebSocket L2 partial orderbook for Binance',
      'Portfolio monitor with 1-hop bridge pricing',
    ],
    category: 'fintech',
    featured: true,
  },
  {
    name: 'OAI Code Evaluator',
    slug: 'oai-code-evaluator',
    description:
      'Configurable declarative rule engine for auditing LLM/model responses across 5 quality dimensions.',
    longDescription:
      'YAML-driven evaluation pipeline with rule-based scoring across Instructions, Accuracy, Optimality, ' +
      'Presentation, and Freshness dimensions. Supports regex/substring matching, threshold conditions, ' +
      'ranking normalization, rewrite post-processing, and structured audit metadata output.',
    technologies: ['Python', 'Rich', 'PyYAML', 'jsonschema', 'Jinja2'],
    github: 'https://github.com/CarlosCaPe/dataqbs_IA/tree/main/projects/oai_code_evaluator',
    highlights: [
      '6-stage evaluation pipeline (adjust → rules → rank → rewrite → validate → summary)',
      'Declarative YAML rules with regex, substring, and threshold conditions',
      '5-dimension scoring with configurable ideals and tolerances',
      'Structured JSON/YAML audit output',
    ],
    category: 'ai-ml',
    featured: true,
  },
  {
    name: 'Email Collector & Classifier',
    slug: 'email-collector',
    description:
      'IMAP email collection with OAuth support and a 5-label classification system for anti-phishing detection.',
    longDescription:
      'Multi-account IMAP collector supporting Gmail, Hotmail (MSAL OAuth device-flow), and Exchange. ' +
      'Classifies emails into Scam/Suspicious/Spam/Clean/Unknown using a weighted scoring engine ' +
      'with 200+ domain rules, URL-shortener detection, phone-pattern matching, and fuzzy deduplication.',
    technologies: ['Python', 'imap-tools', 'MSAL', 'langdetect', 'PyYAML'],
    github: 'https://github.com/CarlosCaPe/dataqbs_IA/tree/main/projects/email_collector',
    highlights: [
      '5-label classifier with weighted scoring and hard rules',
      '200+ domain classification rules',
      'OAuth device-flow for Hotmail/Outlook',
      'Fuzzy deduplication with SimHash',
    ],
    category: 'automation',
    featured: true,
  },
  {
    name: 'Real Estate Tools',
    slug: 'real-estate',
    description:
      'API integration and web scraping tools for real-estate platforms (EasyBroker, Wiggot).',
    technologies: ['Python', 'requests', 'Playwright', 'openpyxl'],
    github: 'https://github.com/CarlosCaPe/dataqbs_IA/tree/main/projects/real_estate',
    highlights: [
      '5,400+ LOC EasyBroker API client with concurrent downloads',
      'Playwright-based Wiggot scraper with SSO handling',
      'Microsoft Fabric integration for data engineering',
    ],
    category: 'data-engineering',
    featured: false,
  },
  {
    name: 'Supplier Verifier',
    slug: 'supplier-verifier',
    description:
      'Automated company address verification and supplier-type classification using search APIs and fuzzy matching.',
    technologies: ['Python', 'requests', 'rapidfuzz', 'Google CSE', 'SerpAPI'],
    github: 'https://github.com/CarlosCaPe/dataqbs_IA/tree/main/projects/supplier_verifier',
    highlights: [
      'Fuzzy address matching with rapidfuzz',
      'Category keyword heuristics with evidence scoring',
      'Google CSE / SerpAPI integration',
    ],
    category: 'automation',
    featured: false,
  },
  {
    name: 'Media Comparison (Audio / Image)',
    slug: 'tls-compare',
    description:
      'Automated A/B media comparison tools for quality evaluation using browser automation.',
    technologies: ['Python', 'Playwright', 'NumPy', 'Pillow'],
    github: 'https://github.com/CarlosCaPe/dataqbs_IA',
    highlights: [
      'Side-by-side audio comparison with Playwright automation',
      'Image quality comparison with pixel-level analysis',
    ],
    category: 'tools',
    featured: false,
  },
  {
    name: 'Linux Migration Toolkit',
    slug: 'linux',
    description:
      'Complete Windows → Pop!_OS migration scripts with dev-environment bootstrap and VM setup.',
    technologies: ['Bash', 'QEMU/KVM', 'Python', 'Poetry', 'pre-commit'],
    github: 'https://github.com/CarlosCaPe/dataqbs_IA/tree/main/projects/linux',
    highlights: [
      'Reproducible dev-environment bootstrap script',
      'QEMU/KVM Windows VM creation',
      'System health-check script (CPU, RAM, disk, dev tools, Poetry envs)',
    ],
    category: 'devops',
    featured: false,
  },
  {
    name: 'dataqbs.com Portfolio',
    slug: 'dataqbs-site',
    description:
      'This very website — a LinkedIn-style portfolio with RAG-powered AI chatbot, built with Astro + Svelte + Tailwind on Cloudflare Pages.',
    technologies: ['Astro', 'Svelte', 'Tailwind CSS', 'Cloudflare Workers AI', 'Groq', 'TypeScript'],
    github: 'https://github.com/CarlosCaPe/dataqbs_IA/tree/main/projects/dataqbs_site',
    demo: 'https://www.dataqbs.com',
    highlights: [
      'RAG chatbot with vector embeddings + Groq LLM streaming',
      'Knowledge pipeline: markdown → 58 chunks with 768-dim embeddings',
      'i18n (EN/ES/DE), dark mode, LinkedIn-style layout',
      'Cloudflare Pages + Workers AI + KV storage',
    ],
    category: 'ai-ml',
    featured: true,
  },
  {
    name: 'MEMO-GRID',
    slug: 'memo-grid',
    description:
      'Maker-only grid trading bot for ETH/BTC on Binance with HPO-optimized parameters and full backtest framework.',
    longDescription:
      'Production grid trading microservice using ccxt with Binance Spot. Features Optuna hyperparameter optimization (50K trials), ' +
      'backtest engine with real fee modeling, attribution analysis (alpha vs beta decomposition), Monte Carlo projections, ' +
      'and 22 analysis tools. Includes FIFO inventory tracking, adaptive step sizing, and systemd deployment support.',
    technologies: ['Python', 'ccxt', 'Optuna', 'pandas', 'NumPy', 'PyYAML', 'pytest'],
    github: 'https://github.com/CarlosCaPe/memo/tree/main/MEMO-GRID',
    highlights: [
      'HPO with 50,000 Optuna trials (TPE sampler) for ETH/BTC grid parameters',
      'Backtest engine spanning 2017–2026 with maker fee modeling',
      'Attribution analysis: alpha vs beta return decomposition',
      'Monte Carlo projections with confidence intervals',
      '33 unit tests with full coverage',
    ],
    category: 'fintech',
    featured: true,
  },
  {
    name: 'VCA PostgreSQL Audits',
    slug: 'vca-audits',
    description:
      'Enterprise PostgreSQL audit framework with templated DDL exports, schema analysis, and ticket-based remediation.',
    longDescription:
      'Full audit and schema management framework for Azure Database for PostgreSQL. ' +
      'Includes per-object DDL export with Nunjucks templates, automated schema discovery, ' +
      'LLM-friendly schema_knowledge.json generation, and 20+ ticket-based database improvements ' +
      'across index optimization, FK remediation, timestamp normalization, and stored procedure reviews.',
    technologies: ['PostgreSQL', 'Node.js', 'JavaScript', 'Nunjucks', 'Azure PostgreSQL'],
    github: 'https://github.com/CarlosCaPe/FSH',
    highlights: [
      '20+ tickets: index optimization, FK remediation, schema renames, timestamp fixes',
      'Templated per-object DDL exporter (Nunjucks) for CI/CD-friendly snapshots',
      'Technical Design Documents for 5+ database systems',
      'Regression test suite for critical database changes',
      'Automated timesheet generation with Harvest API',
    ],
    category: 'data-engineering',
    featured: true,
  },
  {
    name: 'IROC Video Wall Dashboard',
    slug: 'iroc-video-wall',
    description:
      'Production mining performance dashboard with 34 KPIs, multi-site switching, and AI chatbot for Freeport-McMoRan.',
    longDescription:
      'Streamlit-based production monitoring dashboard for IROC operations across 7 Freeport-McMoRan mining sites. ' +
      'Features real-time metrics from Snowflake and Azure Data Explorer (ADX), 34 KPIs covering dig compliance, ' +
      'crusher rates, cycle times, and ROM tonnage. Includes RAG-powered AI chatbot with GitHub Copilot SDK, ' +
      'semantic model with 16 business outcomes per site, and auto-refresh every 60 seconds.',
    technologies: ['Python', 'Streamlit', 'Snowflake', 'Azure Data Explorer', 'KQL', 'GitHub Copilot SDK'],
    github: 'https://github.com/CarlosCaPe/HXW/tree/main/SQLRefactoring/VideoWallDashboard',
    highlights: [
      '34 KPIs across 7 mining sites with real-time auto-refresh',
      'AI chatbot with RAG + GitHub Copilot SDK (zero-cost for enterprise)',
      'Semantic model: 16 business outcomes × 7 sites with ADX + Snowflake queries',
      'Docker-ready with Azure Container App deployment',
      '100% KPI-to-query coverage verified',
    ],
    category: 'data-engineering',
    featured: true,
  },
  {
    name: 'Ore Tracing & Stockpile Simulation',
    slug: 'ore-tracing',
    description:
      'Physics-based simulation platform for predicting mineral composition and mass flow through mining processing circuits.',
    longDescription:
      'End-to-end ore tracing system that simulates stockpile behavior using 3D block models and tracks mineralogy ' +
      'through the comminution circuit (secondary/tertiary crushers → mills → flotation). Features predictive ' +
      'calibration of industrial belt scales with Kalman filtering, crush-out time estimation, lag-based propagation ' +
      'models, and nowcast simulation for multiple mine sites. Data pipeline reads sensor data at 1-minute resolution ' +
      'from a cloud data warehouse, runs simulations, and writes traced mineral states back for downstream analytics.',
    technologies: ['Python', 'Snowflake', 'Azure ML Pipelines', 'Dagster', 'NumPy', 'SciPy', 'PyYAML', 'Dynaconf'],
    highlights: [
      'Physics-based 3D stockpile simulation with block-level mass tracking',
      'Mineral composition tracing through crusher → mill → flotation circuits',
      'Kalman filter belt-scale correction with inertia weighting',
      'Nowcast and crush-out time prediction for operational planning',
      'Multi-site deployment with config-driven YAML architecture',
    ],
    category: 'data-engineering',
    featured: true,
  },
  {
    name: 'Mining Operations Chatbot',
    slug: 'mining-chatbot',
    description:
      'Natural-language chatbot for querying ADX and Snowflake mining data across 7 sites with semantic model.',
    technologies: ['Python', 'Streamlit', 'Azure Data Explorer', 'Snowflake', 'YAML'],
    github: 'https://github.com/CarlosCaPe/HXW/tree/main/chatbot',
    highlights: [
      'Natural-language queries for 16 business outcomes per site',
      'ADX + Snowflake dual data source with sensor mappings',
      '7 mining sites: Morenci, Bagdad, Sierrita, Safford, Climax, Henderson, Cerro Verde',
      'Rule-based fallback when AI is unavailable',
    ],
    category: 'ai-ml',
    featured: false,
  },
  {
    name: 'Cross-Exchange Arbitrage Radar',
    slug: 'arbextra',
    description:
      'BTC/USDT cross-exchange arbitrage scanner with auto-triggered taker orders and portfolio monitor.',
    technologies: ['Python', 'ccxt', 'PyYAML', 'pandas'],
    github: 'https://github.com/CarlosCaPe/memo/tree/main/arbextra',
    highlights: [
      'Scans multiple exchanges for BTC/USDT spread opportunities',
      'Configurable auto-trigger with dry-run and live modes',
      'Portfolio PnL tracker with token baselines and CSV export',
      'Rebalance percentage feature with safety clamping',
    ],
    category: 'fintech',
    featured: false,
  },
];
