/**
 * project_translations.ts — Project descriptions & highlights for ES / DE.
 *
 * Keyed by project slug (matching projects.ts).
 * The ProjectsGrid component uses these to show translated content
 * when the locale is not 'en'.
 *
 * KEEP IN SYNC with projects.ts — if you add/rename projects there, update here too.
 */

export interface ProjectTranslation {
  description: string;
  longDescription?: string;
  highlights: string[];
}

// ══════════════════════════════════════════════════════
//  SPANISH
// ══════════════════════════════════════════════════════
const es: Record<string, ProjectTranslation> = {
  'arbitraje': {
    description:
      'Detector de arbitraje de criptomonedas multi-exchange con modos Bellman-Ford y triangular, más un ejecutor de swaps en vivo.',
    longDescription:
      'Escanea 9 exchanges (Binance, Bitget, Bybit, Coinbase, OKX, KuCoin, Kraken, Gate.io, MEXC) buscando ineficiencias de precio. ' +
      'Usa algoritmo de camino más corto Bellman-Ford y detección de arbitraje triangular. Incluye un módulo Swapper para ejecutar trades, ' +
      'feeds WebSocket de order book L2, bootstrapping de SDK para integraciones nativas, y un monitor de balances en tiempo real.',
    highlights: [
      '4,000+ LOC scanner con detección de arbitraje basada en grafos',
      '9 integraciones de exchanges con 4 backends de proveedor de balances',
      'Ejecutor de swaps en vivo con modos dry-run y producción',
      'WebSocket L2 orderbook parcial para Binance',
      'Monitor de portafolio con pricing de puente de 1 salto',
    ],
  },
  'oai-code-evaluator': {
    description:
      'Motor de reglas declarativo configurable para auditar respuestas de LLM/modelos en 5 dimensiones de calidad.',
    longDescription:
      'Pipeline de evaluación basado en YAML con scoring basado en reglas en Instrucciones, Precisión, Optimalidad, ' +
      'Presentación y Frescura. Soporta coincidencia regex/substring, condiciones de umbral, ' +
      'normalización de ranking, post-procesamiento de reescritura, y salida de metadatos de auditoría estructurada.',
    highlights: [
      'Pipeline de evaluación de 6 etapas (ajustar → reglas → ranking → reescribir → validar → resumen)',
      'Reglas YAML declarativas con condiciones regex, substring y umbral',
      'Scoring en 5 dimensiones con ideales y tolerancias configurables',
      'Salida de auditoría estructurada JSON/YAML',
    ],
  },
  'email-collector': {
    description:
      'Colector de correo IMAP con soporte OAuth y sistema de clasificación de 5 etiquetas para detección anti-phishing.',
    longDescription:
      'Colector IMAP multi-cuenta soportando Gmail, Hotmail (flujo de dispositivo MSAL OAuth) y Exchange. ' +
      'Clasifica correos en Estafa/Sospechoso/Spam/Limpio/Desconocido usando un motor de scoring ponderado ' +
      'con 200+ reglas de dominio, detección de acortadores de URL, coincidencia de patrones de teléfono y deduplicación fuzzy.',
    highlights: [
      'Clasificador de 5 etiquetas con scoring ponderado y reglas duras',
      '200+ reglas de clasificación de dominio',
      'Flujo de dispositivo OAuth para Hotmail/Outlook',
      'Deduplicación fuzzy con SimHash',
    ],
  },
  'real-estate': {
    description:
      'Herramientas de integración API y web scraping para plataformas inmobiliarias (EasyBroker, Wiggot).',
    highlights: [
      'Cliente API EasyBroker de 5,400+ LOC con descargas concurrentes',
      'Scraper Wiggot basado en Playwright con manejo de SSO',
      'Integración de Microsoft Fabric para ingeniería de datos',
    ],
  },
  'supplier-verifier': {
    description:
      'Verificación automatizada de dirección de empresa y clasificación de tipo de proveedor usando APIs de búsqueda y coincidencia fuzzy.',
    highlights: [
      'Coincidencia fuzzy de direcciones con rapidfuzz',
      'Heurísticas de palabras clave de categoría con scoring de evidencia',
      'Integración Google CSE / SerpAPI',
    ],
  },
  'tls-compare': {
    description:
      'Herramientas automatizadas de comparación A/B de medios para evaluación de calidad usando automatización de navegador.',
    highlights: [
      'Comparación de audio lado a lado con automatización Playwright',
      'Comparación de calidad de imagen con análisis a nivel de píxel',
    ],
  },
  'linux': {
    description:
      'Scripts completos de migración Windows → Pop!_OS con bootstrap de entorno de desarrollo y configuración de VM.',
    highlights: [
      'Script reproducible de bootstrap de entorno de desarrollo',
      'Creación de VM con QEMU/KVM para Windows',
      'Script de chequeo de salud del sistema (CPU, RAM, disco, dev tools, entornos Poetry)',
    ],
  },
  'dataqbs-site': {
    description:
      'Este mismo sitio — un portafolio estilo LinkedIn con chatbot de IA RAG, construido con Astro + Svelte + Tailwind en Cloudflare Pages.',
    highlights: [
      'Chatbot RAG con embeddings vectoriales + streaming LLM con Groq',
      'Pipeline de conocimiento: markdown → 58 chunks con embeddings de 768 dims',
      'i18n (EN/ES/DE), modo oscuro, diseño estilo LinkedIn',
      'Cloudflare Pages + Workers AI + almacenamiento KV',
    ],
  },
  'memo-grid': {
    description:
      'Bot de grid trading solo-maker para ETH/BTC en Binance con parámetros optimizados por HPO y framework de backtest completo.',
    longDescription:
      'Microservicio de grid trading en producción usando ccxt con Binance Spot. Incluye optimización de hiperparámetros Optuna (50K pruebas), ' +
      'motor de backtest con modelado de comisiones reales, análisis de atribución (descomposición alfa vs beta), proyecciones Monte Carlo, ' +
      'y 22 herramientas de análisis. Incluye seguimiento de inventario FIFO, dimensionamiento adaptativo de pasos, y soporte de despliegue systemd.',
    highlights: [
      'HPO con 50,000 pruebas Optuna (muestreador TPE) para parámetros de grid ETH/BTC',
      'Motor de backtest abarcando 2017–2026 con modelado de comisión maker',
      'Análisis de atribución: descomposición de retorno alfa vs beta',
      'Proyecciones Monte Carlo con intervalos de confianza',
      '33 pruebas unitarias con cobertura completa',
    ],
  },
  'vca-audits': {
    description:
      'Framework empresarial de auditoría PostgreSQL con exportaciones DDL templadas, análisis de esquema, y remediación basada en tickets.',
    longDescription:
      'Framework completo de auditoría y gestión de esquemas para Azure Database for PostgreSQL. ' +
      'Incluye exportación DDL por objeto con templates Nunjucks, descubrimiento automatizado de esquemas, ' +
      'generación de schema_knowledge.json amigable con LLM, y 20+ mejoras de base de datos basadas en tickets ' +
      'en optimización de índices, remediación de FK, normalización de timestamps, y revisiones de procedimientos almacenados.',
    highlights: [
      '20+ tickets: optimización de índices, remediación de FK, renombramientos de esquema, correcciones de timestamps',
      'Exportador DDL templado por objeto (Nunjucks) para snapshots compatibles con CI/CD',
      'Documentos de Diseño Técnico para 5+ sistemas de bases de datos',
      'Suite de pruebas de regresión para cambios críticos de base de datos',
      'Generación automatizada de hoja de tiempo con Harvest API',
    ],
  },
  'iroc-video-wall': {
    description:
      'Dashboard de rendimiento minero en producción con 34 KPIs, cambio multi-sitio, y chatbot de IA para Freeport-McMoRan.',
    longDescription:
      'Dashboard de monitoreo de producción basado en Streamlit para operaciones IROC en 7 sitios mineros de Freeport-McMoRan. ' +
      'Presenta métricas en tiempo real desde Snowflake y Azure Data Explorer (ADX), 34 KPIs cubriendo cumplimiento de dig, ' +
      'tasas de trituración, tiempos de ciclo, y tonelaje ROM. Incluye chatbot de IA con RAG usando GitHub Copilot SDK, ' +
      'modelo semántico con 16 resultados de negocio por sitio, y auto-refresh cada 60 segundos.',
    highlights: [
      '34 KPIs a través de 7 sitios mineros con auto-refresh en tiempo real',
      'Chatbot de IA con RAG + GitHub Copilot SDK (costo cero para enterprise)',
      'Modelo semántico: 16 resultados de negocio × 7 sitios con consultas ADX + Snowflake',
      'Listo para Docker con despliegue en Azure Container App',
      '100% cobertura KPI-a-consulta verificada',
    ],
  },
  'ore-tracing': {
    description:
      'Plataforma de simulación basada en física para predecir composición mineral y flujo de masa a través de circuitos de procesamiento minero.',
    longDescription:
      'Sistema de trazado de mineral end-to-end que simula comportamiento de stockpile usando modelos de bloques 3D y rastrea mineralogía ' +
      'a través del circuito de conminución (trituradoras secundarias/terciarias → molinos → flotación). Incluye calibración predictiva ' +
      'de básculas industriales con filtrado Kalman, estimación de tiempo de crush-out, modelos de propagación basados en lag, ' +
      'y simulación nowcast para múltiples sitios mineros. El pipeline de datos lee datos de sensores a resolución de 1 minuto ' +
      'desde un data warehouse en la nube, ejecuta simulaciones, y escribe estados minerales trazados para analítica downstream.',
    highlights: [
      'Simulación de stockpile basada en física 3D con seguimiento de masa a nivel de bloque',
      'Trazado de composición mineral a través de circuitos trituradora → molino → flotación',
      'Corrección de báscula con filtro Kalman con ponderación de inercia',
      'Predicción nowcast y de tiempo de crush-out para planificación operativa',
      'Despliegue multi-sitio con arquitectura YAML config-driven',
    ],
  },
  'mining-chatbot': {
    description:
      'Chatbot de lenguaje natural para consultar datos mineros de ADX y Snowflake en 7 sitios con modelo semántico.',
    highlights: [
      'Consultas en lenguaje natural para 16 resultados de negocio por sitio',
      'Fuente de datos dual ADX + Snowflake con mapeos de sensores',
      '7 sitios mineros: Morenci, Bagdad, Sierrita, Safford, Climax, Henderson, Cerro Verde',
      'Fallback basado en reglas cuando la IA no está disponible',
    ],
  },
  'arbextra': {
    description:
      'Escáner de arbitraje cross-exchange BTC/USDT con órdenes taker auto-disparadas y monitor de portafolio.',
    highlights: [
      'Escanea múltiples exchanges buscando oportunidades de spread BTC/USDT',
      'Auto-trigger configurable con modos dry-run y producción',
      'Rastreador de PnL de portafolio con líneas base de tokens y exportación CSV',
      'Función de rebalanceo porcentual con límites de seguridad',
    ],
  },
};

// ══════════════════════════════════════════════════════
//  GERMAN
// ══════════════════════════════════════════════════════
const de: Record<string, ProjectTranslation> = {
  'arbitraje': {
    description:
      'Multi-Exchange Kryptowährungs-Arbitrage-Detektor mit Bellman-Ford- und Triangular-Modi, plus Live-Swap-Executor.',
    longDescription:
      'Scant 9 Börsen (Binance, Bitget, Bybit, Coinbase, OKX, KuCoin, Kraken, Gate.io, MEXC) nach Preisineffizienzen. ' +
      'Verwendet Bellman-Ford Kürzester-Pfad-Algorithmus und trianguläre Arbitrage-Erkennung. Enthält ein Swapper-Modul zur Trade-Ausführung, ' +
      'WebSocket L2 Orderbuch-Feeds, SDK-Bootstrapping für native Exchange-Integrationen und einen Echtzeit-Balance-Monitor.',
    highlights: [
      '4.000+ LOC Scanner mit graphbasierter Arbitrage-Erkennung',
      '9 Exchange-Integrationen mit 4 Balance-Provider-Backends',
      'Live-Swap-Executor mit Dry-Run- und Produktionsmodi',
      'WebSocket L2 partielles Orderbuch für Binance',
      'Portfolio-Monitor mit 1-Hop-Bridge-Pricing',
    ],
  },
  'oai-code-evaluator': {
    description:
      'Konfigurierbare deklarative Regelengine zur Prüfung von LLM/Modell-Antworten über 5 Qualitätsdimensionen.',
    longDescription:
      'YAML-gesteuerter Evaluierungspipeline mit regelbasiertem Scoring über Anweisungen, Genauigkeit, Optimalität, ' +
      'Präsentation und Aktualität. Unterstützt Regex/Substring-Matching, Schwellenwert-Bedingungen, ' +
      'Ranking-Normalisierung, Rewrite-Nachbearbeitung und strukturierte Audit-Metadaten-Ausgabe.',
    highlights: [
      '6-stufiger Evaluierungspipeline (anpassen → Regeln → Ranking → umschreiben → validieren → Zusammenfassung)',
      'Deklarative YAML-Regeln mit Regex-, Substring- und Schwellenwert-Bedingungen',
      '5-Dimensionen-Scoring mit konfigurierbaren Idealen und Toleranzen',
      'Strukturierte JSON/YAML-Audit-Ausgabe',
    ],
  },
  'email-collector': {
    description:
      'IMAP-E-Mail-Sammler mit OAuth-Unterstützung und 5-Label-Klassifizierungssystem zur Anti-Phishing-Erkennung.',
    longDescription:
      'Multi-Account IMAP-Sammler mit Unterstützung für Gmail, Hotmail (MSAL OAuth Device-Flow) und Exchange. ' +
      'Klassifiziert E-Mails in Betrug/Verdächtig/Spam/Sauber/Unbekannt mit einer gewichteten Scoring-Engine ' +
      'mit 200+ Domain-Regeln, URL-Shortener-Erkennung, Telefon-Muster-Matching und Fuzzy-Deduplizierung.',
    highlights: [
      '5-Label-Klassifikator mit gewichtetem Scoring und harten Regeln',
      '200+ Domain-Klassifizierungsregeln',
      'OAuth Device-Flow für Hotmail/Outlook',
      'Fuzzy-Deduplizierung mit SimHash',
    ],
  },
  'real-estate': {
    description:
      'API-Integrations- und Web-Scraping-Tools für Immobilienplattformen (EasyBroker, Wiggot).',
    highlights: [
      '5.400+ LOC EasyBroker API-Client mit gleichzeitigen Downloads',
      'Playwright-basierter Wiggot-Scraper mit SSO-Handling',
      'Microsoft Fabric-Integration für Data Engineering',
    ],
  },
  'supplier-verifier': {
    description:
      'Automatisierte Firmenadress-Verifizierung und Lieferanten-Typ-Klassifizierung mittels Such-APIs und Fuzzy-Matching.',
    highlights: [
      'Fuzzy-Adressabgleich mit rapidfuzz',
      'Kategoriekeyword-Heuristiken mit Evidenz-Scoring',
      'Google CSE / SerpAPI-Integration',
    ],
  },
  'tls-compare': {
    description:
      'Automatisierte A/B-Medienvergleichstools zur Qualitätsbewertung mittels Browser-Automatisierung.',
    highlights: [
      'Seite-an-Seite Audiovergleich mit Playwright-Automatisierung',
      'Bildqualitätsvergleich mit Pixelanalyse',
    ],
  },
  'linux': {
    description:
      'Vollständige Windows → Pop!_OS Migrationsskripte mit Entwicklungsumgebungs-Bootstrap und VM-Setup.',
    highlights: [
      'Reproduzierbares Entwicklungsumgebungs-Bootstrap-Skript',
      'QEMU/KVM Windows VM-Erstellung',
      'System-Gesundheitscheck-Skript (CPU, RAM, Festplatte, Dev-Tools, Poetry-Umgebungen)',
    ],
  },
  'dataqbs-site': {
    description:
      'Diese Website — ein LinkedIn-ähnliches Portfolio mit RAG-KI-Chatbot, erstellt mit Astro + Svelte + Tailwind auf Cloudflare Pages.',
    highlights: [
      'RAG-Chatbot mit Vektor-Embeddings + Groq LLM-Streaming',
      'Wissenspipeline: Markdown → 58 Chunks mit 768-Dim Embeddings',
      'i18n (EN/ES/DE), Dunkelmodus, LinkedIn-ähnliches Layout',
      'Cloudflare Pages + Workers AI + KV-Speicher',
    ],
  },
  'memo-grid': {
    description:
      'Maker-Only Grid-Trading-Bot für ETH/BTC auf Binance mit HPO-optimierten Parametern und vollständigem Backtest-Framework.',
    longDescription:
      'Produktions-Grid-Trading-Microservice mit ccxt auf Binance Spot. Bietet Optuna-Hyperparameter-Optimierung (50K Versuche), ' +
      'Backtest-Engine mit realem Gebührenmodell, Attributionsanalyse (Alpha vs Beta Zerlegung), Monte-Carlo-Projektionen, ' +
      'und 22 Analysetools. Enthält FIFO-Bestandsverfolgung, adaptive Schrittgrößenbestimmung und systemd-Deployment-Support.',
    highlights: [
      'HPO mit 50.000 Optuna-Versuchen (TPE-Sampler) für ETH/BTC Grid-Parameter',
      'Backtest-Engine von 2017–2026 mit Maker-Gebührenmodell',
      'Attributionsanalyse: Alpha vs Beta Renditezerlegung',
      'Monte-Carlo-Projektionen mit Konfidenzintervallen',
      '33 Unit-Tests mit vollständiger Abdeckung',
    ],
  },
  'vca-audits': {
    description:
      'Enterprise PostgreSQL-Audit-Framework mit Template-DDL-Exporten, Schema-Analyse und ticketbasierter Sanierung.',
    longDescription:
      'Vollständiges Audit- und Schema-Management-Framework für Azure Database for PostgreSQL. ' +
      'Enthält pro-Objekt DDL-Export mit Nunjucks-Templates, automatisierte Schema-Erkennung, ' +
      'LLM-freundliche schema_knowledge.json-Generierung und 20+ ticketbasierte Datenbank-Verbesserungen ' +
      'in Index-Optimierung, FK-Bereinigung, Timestamp-Normalisierung und Stored-Procedure-Reviews.',
    highlights: [
      '20+ Tickets: Index-Optimierung, FK-Bereinigung, Schema-Umbenennungen, Timestamp-Korrekturen',
      'Template-basierter pro-Objekt DDL-Exporter (Nunjucks) für CI/CD-kompatible Snapshots',
      'Technische Design-Dokumente für 5+ Datenbanksysteme',
      'Regressionstestsuite für kritische Datenbankänderungen',
      'Automatisierte Stundenzettelgenerierung mit Harvest API',
    ],
  },
  'iroc-video-wall': {
    description:
      'Produktions-Mining-Performance-Dashboard mit 34 KPIs, Multi-Site-Umschaltung und KI-Chatbot für Freeport-McMoRan.',
    longDescription:
      'Streamlit-basiertes Produktionsüberwachungs-Dashboard für IROC-Operationen an 7 Freeport-McMoRan Bergbaustandorten. ' +
      'Zeigt Echtzeit-Metriken aus Snowflake und Azure Data Explorer (ADX), 34 KPIs zu Dig-Compliance, ' +
      'Brecher-Raten, Zykluszeiten und ROM-Tonnage. Enthält RAG-KI-Chatbot mit GitHub Copilot SDK, ' +
      'semantisches Modell mit 16 Geschäftsergebnissen pro Standort und Auto-Refresh alle 60 Sekunden.',
    highlights: [
      '34 KPIs über 7 Bergbaustandorte mit Echtzeit-Auto-Refresh',
      'KI-Chatbot mit RAG + GitHub Copilot SDK (kostenfrei für Enterprise)',
      'Semantisches Modell: 16 Geschäftsergebnisse × 7 Standorte mit ADX + Snowflake-Abfragen',
      'Docker-ready mit Azure Container App Deployment',
      '100% KPI-zu-Abfrage-Abdeckung verifiziert',
    ],
  },
  'ore-tracing': {
    description:
      'Physikbasierte Simulationsplattform zur Vorhersage von Mineralzusammensetzung und Massenfluss durch Bergbau-Verarbeitungskreisläufe.',
    longDescription:
      'End-to-End Erzverfolgungssystem, das Stockpile-Verhalten mit 3D-Blockmodellen simuliert und Mineralogie ' +
      'durch den Zerkleinerungskreislauf verfolgt (Sekundär-/Tertiärbrecher → Mühlen → Flotation). Bietet prädiktive ' +
      'Kalibrierung industrieller Bandwaagen mit Kalman-Filterung, Crush-out-Zeitschätzung, lag-basierte Propagationsmodelle ' +
      'und Nowcast-Simulation für mehrere Bergbaustandorte. Die Datenpipeline liest Sensordaten mit 1-Minuten-Auflösung ' +
      'aus einem Cloud Data Warehouse, führt Simulationen durch und schreibt verfolgte Mineralzustände für Downstream-Analytik zurück.',
    highlights: [
      'Physikbasierte 3D-Stockpile-Simulation mit Massenverfolgung auf Blockebene',
      'Mineralzusammensetzungsverfolgung durch Brecher → Mühle → Flotation Kreisläufe',
      'Kalman-Filter Bandwaagen-Korrektur mit Trägheitsgewichtung',
      'Nowcast- und Crush-out-Zeitvorhersage für operative Planung',
      'Multi-Standort-Deployment mit konfigurationsgesteuerter YAML-Architektur',
    ],
  },
  'mining-chatbot': {
    description:
      'Natural-Language-Chatbot zur Abfrage von ADX- und Snowflake-Bergbaudaten über 7 Standorte mit semantischem Modell.',
    highlights: [
      'Natural-Language-Abfragen für 16 Geschäftsergebnisse pro Standort',
      'ADX + Snowflake Dual-Datenquelle mit Sensor-Mappings',
      '7 Bergbaustandorte: Morenci, Bagdad, Sierrita, Safford, Climax, Henderson, Cerro Verde',
      'Regelbasierter Fallback wenn KI nicht verfügbar',
    ],
  },
  'arbextra': {
    description:
      'Cross-Exchange BTC/USDT Arbitrage-Scanner mit automatisch ausgelösten Taker-Orders und Portfolio-Monitor.',
    highlights: [
      'Scant mehrere Börsen nach BTC/USDT-Spread-Opportunitäten',
      'Konfigurierbarer Auto-Trigger mit Dry-Run- und Live-Modi',
      'Portfolio-PnL-Tracker mit Token-Baselines und CSV-Export',
      'Rebalance-Prozent-Feature mit Sicherheitsbegrenzung',
    ],
  },
};

export const projectTranslations: Record<string, Record<string, ProjectTranslation>> = {
  es,
  de,
};
