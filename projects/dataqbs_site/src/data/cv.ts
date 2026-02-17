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
//  Experience  — UPDATE with your actual work history
// ══════════════════════════════════════════════════════
export const experience: Experience[] = [
  {
    company: 'dataqbs (Self-Employed)',
    role: 'Data Engineer & Software Developer',
    period: { start: '2024-01', end: null },
    location: 'Mexico · Remote',
    type: 'self-employed',
    description:
      'Building a monorepo of data-engineering and AI tools: crypto arbitrage scanner, ' +
      'LLM-response evaluation engine, email classification system, real-estate data automation, ' +
      'and automated media comparison tools.',
    achievements: [
      'Designed Bellman-Ford & triangular arbitrage scanner across 9 crypto exchanges with live swap execution',
      'Built declarative YAML-driven rule engine for LLM response auditing with 5-dimension scoring',
      'Implemented multi-account IMAP email collector with 5-label classifier (anti-phishing, domain scoring)',
      'Created real-time multi-exchange portfolio monitor with 1-hop bridge pricing',
      'Automated Windows → Linux migration with reproducible dev-env scripts',
    ],
    technologies: [
      'Python', 'ccxt', 'pandas', 'Playwright', 'PyYAML', 'Rich',
      'GitHub Actions', 'Poetry', 'ruff', 'pytest',
    ],
  },
  {
    company: 'Confidential Client',
    role: 'Senior Data Engineer',
    period: { start: '2022-06', end: '2023-12' },
    location: 'Remote',
    type: 'contract',
    description:
      'Designed and maintained cloud data pipelines on Azure and Snowflake for a large enterprise client.',
    achievements: [
      'Built ETL pipelines processing 50M+ rows/day with Azure Data Factory & Snowflake',
      'Optimized SQL queries reducing warehouse costs by 35%',
      'Implemented data-quality checks with automated alerting',
    ],
    technologies: ['Snowflake', 'Azure Data Factory', 'Azure SQL', 'Python', 'SQL', 'dbt'],
    hidden: true,
  },
  // ── ADD MORE experiences below ──
  // {
  //   company: 'Your Previous Company',
  //   role: 'Data Engineer',
  //   period: { start: '2020-01', end: '2022-05' },
  //   ...
  // },
];

// ══════════════════════════════════════════════════════
//  Education — UPDATE with your actual education
// ══════════════════════════════════════════════════════
export const education: Education[] = [
  {
    institution: 'Universidad de Guadalajara',
    degree: 'Bachelor of Science',
    field: 'Computer Science / Engineering',
    period: { start: '2000', end: '2005' },
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
      { name: 'Bash', level: 'advanced' },
      { name: 'PowerShell', level: 'intermediate' },
    ],
  },
  {
    category: 'Data & Cloud',
    icon: '☁️',
    skills: [
      { name: 'Snowflake', level: 'expert' },
      { name: 'Azure (SQL, ADF, Functions)', level: 'advanced' },
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
      { name: 'Fine-Tuning (PEFT / LoRA)', level: 'intermediate' },
    ],
  },
  {
    category: 'Libraries & Frameworks',
    icon: '📦',
    skills: [
      { name: 'pandas / NumPy', level: 'expert' },
      { name: 'ccxt (crypto exchanges)', level: 'expert' },
      { name: 'Playwright', level: 'advanced' },
      { name: 'Astro / Svelte', level: 'intermediate' },
      { name: 'Rich / Jinja2', level: 'advanced' },
      { name: 'rapidfuzz', level: 'advanced' },
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
      { name: 'Azure SQL', level: 'advanced' },
      { name: 'SQLite', level: 'advanced' },
    ],
  },
];
