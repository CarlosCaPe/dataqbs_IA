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
];
