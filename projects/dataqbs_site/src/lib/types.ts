// ── Chat ──────────────────────────────────────────────
export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
}

export type ChatStatus =
  | 'idle'
  | 'verifying'
  | 'ready'
  | 'sending'
  | 'streaming'
  | 'error';

// ── Knowledge ────────────────────────────────────────
export interface KnowledgeChunk {
  id: string;
  text: string;
  embedding: number[];
  metadata: ChunkMetadata;
}

export interface ChunkMetadata {
  source: 'cv' | 'certification' | 'github' | 'project';
  section?: string;
  file?: string;
  entity?: string;
  locale?: string;
}

export interface KnowledgeIndex {
  version: string;
  generated_at: string;
  model: string;
  dimensions: number;
  chunks: KnowledgeChunk[];
}

// ── CV ───────────────────────────────────────────────
export interface Experience {
  company: string;
  role: string;
  period: { start: string; end: string | null };
  location: string;
  type: 'full-time' | 'contract' | 'freelance' | 'self-employed';
  description: string;
  achievements: string[];
  technologies: string[];
  hidden?: boolean; // true → show company as "Confidential Client"
}

export interface Education {
  institution: string;
  degree: string;
  field: string;
  period: { start: string; end: string };
  location: string;
  logo?: string;
}

export interface Certification {
  name: string;
  shortName: string;
  issuer: string;
  year: number;
  credentialUrl?: string;
  logo?: string;
}

export interface Project {
  name: string;
  slug: string;
  description: string;
  longDescription?: string;
  technologies: string[];
  github?: string;
  demo?: string;
  highlights: string[];
  category: 'data-engineering' | 'ai-ml' | 'automation' | 'fintech' | 'devops' | 'tools';
  featured: boolean;
}

export interface SkillGroup {
  category: string;
  icon: string;
  skills: { name: string; level: 'expert' | 'advanced' | 'intermediate' }[];
}

export interface SocialLink {
  platform: string;
  url: string;
  icon: string;
  label: string;
}

// ── Contact ──────────────────────────────────────────
export interface ContactFormData {
  name: string;
  email: string;
  message: string;
  turnstileToken: string;
  locale: string;
}

// ── API ──────────────────────────────────────────────
export interface ChatRequest {
  message: string;
  history: { role: string; content: string }[];
  locale: string;
  turnstileToken?: string;
}

export interface ChatResponse {
  content: string;
  chunks_used: number;
}

export interface ContactResponse {
  success: boolean;
  message: string;
}
