export interface Translations {
  nav: { experience: string; certifications: string; projects: string; skills: string; contact: string; menu: string };
  profile: {
    headline: string;
    location: string;
    viewCV: string;
    contactMe: string;
    about: string;
    summary: string;
    vision: string;
    visionLabel: string;
    contactInfo: string;
    connections: string;
    openToWork: string;
    roles: string;
    coverAlt: string;
  };
  sections: {
    experience: string;
    projects: string;
    skills: string;
    certifications: string;
    contact: string;
    featuredProjects: string;
    allProjects: string;
  };
  timeline: { present: string; showMore: string; showLess: string; confidential: string; showAllExperiences: string; showAllCertifications: string };
  skill: { expert: string; advanced: string; intermediate: string };
  chat: {
    title: string;
    placeholder: string;
    send: string;
    welcome: string;
    thinking: string;
    error: string;
    rateLimit: string;
    verifying: string;
    openChat: string;
    closeChat: string;
    privacyNote: string;
    suggestion1: string;
    suggestion2: string;
    suggestion3: string;
    suggestion4: string;
    sendConversation: string;
  };
  contact: {
    nameLabel: string;
    emailLabel: string;
    messageLabel: string;
    send: string;
    success: string;
    error: string;
    namePlaceholder: string;
    emailPlaceholder: string;
    messagePlaceholder: string;
    linksHeading: string;
  };
  theme: { light: string; dark: string; toggle: string };
  lang: { label: string; es: string; en: string; de: string };
  footer: { rights: string; builtWith: string; source: string };
  project: { viewCode: string; liveDemo: string; highlights: string };
  cert: { issuedBy: string; verify: string };
}

// ── English ──────────────────────────────────────────
const en: Translations = {
  nav: { experience: 'Experience', certifications: 'Certifications', projects: 'Projects', skills: 'Skills', contact: 'Contact', menu: 'Menu' },
  profile: {
    headline: 'AI-Driven Engineer | Data · Developer · DBA | Snowflake · Azure SQL · ADX/KQL · Python | Remote (EN/ES)',
    location: 'Mexico · Remote (Worldwide)',
    viewCV: 'View CV',
    contactMe: 'Contact me',
    about: 'About',
    summary:
      "I'm a Senior Data Engineer and Cloud Data Consultant with 20+ years of experience modernizing analytics ecosystems " +
      'with Snowflake, Microsoft Fabric, Azure SQL, and SQL Server. ' +
      'I build automated, scalable pipelines and resilient data models that turn raw data into reliable, actionable insight — ' +
      'especially in high-volume, mission-critical environments where performance, cost efficiency, and long-term maintainability are survival. ' +
      'My toolkit is deep SQL + Python, paired with AI-assisted development (GitHub Copilot, ChatGPT, Claude) ' +
      'to deliver solutions that are cloud-native, operationally practical, and designed to evolve beyond prototypes.',
    vision: 'To live in peace, free from rigid structures — building projects that flow naturally through intelligence and awareness. Technology should serve life, not the other way around.',
    visionLabel: 'Vision',
    contactInfo: 'Contact info',
    connections: 'connections',
    openToWork: 'Open to work',
    roles: 'roles',
    coverAlt: 'Cover',
  },
  sections: {
    experience: 'Experience',
    projects: 'Projects',
    skills: 'Skills',
    certifications: 'Certifications',
    contact: 'Contact',
    featuredProjects: 'Featured Projects',
    allProjects: 'All Projects',
  },
  timeline: { present: 'Present', showMore: 'Show more', showLess: 'Show less', confidential: 'Confidential Client', showAllExperiences: 'Show all {count} experiences', showAllCertifications: 'Show all {count} certifications' },
  skill: { expert: 'Expert', advanced: 'Advanced', intermediate: 'Intermediate' },
  chat: {
    title: 'Chat with Carlos',
    placeholder: 'Ask about my experience, skills, projects…',
    send: 'Send',
    welcome:
      "Hi! I'm Carlos — well, my AI version. Ask me anything about my 20+ years in data engineering, my projects, skills, or certifications. **Tell me about your requirement** and I'll share how my experience can help.",
    thinking: 'Thinking…',
    error: 'Something went wrong. Please try again.',
    rateLimit: 'Too many messages. Please wait a moment.',
    verifying: 'Verifying…',
    openChat: 'Chat with Carlos',
    closeChat: 'Close chat',
    privacyNote: 'Your messages are not stored. This conversation is private.',
    suggestion1: 'Tell me about your requirement',
    suggestion2: 'What companies have you worked for?',
    suggestion3: 'Can you do Snowflake migrations?',
    suggestion4: 'What certifications do you have?',
    sendConversation: 'Send this conversation',
  },
  contact: {
    nameLabel: 'Name',
    emailLabel: 'Email',
    messageLabel: 'Message',
    send: 'Send message',
    success: "Message sent! I'll get back to you soon.",
    error: 'Could not send message. Please try again.',
    namePlaceholder: 'Your name',
    emailPlaceholder: 'your@email.com',
    messagePlaceholder: 'Your message…',
    linksHeading: 'Links',
  },
  theme: { light: 'Light', dark: 'Dark', toggle: 'Toggle theme' },
  lang: { label: 'Language', es: 'Español', en: 'English', de: 'Deutsch' },
  footer: {
    rights: '© 2026 Carlos Carrillo. All rights reserved.',
    builtWith: 'Built with Astro + Svelte · Hosted on Cloudflare Pages',
    source: 'Source code',
  },
  project: { viewCode: 'View Code', liveDemo: 'Live Demo', highlights: 'Highlights' },
  cert: { issuedBy: 'Issued by', verify: 'Verify' },
};

// ── Spanish ──────────────────────────────────────────
const es: Translations = {
  nav: { experience: 'Experiencia', certifications: 'Certificaciones', projects: 'Proyectos', skills: 'Habilidades', contact: 'Contacto', menu: 'Menú' },
  profile: {
    headline: 'Ingeniero AI-Driven | Datos · Desarrollador · DBA | Snowflake · Azure SQL · ADX/KQL · Python | Remoto (EN/ES)',
    location: 'México · Remoto (Mundial)',
    viewCV: 'Ver CV (EN)',
    contactMe: 'Contáctame',
    about: 'Acerca de',
    summary:
      'Soy un Ingeniero de Datos Senior y Consultor Cloud con más de 20 años de experiencia modernizando ecosistemas analíticos ' +
      'con Snowflake, Microsoft Fabric, Azure SQL y SQL Server. ' +
      'Construyo pipelines automatizados y escalables, y modelos de datos resilientes que convierten datos crudos en información confiable y accionable — ' +
      'especialmente en entornos de alto volumen y misión crítica donde el rendimiento, la eficiencia en costos y la mantenibilidad a largo plazo son supervivencia. ' +
      'Mi toolkit es SQL profundo + Python, combinado con desarrollo asistido por IA (GitHub Copilot, ChatGPT, Claude) ' +
      'para entregar soluciones cloud-native, operacionalmente prácticas y diseñadas para evolucionar más allá de los prototipos.',
    vision: 'Vivir en paz, libre de estructuras rígidas — construyendo proyectos que fluyen naturalmente a través de inteligencia y consciencia. La tecnología debe servir a la vida, no al revés.',
    visionLabel: 'Visión',
    contactInfo: 'Info de contacto',
    connections: 'conexiones',
    openToWork: 'Abierto a trabajar',
    roles: 'roles',
    coverAlt: 'Portada',
  },
  sections: {
    experience: 'Experiencia',
    projects: 'Proyectos',
    skills: 'Habilidades',
    certifications: 'Certificaciones',
    contact: 'Contacto',
    featuredProjects: 'Proyectos Destacados',
    allProjects: 'Todos los Proyectos',
  },
  timeline: { present: 'Actual', showMore: 'Ver más', showLess: 'Ver menos', confidential: 'Cliente Confidencial', showAllExperiences: 'Ver las {count} experiencias', showAllCertifications: 'Ver las {count} certificaciones' },
  skill: { expert: 'Experto', advanced: 'Avanzado', intermediate: 'Intermedio' },
  chat: {
    title: 'Chatea con Carlos',
    placeholder: 'Pregunta sobre mi experiencia, habilidades, proyectos…',
    send: 'Enviar',
    welcome:
      '¡Hola! Soy Carlos — bueno, mi versión IA. Pregúntame lo que quieras sobre mis 20+ años en ingeniería de datos, mis proyectos, habilidades o certificaciones. **Cuéntame tu requisito** y te comparto cómo mi experiencia puede ayudar.',
    thinking: 'Pensando…',
    error: 'Algo salió mal. Intenta de nuevo.',
    rateLimit: 'Demasiados mensajes. Espera un momento.',
    verifying: 'Verificando…',
    openChat: 'Chatea con Carlos',
    closeChat: 'Cerrar chat',
    privacyNote: 'Tus mensajes no se almacenan. Esta conversación es privada.',
    suggestion1: 'Cuéntame tu requisito',
    suggestion2: '¿En qué empresas has trabajado?',
    suggestion3: '¿Puedes hacer migraciones a Snowflake?',
    suggestion4: '¿Qué certificaciones tienes?',
    sendConversation: 'Enviar esta conversación',
  },
  contact: {
    nameLabel: 'Nombre',
    emailLabel: 'Correo',
    messageLabel: 'Mensaje',
    send: 'Enviar mensaje',
    success: '¡Mensaje enviado! Te responderé pronto.',
    error: 'No se pudo enviar. Intenta de nuevo.',
    namePlaceholder: 'Tu nombre',
    emailPlaceholder: 'tu@correo.com',
    messagePlaceholder: 'Tu mensaje…',
    linksHeading: 'Enlaces',
  },
  theme: { light: 'Claro', dark: 'Oscuro', toggle: 'Cambiar tema' },
  lang: { label: 'Idioma', es: 'Español', en: 'English', de: 'Deutsch' },
  footer: {
    rights: '© 2026 Carlos Carrillo. Todos los derechos reservados.',
    builtWith: 'Hecho con Astro + Svelte · Hospedado en Cloudflare Pages',
    source: 'Código fuente',
  },
  project: { viewCode: 'Ver Código', liveDemo: 'Demo', highlights: 'Destacados' },
  cert: { issuedBy: 'Emitido por', verify: 'Verificar' },
};

// ── German ───────────────────────────────────────────
const de: Translations = {
  nav: { experience: 'Erfahrung', certifications: 'Zertifizierungen', projects: 'Projekte', skills: 'Fähigkeiten', contact: 'Kontakt', menu: 'Menü' },
  profile: {
    headline: 'KI-getriebener Ingenieur | Daten · Entwickler · DBA | Snowflake · Azure SQL · ADX/KQL · Python | Remote (EN/ES)',
    location: 'Mexiko · Remote (Weltweit)',
    viewCV: 'CV anzeigen (EN)',
    contactMe: 'Kontakt aufnehmen',
    about: 'Über mich',
    summary:
      'Ich bin ein Senior Data Engineer und Cloud-Datenberater mit über 20 Jahren Erfahrung in der Modernisierung analytischer Ökosysteme ' +
      'mit Snowflake, Microsoft Fabric, Azure SQL und SQL Server. ' +
      'Ich baue automatisierte, skalierbare Pipelines und belastbare Datenmodelle, die Rohdaten in zuverlässige, umsetzbare Erkenntnisse verwandeln — ' +
      'besonders in hochvolumigen, missionskritischen Umgebungen, in denen Leistung, Kosteneffizienz und langfristige Wartbarkeit überlebenswichtig sind. ' +
      'Mein Toolkit ist tiefes SQL + Python, gepaart mit KI-gestützter Entwicklung (GitHub Copilot, ChatGPT, Claude), ' +
      'um Lösungen zu liefern, die Cloud-nativ, operativ praktisch und für die Weiterentwicklung über Prototypen hinaus konzipiert sind.',
    vision: 'In Frieden leben, frei von starren Strukturen — Projekte aufbauen, die natürlich durch Intelligenz und Bewusstsein fließen. Technologie sollte dem Leben dienen, nicht umgekehrt.',
    visionLabel: 'Vision',
    contactInfo: 'Kontaktdaten',
    connections: 'Kontakte',
    openToWork: 'Offen für Arbeit',
    roles: 'Rollen',
    coverAlt: 'Titelbild',
  },
  sections: {
    experience: 'Erfahrung',
    projects: 'Projekte',
    skills: 'Fähigkeiten',
    certifications: 'Zertifizierungen',
    contact: 'Kontakt',
    featuredProjects: 'Ausgewählte Projekte',
    allProjects: 'Alle Projekte',
  },
  timeline: { present: 'Aktuell', showMore: 'Mehr anzeigen', showLess: 'Weniger anzeigen', confidential: 'Vertraulicher Kunde', showAllExperiences: 'Alle {count} Erfahrungen anzeigen', showAllCertifications: 'Alle {count} Zertifizierungen anzeigen' },
  skill: { expert: 'Experte', advanced: 'Fortgeschritten', intermediate: 'Mittel' },
  chat: {
    title: 'Chat mit Carlos',
    placeholder: 'Frag nach Erfahrung, Fähigkeiten, Projekten…',
    send: 'Senden',
    welcome:
      "Hallo! Ich bin Carlos — naja, meine KI-Version. Frag mich alles über meine 20+ Jahre im Data Engineering, meine Projekte, Fähigkeiten oder Zertifizierungen. **Erzähl mir von deinem Bedarf** und ich teile dir mit, wie meine Erfahrung helfen kann.",
    thinking: 'Denke nach…',
    error: 'Etwas ist schiefgelaufen. Bitte versuche es erneut.',
    rateLimit: 'Zu viele Nachrichten. Bitte warte einen Moment.',
    verifying: 'Überprüfung…',
    openChat: 'Chat mit Carlos',
    closeChat: 'Chat schließen',
    privacyNote: 'Deine Nachrichten werden nicht gespeichert. Dieses Gespräch ist privat.',
    suggestion1: 'Erzähl mir von deinem Bedarf',
    suggestion2: 'Für welche Unternehmen hast du gearbeitet?',
    suggestion3: 'Kannst du Snowflake-Migrationen machen?',
    suggestion4: 'Welche Zertifizierungen hast du?',
    sendConversation: 'Dieses Gespräch senden',
  },
  contact: {
    nameLabel: 'Name',
    emailLabel: 'E-Mail',
    messageLabel: 'Nachricht',
    send: 'Nachricht senden',
    success: 'Nachricht gesendet! Ich melde mich bald.',
    error: 'Konnte nicht gesendet werden. Bitte erneut versuchen.',
    namePlaceholder: 'Dein Name',
    emailPlaceholder: 'deine@email.de',
    messagePlaceholder: 'Deine Nachricht…',
    linksHeading: 'Links',
  },
  theme: { light: 'Hell', dark: 'Dunkel', toggle: 'Thema wechseln' },
  lang: { label: 'Sprache', es: 'Español', en: 'English', de: 'Deutsch' },
  footer: {
    rights: '© 2026 Carlos Carrillo. Alle Rechte vorbehalten.',
    builtWith: 'Erstellt mit Astro + Svelte · Gehostet auf Cloudflare Pages',
    source: 'Quellcode',
  },
  project: { viewCode: 'Code ansehen', liveDemo: 'Live-Demo', highlights: 'Highlights' },
  cert: { issuedBy: 'Ausgestellt von', verify: 'Verifizieren' },
};

export const translations: Record<string, Translations> = { en, es, de };
export const supportedLocales = ['en', 'es', 'de'] as const;
export type Locale = (typeof supportedLocales)[number];
