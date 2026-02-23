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
    messageTooLong: string;
    chatAttached: string;
  };
  theme: { light: string; dark: string; toggle: string };
  lang: { label: string; es: string; en: string; de: string };
  footer: { rights: string; builtWith: string; source: string };
  project: { viewCode: string; liveDemo: string; highlights: string };
  cert: { issuedBy: string; verify: string; expired: string; expires: string; credentialId: string };
  experienceType: Record<string, string>;
  skillCategory: Record<string, string>;
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
      "Senior Data Engineer, AI builder, and Cloud Consultant with 20+ years turning complex data problems into production systems. " +
      'I architect end-to-end solutions — from incremental ETL pipelines and Snowflake/Azure SQL data warehouses to RAG-powered chatbots, ' +
      'physics-based mining simulations, real-time dashboards (34 KPIs across 7 mine sites), and algorithmic trading engines with 50K-trial hyperparameter optimization. ' +
      'My core stack is deep SQL + Python, extended with AI tooling I actually build with — not just use: ' +
      'LLM evaluation pipelines, vector embedding search, Kalman-filter calibration, and Bellman-Ford graph algorithms. ' +
      'I deliver in high-volume, mission-critical environments where uptime, cost efficiency, and long-term maintainability are survival — ' +
      'cloud-native, operationally practical, and designed to evolve beyond prototypes. ' +
      'Fully remote for years with US and LATAM teams — structured delivery, documentation-driven workflows, and clear technical communication across time zones.',
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
    linksHeading: 'Links',    messageTooLong: 'Message too long (max {max} characters)',
    chatAttached: 'Chat conversation attached',  },
  theme: { light: 'Light', dark: 'Dark', toggle: 'Toggle theme' },
  lang: { label: 'Language', es: 'Español', en: 'English', de: 'Deutsch' },
  footer: {
    rights: '© 2026 Carlos Carrillo. All rights reserved.',
    builtWith: 'Built with Astro + Svelte · Hosted on Cloudflare Pages',
    source: 'Source code',
  },
  project: { viewCode: 'View Code', liveDemo: 'Live Demo', highlights: 'Highlights' },
  cert: { issuedBy: 'Issued by', verify: 'Verify', expired: 'Expired', expires: 'Expires', credentialId: 'Credential ID' },
  experienceType: { 'full-time': 'Full-time', 'contract': 'Contract', 'freelance': 'Freelance', 'self-employed': 'Self-employed' },
  skillCategory: { 'Languages': 'Languages', 'Data & Cloud': 'Data & Cloud', 'AI & ML': 'AI & ML', 'Libraries & Frameworks': 'Libraries & Frameworks', 'DevOps & Tools': 'DevOps & Tools', 'Databases': 'Databases' },
};

// ── Spanish ──────────────────────────────────────────
const es: Translations = {
  nav: { experience: 'Experiencia', certifications: 'Certificaciones', projects: 'Proyectos', skills: 'Habilidades', contact: 'Contacto', menu: 'Menú' },
  profile: {
    headline: 'Ingeniero AI-Driven | Datos · Desarrollador · DBA | Snowflake · Azure SQL · ADX/KQL · Python | Remoto (EN/ES)',
    location: 'México · Remoto (Mundial)',
    viewCV: 'Ver CV',
    contactMe: 'Contáctame',
    about: 'Acerca de',
    summary:
      'Ingeniero de Datos Senior, constructor de IA y Consultor Cloud con más de 20 años convirtiendo problemas complejos de datos en sistemas en producción. ' +
      'Arquitecto soluciones end-to-end — desde pipelines ETL incrementales y data warehouses en Snowflake/Azure SQL hasta chatbots RAG, ' +
      'simulaciones físicas para minería, dashboards en tiempo real (34 KPIs en 7 sitios mineros) y motores de trading algorítmico con optimización de 50K trials. ' +
      'Mi stack core es SQL profundo + Python, extendido con herramientas de IA que realmente construyo — no solo uso: ' +
      'pipelines de evaluación LLM, búsqueda por embeddings vectoriales, calibración con filtros de Kalman y algoritmos de grafos Bellman-Ford. ' +
      'Entrego en entornos de alto volumen y misión crítica donde el uptime, la eficiencia en costos y la mantenibilidad a largo plazo son supervivencia — ' +
      'cloud-native, operacionalmente práctico y diseñado para evolucionar más allá de los prototipos. ' +
      'Totalmente remoto por años con equipos de EE.UU. y LATAM — entrega estructurada, flujos documentados y comunicación técnica clara entre zonas horarias.',
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
    linksHeading: 'Enlaces',    messageTooLong: 'Mensaje demasiado largo (m\u00e1ximo {max} caracteres)',
    chatAttached: 'Conversaci\u00f3n de chat adjunta',  },
  theme: { light: 'Claro', dark: 'Oscuro', toggle: 'Cambiar tema' },
  lang: { label: 'Idioma', es: 'Español', en: 'English', de: 'Deutsch' },
  footer: {
    rights: '© 2026 Carlos Carrillo. Todos los derechos reservados.',
    builtWith: 'Hecho con Astro + Svelte · Hospedado en Cloudflare Pages',
    source: 'Código fuente',
  },
  project: { viewCode: 'Ver Código', liveDemo: 'Demo', highlights: 'Destacados' },
  cert: { issuedBy: 'Emitido por', verify: 'Verificar', expired: 'Expirada', expires: 'Expira', credentialId: 'ID de Credencial' },
  experienceType: { 'full-time': 'Tiempo completo', 'contract': 'Contrato', 'freelance': 'Freelance', 'self-employed': 'Independiente' },
  skillCategory: { 'Languages': 'Lenguajes', 'Data & Cloud': 'Datos y Nube', 'AI & ML': 'IA y ML', 'Libraries & Frameworks': 'Librerías y Frameworks', 'DevOps & Tools': 'DevOps y Herramientas', 'Databases': 'Bases de Datos' },
};

// ── German ───────────────────────────────────────────
const de: Translations = {
  nav: { experience: 'Erfahrung', certifications: 'Zertifizierungen', projects: 'Projekte', skills: 'Fähigkeiten', contact: 'Kontakt', menu: 'Menü' },
  profile: {
    headline: 'KI-getriebener Ingenieur | Daten · Entwickler · DBA | Snowflake · Azure SQL · ADX/KQL · Python | Remote (EN/ES)',
    location: 'Mexiko · Remote (Weltweit)',
    viewCV: 'CV anzeigen',
    contactMe: 'Kontakt aufnehmen',
    about: 'Über mich',
    summary:
      'Senior Data Engineer, KI-Entwickler und Cloud-Berater mit über 20 Jahren Erfahrung in der Umsetzung komplexer Datenprobleme in Produktionssysteme. ' +
      'Ich architekturiere End-to-End-Lösungen — von inkrementellen ETL-Pipelines und Snowflake/Azure SQL Data Warehouses bis hin zu RAG-Chatbots, ' +
      'physikbasierten Bergbausimulationen, Echtzeit-Dashboards (34 KPIs über 7 Minenstandorte) und algorithmischen Trading-Engines mit 50K-Trial-Hyperparameter-Optimierung. ' +
      'Mein Kernstack ist tiefes SQL + Python, erweitert mit KI-Tools, die ich tatsächlich baue — nicht nur nutze: ' +
      'LLM-Evaluierungspipelines, Vektor-Embedding-Suche, Kalman-Filter-Kalibrierung und Bellman-Ford-Graphalgorithmen. ' +
      'Ich liefere in hochvolumigen, missionskritischen Umgebungen, in denen Betriebszeit, Kosteneffizienz und langfristige Wartbarkeit überlebenswichtig sind — ' +
      'Cloud-nativ, operativ praktisch und für die Weiterentwicklung über Prototypen hinaus konzipiert. ' +
      'Seit Jahren vollständig remote mit US- und LATAM-Teams — strukturierte Lieferung, dokumentationsgetriebene Workflows und klare technische Kommunikation über Zeitzonen hinweg.',
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
    linksHeading: 'Links',    messageTooLong: 'Nachricht zu lang (max. {max} Zeichen)',
    chatAttached: 'Chat-Gespr\u00e4ch angeh\u00e4ngt',  },
  theme: { light: 'Hell', dark: 'Dunkel', toggle: 'Thema wechseln' },
  lang: { label: 'Sprache', es: 'Español', en: 'English', de: 'Deutsch' },
  footer: {
    rights: '© 2026 Carlos Carrillo. Alle Rechte vorbehalten.',
    builtWith: 'Erstellt mit Astro + Svelte · Gehostet auf Cloudflare Pages',
    source: 'Quellcode',
  },
  project: { viewCode: 'Code ansehen', liveDemo: 'Live-Demo', highlights: 'Highlights' },
  cert: { issuedBy: 'Ausgestellt von', verify: 'Verifizieren', expired: 'Abgelaufen', expires: 'Läuft ab', credentialId: 'Zertifikats-ID' },
  experienceType: { 'full-time': 'Vollzeit', 'contract': 'Vertrag', 'freelance': 'Freiberuflich', 'self-employed': 'Selbstständig' },
  skillCategory: { 'Languages': 'Sprachen', 'Data & Cloud': 'Daten & Cloud', 'AI & ML': 'KI & ML', 'Libraries & Frameworks': 'Bibliotheken & Frameworks', 'DevOps & Tools': 'DevOps & Werkzeuge', 'Databases': 'Datenbanken' },
};

export const translations: Record<string, Translations> = { en, es, de };
export const supportedLocales = ['en', 'es', 'de'] as const;
export type Locale = (typeof supportedLocales)[number];
