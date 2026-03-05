/**
 * cv_translations.ts — Experience translations for ES / DE.
 *
 * Keyed by role index (matching the order in cv.ts experience array).
 * The ExperienceTimeline component uses these to show translated descriptions
 * and achievements when the locale is not 'en'.
 *
 * KEEP IN SYNC with cv.ts — if you add/reorder roles there, update here too.
 */

export interface ExperienceTranslation {
  description: string;
  achievements: string[];
}

// ══════════════════════════════════════════════════════
//  SPANISH
// ══════════════════════════════════════════════════════
const es: Record<number, ExperienceTranslation> = {
  // 0 — Hexaware Technologies
  0: {
    description:
      'Lideré la integración Snowflake → Azure SQL para operaciones mineras de Freeport-McMoRan. ' +
      'Desplegué pipelines de sincronización incremental, construí CLI de pruebas de regresión, optimicé vistas Snowflake, ' +
      'y desarrollé dashboards de producción y chatbots de IA para 7 sitios mineros.',
    achievements: [
      'Lideré la integración Snowflake → Azure SQL; desplegué pipeline de sincronización incremental de 14 tablas con procedimientos MERGE, programación cada 15 min, detección delta con HASH, verificación E2E (~590K filas) en DEV→TEST→PROD',
      'Diseñé cargas incrementales basadas en marca de agua usando timestamps de negocio y respaldos DW_MODIFY_TS para dashboards de Connected Operations',
      'Construí snowrefactor, CLI en Python para pruebas de regresión de vistas Snowflake: extracción automatizada de DDL, despliegue, comparación de esquemas y benchmarking en flujos CTE estilo dbt',
      'Optimicé vistas Snowflake mediante pushdown profundo de CTEs en arquitecturas UNION ALL (65s→9.7s, 5×). Benchmarké migración Snowflake→ADX: SENSOR_SNAPSHOT_GET 30s→0.15s (200×)',
      'Desarrollé IROC Video Wall (Streamlit, 7 sitios mineros, auto-refresh 60s, chat IA) y Chatbot de Operaciones Mineras (consultas NL sobre ADX+Snowflake). Docker, Azure App Service, Azure AD SSO',
      'Construí extracción de esquemas en 3 ambientes Azure SQL, infraestructura KQL/ADX (2 clusters, 20+ DBs por sitio), ejecución config-driven con auth Entra ID/Kerberos',
      'Aproveché GitHub Copilot (Enterprise) para arquitectura de pipelines, generación SQL, benchmarking y desarrollo de dashboards',
      'Construí simulación de stockpile basada en física con modelado 3D de bloques para trazado de mineral a través de circuitos de conminución (trituradoras → molinos → flotación). Seguimiento predictivo de mineralogía, calibración de básculas con filtrado Kalman y estimación de tiempos de crush-out en múltiples sitios mineros',
    ],
  },
  // 1 — dataqbs
  1: {
    description:
      'Consultoría independiente proporcionando BI, ingeniería de datos y soluciones de bases de datos para clientes de EE.UU. y LATAM. ' +
      'También construyendo proyectos internos de I+D: escáner de arbitraje cripto, bots de grid trading, motor de evaluación LLM, ' +
      'sistema de clasificación de correos, y este sitio portfolio con chatbot RAG.',
    achievements: [
      'Entregué ingeniería de datos para NewFire Global, VCA Animal Hospitals, C&A México, BCG, Moviro, Svitla, Quesos Navarro',
      'Construí MEMO-GRID: bot avanzado de grid trading con HPO Optuna (50K pruebas), multiplicador 23× BTC, análisis de atribución (95.7% alfa)',
      'Diseñé escáner de arbitraje cripto triangular con Bellman-Ford a través de 9 exchanges con ejecución de swaps en vivo',
      'Construí motor de reglas declarativo basado en YAML para auditoría de respuestas LLM con scoring en 5 dimensiones',
      'Implementé colector de correo IMAP multi-cuenta con clasificador de 5 etiquetas (anti-phishing, scoring de dominios)',
      'Creé este sitio portfolio (dataqbs.com) con chatbot RAG, embeddings vectoriales y streaming LLM con Groq',
    ],
  },
  // 2 — SVAM International
  2: {
    description:
      'Lideré migración de SQL Server on-prem y SSIS a Snowflake para analítica de certificaciones estudiantiles.',
    achievements: [
      'Lideré migración de SQL Server on-prem y SSIS a Snowflake, diseñando nuevos modelos fact/dimension para analítica de certificaciones estudiantiles',
      'Automaticé ingesta de JSON desde APIs de Salesforce hacia Snowflake usando Python',
      'Construí pruebas de validación y reconciliación de datos, asegurando precisión de carga end-to-end',
      'Entregué datasets curados vía SharePoint, mejorando la visibilidad para stakeholders académicos',
      'Soporté transformación de datos y scheduling mediante scripts custom y procesos controlados por CI',
    ],
  },
  // 3 — Svitla Systems
  3: {
    description:
      'Diseñé y desplegué el primer data warehouse en Azure SQL de la empresa para analítica de ventas en la nube.',
    achievements: [
      'Diseñé y desplegué el primer data warehouse en Azure SQL de la empresa para analítica de ventas en la nube',
      'Desarrollé paquetes SSIS para extracciones on-prem y orquesté actualizaciones con Azure Data Factory',
      'Construí modelos de datos star-schema flexibles para escalar según crecían las necesidades de reporteo',
      'Colaboré con equipos de BI para publicar dashboards de Power BI en Azure',
    ],
  },
  // 4 — Epikso Mexico
  4: {
    description:
      'Administré seguridad de Snowflake, ajuste de rendimiento e Infrastructure-as-Code para configuración automatizada de ambientes.',
    achievements: [
      'Administré seguridad de Snowflake, acceso basado en roles y ajuste de rendimiento',
      'Implementé Infrastructure-as-Code para configuración automatizada de ambientes',
      'Monitoreé rendimiento de consultas y optimicé almacenamiento/micro-particionamiento',
      'Integré pipelines CI/CD vía Bitbucket, mejorando el control de despliegues',
    ],
  },
  // 5 — Jabil (Data Technical Lead)
  5: {
    description:
      'Dirigí migración de Hadoop + Impala + SQL Server PDW a Snowflake en AWS para analítica de manufactura.',
    achievements: [
      'Dirigí migración de Hadoop + Impala + SQL Server PDW a Snowflake en AWS, habilitando analítica más rápida',
      'Construí orquestación streaming y basada en tareas usando funciones nativas de automatización de Snowflake',
      'Diseñé zonas de landing, staging y refinadas para ingesta y transformación escalable',
      'Soporté equipos distribuidos en la modernización de analítica de manufactura',
    ],
  },
  // 6 — 3Pillar Global
  6: {
    description:
      'Desarrollé integraciones de datos EDI y capas de reporteo para clientes empresariales.',
    achievements: [
      'Desarrollé integraciones de datos EDI y capas de reporteo con SQL Server, SSIS y SSRS',
      'Mantuve sincronización confiable de datos entre múltiples socios externos',
    ],
  },
  // 7 — HCL Technologies
  7: {
    description:
      'Migré y optimicé reportes Actuate hacia SSRS y SharePoint para reporteo empresarial.',
    achievements: [
      'Migré y optimicé reportes Actuate hacia SSRS y SharePoint',
      'Desarrollé lógica SQL de alto rendimiento para reportes empresariales',
    ],
  },
  // 8 — Jabil (Database Analyst II)
  8: {
    description:
      'Creé y mantuve flujos ETL integrando sistemas Oracle, SAP y MySQL con confiabilidad de bases de datos 24/7.',
    achievements: [
      'Creé y mantuve flujos ETL usando SSIS, integrando sistemas Oracle, SAP y MySQL',
      'Aseguré confiabilidad 24/7 de bases de datos y optimización de rendimiento',
    ],
  },
  // 9 — C&A México
  9: {
    description:
      'Diseñé cubos OLAP y reportes interactivos para analítica retail a través de unidades de negocio.',
    achievements: [
      'Diseñé cubos OLAP (SSAS) y reportes interactivos SSRS para analítica retail',
      'Construí flujos ETL desde mainframes y tiendas regionales hacia data warehouse centralizado',
      'Mantuve ambientes SQL de alto rendimiento a través de unidades de negocio',
    ],
  },
  // 10 — FIRMEPLUS
  10: {
    description:
      'Desarrollo de software y bases de datos con PHP, SQL Server y MySQL.',
    achievements: [
      'Desarrollo de software y bases de datos (PHP, SQL Server, MySQL)',
    ],
  },
  // 11 — Jabil Circuit de México
  11: {
    description:
      'Apoyo en desarrollo de bases de datos y aplicaciones web.',
    achievements: [
      'Apoyé desarrollo de bases de datos y aplicaciones web',
    ],
  },
};

// ══════════════════════════════════════════════════════
//  GERMAN
// ══════════════════════════════════════════════════════
const de: Record<number, ExperienceTranslation> = {
  // 0 — Hexaware Technologies
  0: {
    description:
      'Leitete die Snowflake → Azure SQL Integration fuer Freeport-McMoRan Bergbauoperationen. ' +
      'Bereitete inkrementelle Sync-Pipelines, baute CLI fuer Regressionstests, optimierte Snowflake-Views ' +
      'und entwickelte Produktions-Dashboards und KI-Chatbots fuer 7 Bergbaustandorte.',
    achievements: [
      'Leitete die Snowflake → Azure SQL Integration; bereitete inkrementelle Sync-Pipeline fuer 14 Tabellen mit MERGE-Prozeduren, 15-Min-Planung, HASH-Delta-Erkennung, E2E-Verifizierung (~590K Zeilen) in DEV→TEST→PROD',
      'Entwarf wasserzeichenbasierte inkrementelle Ladevorgaenge mit Business-Timestamps und DW_MODIFY_TS-Fallbacks fuer Connected Operations Dashboards',
      'Entwickelte snowrefactor, Python-CLI fuer Snowflake-View-Regressionstests: automatisierter DDL-Pull, Deployment, Schema-Vergleich und Benchmarking in dbt-Style CTE-Workflows',
      'Optimierte Snowflake-Views durch tiefes CTE-Pushdown in UNION ALL-Architekturen (65s→9,7s, 5×). Benchmarkte Snowflake→ADX-Migration: SENSOR_SNAPSHOT_GET 30s→0,15s (200×)',
      'Entwickelte IROC Video Wall (Streamlit, 7 Bergbaustandorte, 60s Auto-Refresh, KI-Chat) und Mining Operations Chatbot (NL-Abfragen ueber ADX+Snowflake). Docker, Azure App Service, Azure AD SSO',
      'Entwickelte Schema-Extraktion ueber 3 Azure SQL-Umgebungen, KQL/ADX-Infrastruktur (2 Cluster, 20+ Standort-DBs), konfigurationsgesteuerte Ausfuehrung mit Entra ID/Kerberos-Auth',
      'Nutzte GitHub Copilot (Enterprise) fuer Pipeline-Architektur, SQL-Generierung, Benchmarking und Dashboard-Entwicklung',
      'Entwickelte physikbasierte Stockpile-Simulation mit 3D-Blockmodellierung fuer Erzverfolgung durch Zerkleinerungskreislaeufe (Brecher → Muehlen → Flotation). Praediktive Mineralogie-Verfolgung, Bandwaagen-Kalibrierung mit Kalman-Filterung und Crush-out-Zeitschaetzung ueber mehrere Bergbaustandorte',
    ],
  },
  // 1 — dataqbs
  1: {
    description:
      'Unabhaengige Beratung fuer BI, Data Engineering und Datenbankloesungen fuer US- und LATAM-Kunden. ' +
      'Baut auch interne F&E-Projekte: Krypto-Arbitrage-Scanner, Grid-Trading-Bots, LLM-Bewertungsengine, ' +
      'E-Mail-Klassifizierungssystem und diese Portfolio-Website mit RAG-Chatbot.',
    achievements: [
      'Lieferte Data Engineering fuer NewFire Global, VCA Animal Hospitals, C&A Mexico, BCG, Moviro, Svitla, Quesos Navarro',
      'Entwickelte MEMO-GRID: fortgeschrittenen Grid-Trading-Bot mit Optuna HPO (50K Versuche), 23× BTC-Multiplikator, Attributionsanalyse (95,7% Alpha)',
      'Entwarf Bellman-Ford & triangulaeren Krypto-Arbitrage-Scanner ueber 9 Boersen mit Live-Swap-Ausfuehrung',
      'Entwickelte deklarative YAML-gesteuerte Regelengine fuer LLM-Antwortpruefung mit 5-Dimensionen-Bewertung',
      'Implementierte Multi-Account-IMAP-E-Mail-Sammler mit 5-Label-Klassifikator (Anti-Phishing, Domain-Bewertung)',
      'Erstellte diese Portfolio-Website (dataqbs.com) mit RAG-Chatbot, Vektor-Embeddings und Groq-LLM-Streaming',
    ],
  },
  // 2 — SVAM International
  2: {
    description:
      'Leitete Migration von On-Prem SQL Server und SSIS zu Snowflake fuer Studentenzertifizierungs-Analytik.',
    achievements: [
      'Leitete Migration von On-Prem SQL Server und SSIS zu Snowflake, Entwurf neuer Fact/Dimension-Modelle fuer Studentenzertifizierungs-Analytik',
      'Automatisierte JSON-Aufnahme von Salesforce-APIs in Snowflake mit Python',
      'Entwickelte Datenvalidierungs- und Abgleichtests zur Sicherstellung der End-to-End-Ladegenauigkeit',
      'Lieferte kuratierte Datensaetze ueber SharePoint zur Verbesserung der Sichtbarkeit fuer akademische Stakeholder',
      'Unterstuetzte Datentransformation und Scheduling durch benutzerdefinierte Skripte und CI-gesteuerte Prozesse',
    ],
  },
  // 3 — Svitla Systems
  3: {
    description:
      'Entwarf und implementierte das erste Azure SQL Data Warehouse des Unternehmens fuer Cloud-basierte Vertriebsanalytik.',
    achievements: [
      'Entwarf und implementierte das erste Azure SQL Data Warehouse des Unternehmens fuer Cloud-basierte Vertriebsanalytik',
      'Entwickelte SSIS-Pakete fuer On-Prem-Extraktionen und orchestrierte Updates mit Azure Data Factory',
      'Erstellte flexible Star-Schema-Datenmodelle zur Skalierung nach wachsenden Reporting-Anforderungen',
      'Zusammenarbeit mit BI-Teams zur Veroeffentlichung von Power BI-Dashboards auf Azure',
    ],
  },
  // 4 — Epikso Mexico
  4: {
    description:
      'Verwaltete Snowflake-Sicherheit, Performance-Tuning und Infrastructure-as-Code fuer automatisierte Umgebungseinrichtung.',
    achievements: [
      'Verwaltete Snowflake-Sicherheit, rollenbasierten Zugriff und Performance-Tuning',
      'Implementierte Infrastructure-as-Code fuer automatisierte Umgebungseinrichtung',
      'Ueberwachte Abfrageleistung und optimierte Speicher/Micro-Partitioning',
      'Integrierte CI/CD-Pipelines ueber Bitbucket zur Verbesserung der Deployment-Kontrolle',
    ],
  },
  // 5 — Jabil (Data Technical Lead)
  5: {
    description:
      'Leitete Migration von Hadoop + Impala + SQL Server PDW zu Snowflake auf AWS fuer Fertigungsanalytik.',
    achievements: [
      'Leitete Migration von Hadoop + Impala + SQL Server PDW zu Snowflake auf AWS fuer schnellere Analytik',
      'Entwickelte Streaming- und aufgabenbasierte Orchestrierung mit nativen Snowflake-Automatisierungsfunktionen',
      'Entwarf Landing-, Staging- und Refined-Zonen fuer skalierbare Aufnahme und Transformation',
      'Unterstuetzte verteilte Teams bei der Modernisierung der Fertigungsanalytik',
    ],
  },
  // 6 — 3Pillar Global
  6: {
    description:
      'Entwickelte EDI-Datenintegrationen und Reporting-Schichten fuer Unternehmenskunden.',
    achievements: [
      'Entwickelte EDI-Datenintegrationen und Reporting-Schichten mit SQL Server, SSIS und SSRS',
      'Sicherstellte zuverlaessige Datensynchronisation mit mehreren externen Partnern',
    ],
  },
  // 7 — HCL Technologies
  7: {
    description:
      'Migrierte und optimierte Actuate-Berichte in SSRS und SharePoint fuer Unternehmensreporting.',
    achievements: [
      'Migrierte und optimierte Actuate-Berichte in SSRS und SharePoint',
      'Entwickelte performante SQL-Logik fuer Unternehmensreporting',
    ],
  },
  // 8 — Jabil (Database Analyst II)
  8: {
    description:
      'Erstellte und wartete ETL-Workflows zur Integration von Oracle-, SAP- und MySQL-Systemen mit 24/7-Datenbankzuverlaessigkeit.',
    achievements: [
      'Erstellte und wartete ETL-Workflows mit SSIS zur Integration von Oracle-, SAP- und MySQL-Systemen',
      'Sicherstellte 24/7-Datenbankzuverlaessigkeit und Leistungsoptimierung',
    ],
  },
  // 9 — C&A México
  9: {
    description:
      'Entwarf OLAP-Cubes und interaktive Berichte fuer Einzelhandelsanalytik ueber Geschaeftsbereiche hinweg.',
    achievements: [
      'Entwarf OLAP-Cubes (SSAS) und interaktive SSRS-Berichte fuer Einzelhandelsanalytik',
      'Erstellte ETL-Workflows von Mainframes und regionalen Filialen zum zentralen Data Warehouse',
      'Wartete Hochleistungs-SQL-Umgebungen ueber Geschaeftsbereiche hinweg',
    ],
  },
  // 10 — FIRMEPLUS
  10: {
    description:
      'Software- und Datenbankentwicklung mit PHP, SQL Server und MySQL.',
    achievements: [
      'Software- und Datenbankentwicklung (PHP, SQL Server, MySQL)',
    ],
  },
  // 11 — Jabil Circuit de México
  11: {
    description:
      'Unterstuetzte Datenbank- und Webanwendungsentwicklung.',
    achievements: [
      'Unterstuetzte Datenbank- und Webanwendungsentwicklung',
    ],
  },
};

export const experienceTranslations: Record<string, Record<number, ExperienceTranslation>> = {
  es,
  de,
};
