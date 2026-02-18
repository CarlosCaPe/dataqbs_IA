# Workday Time Tracking — Guía de Configuración

> **Audiencia:** Consultor funcional configurando Workday Time Tracking para un proyecto de integración de tiempos inbound.
> **Versión API de Workday:** v44.1 (2025R1) — [WSDL](https://community.workday.com/sites/default/files/file-hosting/productionapi/Time_Tracking/v44.1/Time_Tracking.wsdl) | [Schema](https://community.workday.com/sites/default/files/file-hosting/productionapi/Time_Tracking/v44.1/Time_Tracking.xsd)
> **Última actualización:** 18 Feb 2026
> **Estado:** Documento vivo — actualizar conforme se completen las configuraciones.

---

## Tabla de Contenidos

1. [Por Dónde Empezar — Mapa de Configuración](#1-por-dónde-empezar--mapa-de-configuración)
2. [Tareas de Configuración Paso a Paso](#2-tareas-de-configuración-paso-a-paso)
3. [Referencia de Tareas de Búsqueda en Workday](#3-referencia-de-tareas-de-búsqueda-en-workday)
4. [Checklist Pre-Configuración (Preguntas Clave)](#4-checklist-pre-configuración-preguntas-clave)
5. [Entregables Sugeridos](#5-entregables-sugeridos)
6. [Primeras 48 Horas — Qué Hacer Primero](#6-primeras-48-horas--qué-hacer-primero)
7. [Referencia de Operaciones del Web Service](#7-referencia-de-operaciones-del-web-service)
8. [Recursos Adicionales](#8-recursos-adicionales)

---

## 1. Por Dónde Empezar — Mapa de Configuración

Piensa en la configuración de Time Tracking como un setup por capas. Cada capa depende de la anterior. Sigue este orden:

```
┌──────────────────────────────────────────────────────────────────┐
│  CAPA 1: FUNDAMENTOS                                             │
│  Time Entry Codes → Time Code Groups → Time Entry Templates      │
├──────────────────────────────────────────────────────────────────┤
│  CAPA 2: REGLAS                                                  │
│  Time Calculations → Reglas de Tiempo Extra → Redondeo/Gracia    │
├──────────────────────────────────────────────────────────────────┤
│  CAPA 3: POBLACIÓN                                               │
│  Reglas de Elegibilidad → Horarios → Asignación de Horarios      │
├──────────────────────────────────────────────────────────────────┤
│  CAPA 4: PROCESO                                                 │
│  Business Processes (Aprobaciones) → Notificaciones → Alertas    │
├──────────────────────────────────────────────────────────────────┤
│  CAPA 5: SEGURIDAD                                               │
│  Security Groups → Domain Security → ISU (Usuario de Integración)│
├──────────────────────────────────────────────────────────────────┤
│  CAPA 6: REPORTEO E INTEGRACIÓN                                  │
│  Reportes → Integration System → sFTP → Config de Web Service    │
└──────────────────────────────────────────────────────────────────┘
```

> **Principio clave:** Siempre configura de abajo hacia arriba (Capa 1 primero). No puedes asignar un Time Entry Template sin tener Time Entry Codes, y no puedes configurar Time Calculations sin un Template.

---

## 2. Tareas de Configuración Paso a Paso

### CAPA 1: Fundamentos — Time Entry Codes, Groups y Templates

#### 2.1 Time Entry Codes

**Qué son:** Los tipos individuales de tiempo que los trabajadores pueden reportar (Regular, Tiempo Extra, Festivo, Incapacidad, etc.).

**Cómo encontrarlos en Workday:**
- Barra de búsqueda → escribe: `Maintain Time Entry Codes`
- Esta tarea te permite crear, ver y editar todos los códigos de tiempo en tu tenant.

**Qué configurar:**
- [ ] Revisar los time entry codes existentes — ¿están representados todos los tipos de tiempo del sistema origen?
- [ ] Crear los códigos faltantes (ej. `REG` = Regular, `OT` = Tiempo Extra, `HOL` = Festivo, `EXTRA` = Horas Extra)
- [ ] Para cada código, definir:
  - **Name** (nombre amigable para el usuario)
  - **Code** (para mapeo de integración)
  - **Time Entry Code Type** (Hours, Amount, Quantity)
  - **Worktag requirements** (centro de costo, proyecto, etc.)

**Referencia:** [Workday Admin Guide — Time Entry Codes](https://doc.workday.com/admin-guide/en-us/time-tracking/setting-up-time-tracking/tmk1466530755620.html) (requiere login en Workday Community)

> **Tip:** Primero exporta la lista actual. Busca → `Time Entry Codes` (como reporte) para ver lo que ya está configurado.

---

#### 2.2 Time Code Groups

**Qué son:** Agrupaciones lógicas de Time Entry Codes. Controlan *cuáles* códigos están disponibles para *cuáles* poblaciones.

**Cómo encontrarlos en Workday:**
- Barra de búsqueda → escribe: `Create Time Code Group` o `Maintain Time Code Groups`

**Qué configurar:**
- [ ] Crear grupos que correspondan a tus poblaciones (ej. "Planta México", "Corporativo México")
- [ ] Asignar los Time Entry Codes relevantes a cada grupo
- [ ] Determinar si diferentes tipos de trabajadores (sindicalizados vs. corporativos) necesitan grupos distintos

> **Por qué importa:** Si el sistema origen manda un código de tiempo que no está en el Time Code Group del trabajador, Workday lo va a rechazar.

---

#### 2.3 Time Entry Templates

**Qué son:** Definen *cómo* los trabajadores capturan tiempo — por horas, por entrada/salida de reloj, por proyecto, etc. El template determina la experiencia del usuario y qué campos están disponibles.

**Cómo encontrarlos en Workday:**
- Barra de búsqueda → escribe: `Create Time Entry Template` o `Maintain Time Entry Templates`

**Qué configurar:**
- [ ] Decidir el tipo de template:
  - **Enter Time by Duration** — el trabajador captura total de horas por día
  - **Enter Time by In/Out** — el trabajador registra entrada/salida (timestamps)
  - **Enter Time by Project** — el trabajador registra tiempo contra proyectos
- [ ] Asignar Time Code Groups al template
- [ ] Establecer Time Entry Code por default (si aplica)
- [ ] Configurar campos requeridos vs. opcionales (ej. centro de costo, comentarios)
- [ ] Determinar si hay necesidad **híbrida** (algunos trabajadores por in/out, otros por duración)

> **Decisión crítica:** ¿El sistema origen envía **total de horas** (duración) o **eventos de entrada/salida** (timestamps)? Esto determina tu tipo de template y la operación de web service que vas a usar.

---

### CAPA 2: Reglas — Cálculos, Tiempo Extra, Redondeo

#### 2.4 Time Calculations

**Qué son:** Reglas que Workday aplica al tiempo reportado para producir tiempo calculado (ej. "primeras 8 horas = regular, hora 9+ = tiempo extra").

**Cómo encontrarlos en Workday:**
- Barra de búsqueda → escribe: `Maintain Time Calculations`
- También: `Create Time Calculation` para reglas nuevas

**Qué configurar:**
- [ ] Revisar cálculos existentes — ¿cubren tus escenarios?
- [ ] Definir reglas para:
  - **Tiempo extra diario** (ej. > 8 horas/día = TE en México per LFT Art. 67)
  - **Tiempo extra semanal** (ej. > 48 horas/semana)
  - **Doble/triple** (ej. prima dominical, festivos per LFT Art. 73-75)
  - **Diferencial de turno nocturno** (si aplica)
- [ ] Establecer el **orden de cálculo** (la prioridad importa cuando las reglas se traslapan)
- [ ] Definir **Time Calculation Tags** para etiquetar resultados (ej. "Calculated_OT", "Calculated_REG")

**Consideraciones específicas para México (Ley Federal del Trabajo):**
- Semana laboral regular: 48 horas (6 días × 8 hrs) para turno diurno
- Tiempo extra: primeras 9 hrs/semana al 200%, más allá al 300% (Art. 67-68)
- Prima dominical: 25% adicional (Art. 71)
- Festivos: pago doble si se trabaja (Art. 75)
- Turno nocturno: 7 horas = jornada completa (Art. 60)

> **Tip:** Busca → `Time Calculation Tags` para ver/crear tags que etiquetan los bloques de tiempo calculado.

---

#### 2.5 Reglas de Tiempo Extra

**Cómo encontrarlas en Workday:**
- Las reglas de tiempo extra normalmente son parte de **Time Calculations** (ver 2.4)
- Busca → `Maintain Time Calculations` → busca los cálculos relacionados con overtime

**Qué configurar:**
- [ ] Umbral de tiempo extra diario
- [ ] Umbral de tiempo extra semanal
- [ ] Reglas diferentes por población (sindicato vs. corporativo)
- [ ] Reglas de días consecutivos (si aplica)
- [ ] Tasas de tiempo extra en festivos

---

#### 2.6 Reglas de Redondeo y Gracia

**Qué son:** Reglas que redondean los tiempos de entrada/salida (ej. registra a las 8:07 → se redondea a 8:00) y periodos de gracia (ej. 5 minutos de tolerancia para retardos).

**Cómo encontrarlos en Workday:**
- Barra de búsqueda → escribe: `Maintain Rounding Rules` o busca dentro de Time Calculations

**Qué configurar:**
- [ ] Intervalo de redondeo (5 min, 15 min, etc.)
- [ ] Dirección del redondeo (más cercano, arriba, abajo)
- [ ] Periodo de gracia para llegadas tarde
- [ ] Periodo de gracia para salidas tempranas
- [ ] Reglas diferentes por turno/población

> **Nota:** Las reglas de redondeo solo aplican si usas entrada **In/Out (reloj checador)**. Si el origen manda total de horas, el redondeo lo maneja el sistema origen.

---

### CAPA 3: Población — Elegibilidad, Horarios, Asignaciones

#### 2.7 Reglas de Elegibilidad

**Qué son:** Determinan *cuáles trabajadores* son elegibles para time tracking y *cuál* Time Entry Template les toca.

**Cómo encontrarlos en Workday:**
- Barra de búsqueda → escribe: `Maintain Time Tracking Eligibility Rules`

**Qué configurar:**
- [ ] Definir criterios de elegibilidad:
  - Por **tipo de trabajador** (empleado, contingente)
  - Por **ubicación** (plantas México, sitios específicos)
  - Por **job profile** o **job family**
  - Por **organización supervisora**
  - Por **empresa** (para multi-entidad)
- [ ] Asignar el **Time Entry Template** correcto por grupo de elegibilidad
- [ ] Asignar el **Time Code Group** correcto por grupo de elegibilidad
- [ ] Establecer el **Time Entry Calendar** (qué periodos capturan los trabajadores)

> **Para rollout por fases:** Usa las reglas de elegibilidad para controlar qué poblaciones pueden ver y usar Time Tracking. Habilita primero la población del Rollout 1, luego expande.

---

#### 2.8 Horarios de Trabajo

**Qué son:** Definen el patrón de trabajo esperado (horarios de turno, días laborales, días de descanso).

**Cómo encontrarlos en Workday:**
- Barra de búsqueda → escribe: `Create Work Schedule Calendar` o `Maintain Work Schedule Calendars`
- También: `Work Schedule Calendar Patterns` para turnos rotativos

**Qué configurar:**
- [ ] Definir patrones de horario (ej. Lun-Vie 8:00-17:00, rotativo 3 turnos)
- [ ] Establecer días de descanso (típicamente domingo en México)
- [ ] Configurar tiempos de comida (periodos de alimento)
- [ ] Manejar horarios especiales (nocturno = 7 hrs, mixto = 7.5 hrs per LFT)
- [ ] Crear **Ad Hoc Schedules** para excepciones (cobertura en días festivos, etc.)

---

#### 2.9 Asignación de Horarios

**Cómo encontrarlos en Workday:**
- Barra de búsqueda → escribe: `Assign Work Schedule`
- Para carga masiva: usa `Import_Ad_Hoc_Schedules` o `Assign_Work_Schedule` web service

**Qué configurar:**
- [ ] Asignar horarios a trabajadores u organizaciones
- [ ] Determinar si las asignaciones son individuales o a nivel organización
- [ ] Planear los cambios de horario (rotaciones de turno)

---

### CAPA 4: Proceso — Business Processes y Aprobaciones

#### 2.10 Business Processes (BPs)

**Qué son:** Definiciones de flujo de trabajo para cómo las entradas de tiempo pasan por aprobación, cálculo y posting.

**Cómo encontrarlos en Workday:**
- Barra de búsqueda → escribe: `Business Process Type` → filtra por Time Tracking
- BPs clave a buscar:
  - `Enter Time` (puede aparecer como `Submit Time` o `Submit Timesheet` en algunos tenants)
  - `Time Clock Event` (para in/out)
  - `Correct Time Entry` (puede aparecer como `Edit Time Entry`)
  - `Time Request`

**Qué configurar:**
- [ ] Revisar el BP de **Enter Time**:
  - ¿Quién puede iniciar? (trabajador, manager, integración)
  - Pasos de aprobación (manager, skip-level, HR)
  - Condiciones de auto-aprobación (si hay)
  - Reglas de delegación
  - Destinatarios de notificaciones
- [ ] Revisar el BP de **Time Clock Event** (si usas in/out):
  - ¿Procesamiento automático después del evento de reloj?
  - Manejo de excepciones por checadas faltantes
- [ ] Definir **reglas de excepción**:
  - Alertas de checada faltante
  - Alertas de umbral de tiempo extra
  - Tiempo no aprobado al cierre de periodo

> **Tip:** Busca → `View Business Process` y escribe "Time" para ver todos los BPs de tiempo configurados actualmente.

---

#### 2.11 Notificaciones y Alertas

**Cómo encontrarlos en Workday:**
- Dentro de cada definición de Business Process → pestaña de Notifications
- También: Busca → `Create Alert` para alertas operativas

**Qué configurar:**
- [ ] Notificación al manager cuando se envía tiempo a aprobación
- [ ] Notificación al trabajador cuando el tiempo es aprobado/rechazado
- [ ] Alerta de escalamiento para tiempo no aprobado después de X días
- [ ] Alerta de umbral de tiempo extra al manager
- [ ] Alerta de entrada de tiempo faltante

---

### CAPA 5: Seguridad

#### 2.12 Security Groups y Domain Security

**Cómo encontrarlos en Workday:**
- Barra de búsqueda → escribe: `View Security Group` o `Maintain Domain Security Policies`
- Dominios relevantes: `Time Tracking`, `Worker Data: Time Tracking`, `Time Clock Events`

**Qué configurar:**
- [ ] Revisar los **security groups** con acceso a entrada/aprobación de tiempo:
  - `Time Entry` — ¿quién puede capturar tiempo?
  - `Time Approval` — ¿quién puede aprobar?
  - `Time Admin` — ¿quién puede corregir/sobreescribir?
- [ ] **Integration System User (ISU):**
  - Busca → `Create Integration System User`
  - Asignar a un security group con:
    - Acceso `Get` y `Put` al dominio de Time Tracking
    - Acceso a las organizaciones relevantes
  - Este ISU será usado por la integración de Workday Studio para llamar web services
- [ ] **Domain Security Policies:**
  - Busca → `Maintain Domain Security Policies` → filtra por "Time"
  - Asegúrate que el security group del ISU tenga acceso a:
    - Dominio `Time Tracking`
    - Dominio `Worker Data: Time`
    - `Integration: Build` (para Studio)
    - `Integration: Process` (para correr integraciones)
- [ ] Después de los cambios → Busca: `Activate Pending Security Policy Changes` para aplicar

> **Importante:** Los cambios de seguridad no toman efecto hasta que los actives. Siempre activa primero en IMPL1, valida y luego promueve.

---

#### 2.13 Setup del Integration System User (ISU)

**Paso a paso:**

1. Busca → `Create Integration System User`
   - Username: `ISU_TIME_INTEGRATION` (o según tu convención de nombres)
   - Establece un password fuerte (se usa para sFTP/Studio)
   - Desmarca "Require New Password at Next Sign In"

2. Busca → `Create Security Group` (tipo: Integration System Security Group)
   - Nombre: `ISSG_TIME_INTEGRATION`
   - Agrega el ISU como miembro

3. Busca → `Maintain Domain Security Policies`
   - Agrega el nuevo ISSG a los dominios relevantes (ver 2.12)

4. Busca → `Activate Pending Security Policy Changes`

5. Prueba: Inicia sesión como el ISU y verifica que tenga acceso a las áreas de time tracking

---

### CAPA 6: Reporteo e Integración

#### 2.14 Reportes

**Cómo encontrarlos en Workday:**
- Busca → `Create Custom Report` o revisa los existentes: `All Time Entry Reports`
- Reportes estándar útiles:
  - `Time Clock Events` — eventos de reloj crudos
  - `Time Blocks` — tiempo reportado y calculado
  - `Time Entry Exceptions` — errores, checadas faltantes
  - `Workers Missing Time` — seguimiento de cumplimiento

**Qué crear/configurar:**
- [ ] **Reporte de Conciliación:** Conteo del origen vs. conteo cargado en Workday por periodo
- [ ] **Reporte de Rechazos:** Registros que fallaron validación (qué trabajadores, qué códigos, por qué)
- [ ] **Resumen de Horas:** Total de horas por trabajador, código de tiempo, periodo
- [ ] **Reporte de Tiempo Extra:** Trabajadores que exceden umbrales de TE
- [ ] **Reporte de Estado de Aprobación:** Aprobaciones pendientes por manager

> **Tip:** Usa el **Custom Report Builder** de Workday (Busca → `Create Custom Report`). Data sources: `All Workers with Time Block` o `Time Clock Events`.

---

#### 2.15 Integración — Configuración del Web Service

**Cómo encontrarlos en Workday:**
- Busca → `View Integration System` o `Create Integration System`
- Para Studio: Busca → `Workday Studio`

**Operaciones clave del web service para este proyecto (v44.1):**

| Operación | Caso de Uso | Dirección |
|---|---|---|
| `Import_Time_Clock_Events` | Cargar eventos de entrada/salida del origen | **Recomendado para cargas masivas** |
| `Put_Time_Clock_Events` | Cargar eventos de reloj individuales | Tiempo real o lotes pequeños |
| `Import_Reported_Time_Blocks` | Cargar total de horas (duración) | **Recomendado para tiempo basado en duración** |
| `Put_Reported_Time_Blocks_for_Worker` | Cargar tiempo por trabajador | Escala pequeña (no recomendado para integraciones) |
| `Get_Time_Requests` | Obtener solicitudes de tiempo | Outbound si se necesita |
| `Get_Calculated_Time_Blocks` | Obtener tiempo calculado | Outbound para conciliación |
| `Assign_Work_Schedule` | Asignar horarios vía integración | Setup inicial o masivo |

> **Referencia:** [Time_Tracking Web Service v44.1](https://community.workday.com/sites/default/files/file-hosting/productionapi/Time_Tracking/v44.1/Time_Tracking.html)

**¿Qué operación usar?**
- Si el origen envía **timestamps de entrada/salida** → `Import_Time_Clock_Events`
- Si el origen envía **total de horas por día** → `Import_Reported_Time_Blocks`
- Para **eventos individuales en tiempo real** → `Put_Time_Clock_Events`

---

## 3. Referencia de Tareas de Búsqueda en Workday

Usa la barra de búsqueda global de Workday (arriba de cualquier página) para encontrar estas tareas. Escribe el nombre exacto o palabras clave.

### Tareas de Configuración

| Buscar | Términos Alternativos | Qué Hace |
|---|---|---|
| `Maintain Time Entry Codes` | `time entry code`, `time code` | Ver/crear/editar códigos de tiempo |
| `Create Time Code Group` | `time code group` | Agrupar códigos por población |
| `Create Time Entry Template` | `time entry template`, `time template` | Definir cómo capturan tiempo los trabajadores |
| `Maintain Time Calculations` | `time calculation`, `calc rule` | Ver/crear reglas de cálculo |
| `Maintain Time Calculation Tags` | `time calc tag`, `calculation tag` | Etiquetar resultados de tiempo calculado |
| `Maintain Time Tracking Eligibility Rules` | `eligibility`, `time eligibility` | Definir quién tiene time tracking |
| `Create Work Schedule Calendar` | `work schedule`, `schedule calendar` | Definir patrones de turno |
| `Assign Work Schedule` | `schedule assignment` | Asignar horarios a trabajadores |
| `Maintain Rounding Rules` | `rounding`, `time rounding` | Configuración de redondeo de reloj |

### Tareas de Business Process

| Buscar | Qué Hace |
|---|---|
| `View Business Process` | Revisar configuración de BP existente |
| `Edit Business Process` | Modificar pasos de aprobación, condiciones |
| `Business Process Type` → filtrar "Time" | Ver todos los BPs relacionados con tiempo |
| `Create Condition Rule` | Crear reglas para enrutamiento de BP |

### Tareas de Seguridad

| Buscar | Qué Hace |
|---|---|
| `Create Integration System User` | Crear ISU para integración |
| `Create Security Group` | Crear ISSG para el ISU |
| `Maintain Domain Security Policies` | Dar acceso a dominios |
| `Activate Pending Security Policy Changes` | Aplicar cambios de seguridad |
| `View Security Group` | Revisar setup de seguridad actual |

### Tareas de Reporteo

| Buscar | Qué Hace |
|---|---|
| `Create Custom Report` | Crear reportes nuevos |
| `Time Entry Audit` | Revisar actividad de captura de tiempo |
| `Workers Missing Time` | Encontrar quién no ha capturado tiempo |
| `Time Blocks` | Ver tiempo reportado/calculado |

### Tareas de Integración

| Buscar | Qué Hace |
|---|---|
| `Workday Studio` | Abrir el IDE de Studio (si está configurado) |
| `Launch Integration` | Disparar integraciones manualmente |
| `View Integration Events` | Ver historial de ejecuciones de integración |
| `Create Integration System` | Registrar nueva integración |

> **¿No encuentras una tarea?** Algunas tareas dependen de tu rol de seguridad. Si no la encuentras, pídele a tu admin de Workday (Quantum o HR Path) que verifique que tus security groups incluyan las áreas funcionales necesarias.

---

## 4. Checklist Pre-Configuración (Preguntas Clave)

Antes de tocar cualquier configuración, consigue respuestas a estas preguntas. Comparte esto con el cliente / líder de proyecto.

### A. Método de Captura de Tiempo

| # | Pregunta | Opciones | Respuesta |
|---|---|---|---|
| A1 | ¿Cómo registran tiempo los trabajadores en el sistema origen? | Reloj físico / lector de credencial / biométrico / captura manual / app móvil | |
| A2 | ¿El origen envía timestamps de entrada/salida o total de horas? | Entrada/Salida (timestamps) / Duración (total de horas) | |
| A3 | ¿Los descansos/comidas se registran como eventos separados? | Sí (in/out para descansos) / No (deducción automática) | |
| A4 | ¿Hay evento de reloj para entrada Y salida, o solo uno? | Ambos entrada + salida / Solo entrada / Solo salida | |

### B. Tipos y Códigos de Tiempo

| # | Pregunta | Opciones | Respuesta |
|---|---|---|---|
| B1 | ¿Qué tipos de tiempo maneja el sistema origen? | Regular / TE / Festivo / Incapacidad / Vacaciones / Nocturno / etc. | |
| B2 | ¿Hay códigos diferentes para diferentes poblaciones? | Iguales para todos / Diferentes por sindicato / ubicación / etc. | |
| B3 | ¿El tiempo extra lo calcula el origen o lo debe calcular Workday? | Lo calcula el origen / Lo calcula Workday | |

### C. Población y Horarios

| # | Pregunta | Opciones | Respuesta |
|---|---|---|---|
| C1 | ¿Cuántas poblaciones de trabajadores distintas hay? | Número + descripción | |
| C2 | ¿Cuáles son los horarios de trabajo? | Diurno / Nocturno / Rotativo / Mixto | |
| C3 | ¿Cuál es la semana laboral estándar? | 48 hrs (6 días) / 40 hrs (5 días) / Otro | |
| C4 | ¿Hay reglas específicas por sindicato? | Sí (¿cuáles sindicatos?) / No | |
| C5 | ¿Qué población va en Rollout 1 vs. 2? | Listado | |

### D. Integración y Frecuencia

| # | Pregunta | Opciones | Respuesta |
|---|---|---|---|
| D1 | ¿Con qué frecuencia se enviarán los archivos? | Tiempo real / Diario / Semanal / Por periodo de nómina | |
| D2 | ¿Cuál es el periodo de nómina? | Semanal / Quincenal / Mensual | |
| D3 | ¿Qué formato de archivo? | CSV / XML / Ancho fijo / JSON | |
| D4 | ¿Qué encoding del archivo? | UTF-8 / Latin-1 / Otro | |
| D5 | ¿Cómo se identifican los trabajadores? | ID de Empleado / # de Gafete / CURP / RFC | |

### E. Aprobaciones y Excepciones

| # | Pregunta | Opciones | Respuesta |
|---|---|---|---|
| E1 | ¿Quién aprueba el tiempo? | Manager directo / Supervisor / RH / Auto-aprobación | |
| E2 | ¿Hay escalamiento si el tiempo no se aprueba? | Sí (después de X días) / No | |
| E3 | ¿Qué pasa con las checadas faltantes? | Corrige el manager / Corrige el trabajador / Alerta + manual | |
| E4 | ¿Se permiten excepciones/sobreescrituras? | Sí (¿quién puede?) / No | |

### F. Específico de México (Ley Federal del Trabajo)

| # | Pregunta | Opciones | Respuesta |
|---|---|---|---|
| F1 | ¿Qué tipos de jornada aplican? | Diurna (8h) / Nocturna (7h) / Mixta (7.5h) | |
| F2 | ¿Se requiere prima dominical (25%)? | Sí / No | |
| F3 | ¿Cuáles son los días festivos obligatorios? | Listado per Art. 74 LFT | |
| F4 | ¿Cómo se paga el tiempo extra? | 200% primeras 9h/semana, 300% más allá / Otro | |
| F5 | ¿Hay CCTs (Contratos Colectivos de Trabajo) con reglas especiales? | Sí (detalles) / No | |

---

## 5. Entregables Sugeridos

### 5.1 Documento de Requerimientos de Negocio (BRD)

| Sección | Contenido |
|---|---|
| Visión General | Alcance del proyecto, objetivos, criterios de éxito |
| Stakeholders | Roles y responsabilidades |
| Requerimientos | Requerimientos funcionales con prioridades (MoSCoW) |
| Supuestos | Lo que asumimos como verdadero |
| Restricciones | Técnicas, de timeline, de presupuesto |
| Fuera de Alcance | Lo que NO está incluido |
| Firma | Aprobación del cliente |

### 5.2 User Stories + Criterios de Aceptación

Formato ejemplo:

```
US-001: Importar Eventos de Reloj Checador
  Como sistema de integración,
  Quiero importar eventos de reloj checador desde el archivo en sFTP,
  Para que el tiempo de los trabajadores quede registrado en Workday para procesamiento de nómina.

  Criterios de Aceptación:
  ✅ Todos los eventos válidos se crean en Workday
  ✅ Los registros inválidos se logean con detalle del error
  ✅ Los eventos duplicados se detectan y se omiten
  ✅ El archivo de errores se deposita en sFTP para revisión del equipo origen
  ✅ Se envía email resumen al admin después de cada corrida
```

### 5.3 Matriz de Mapeo de Códigos de Tiempo

| Código Origen | Descripción Origen | Workday Time Entry Code | Descripción Workday | Time Code Group | Notas |
|---|---|---|---|---|---|
| `01` | Regular | `REG` | Horas Regulares | Planta México | |
| `02` | Tiempo Extra | `OT_DOUBLE` | Tiempo Extra 200% | Planta México | Primeras 9h/semana |
| `03` | Tiempo Extra Triple | `OT_TRIPLE` | Tiempo Extra 300% | Planta México | Más allá de 9h |
| `04` | Festivo | `HOL` | Festivo Trabajado | Todos | Per Art. 74 LFT |
| ... | ... | ... | ... | ... | |

### 5.4 Mapeo de Campos (Integración)

| Campo Origen | Campo Workday | Elemento WS | Requerido | Transformación |
|---|---|---|---|---|
| `Employee_ID` | Worker Reference | `Worker_Reference` | Sí | Prefijar con `EMP_` si es necesario |
| `Date` | Time Date | `Date` | Sí | Formato: `YYYY-MM-DD` |
| `Clock_In` | Clock Event Time (In) | `Time_Clock_Moment` | Sí | ISO 8601 con timezone |
| `Clock_Out` | Clock Event Time (Out) | `Time_Clock_Moment` | Sí | ISO 8601 con timezone |
| `Time_Code` | Time Entry Code | `Time_Entry_Code_Reference` | Sí | Mapear vía tabla de lookup |
| ... | ... | ... | ... | ... |

---

## 6. Primeras 48 Horas — Qué Hacer Primero

### Hora 0-4: Descubrimiento y Acceso

- [ ] **Obtener acceso a IMPL1** — confirma que puedes loguearte y buscar tareas
- [ ] **Verificar tu rol de seguridad** — ¿puedes acceder a las tareas de configuración de time tracking?
- [ ] **Exportar el estado actual:**
  - Corre: reporte de `Time Entry Codes` → exporta a Excel
  - Corre: reporte de `Time Code Groups` → exporta
  - Corre: reporte de `Time Entry Templates` → exporta
  - Nota: Busca → `View Business Process` → "Enter Time" → screenshot/exporta
- [ ] **Documenta lo que ya existe** — IMPL1 puede tener configuración parcial de una fase anterior

### Hora 4-8: Revisión de Fundamentos

- [ ] Busca → `Maintain Time Entry Codes` → ¿Están definidos los códigos necesarios?
- [ ] Busca → `Maintain Time Code Groups` → revisa o crea grupos
- [ ] Busca → `Create Time Entry Template` → revisa existentes o determina qué tipo se necesita
- [ ] **Decisión:** ¿Basado en duración o In/Out? (Esto define todo lo que viene después)

### Hora 8-16: Reglas y Población

- [ ] Busca → `Maintain Time Calculations` → revisa reglas existentes
- [ ] Busca → `Maintain Time Tracking Eligibility Rules` → revisa quién es elegible
- [ ] Busca → `Create Work Schedule Calendar` → revisa horarios existentes
- [ ] **Mapea los tipos de tiempo del origen** a códigos de Workday (aunque no tengas el archivo, usa la lista de códigos como hipótesis)
- [ ] Identifica gaps: códigos faltantes, reglas faltantes, horarios faltantes

### Hora 16-24: Business Process y Seguridad

- [ ] Busca → `View Business Process` → "Enter Time" → documenta el flujo actual
- [ ] Revisa la cadena de aprobación: ¿quién aprueba? ¿cuántos niveles?
- [ ] Busca → `Create Integration System User` → verifica si ya existe un ISU
- [ ] Revisa domain security para los dominios de time tracking
- [ ] Documenta cualquier **pregunta funcional** que surja (agrégala a [questions.md](questions.md))

### Hora 24-48: Documentación y Comunicación

- [ ] **Haz el borrador del mapeo de códigos** (mejor estimación con lo que hayas aprendido)
- [ ] **Haz el borrador del BRD** con lo que ya sabes
- [ ] **Envía las preguntas** al cliente (del checklist de arriba)
- [ ] **Envía actualización de estatus** al equipo: "Esto encontré, esto falta"
- [ ] **Planea siguientes pasos** basado en las respuestas

---

## 7. Referencia de Operaciones del Web Service

Del [Workday Time_Tracking Web Service v44.1](https://community.workday.com/sites/default/files/file-hosting/productionapi/Time_Tracking/v44.1/Time_Tracking.html):

| Operación | Descripción | Mejor Para |
|---|---|---|
| `Import_Time_Clock_Events` | Cargar lotes grandes de eventos de entrada/salida | **Inbound masivo — recomendado para este proyecto si usas in/out** |
| `Import_Reported_Time_Blocks` | Importar bloques de tiempo (duración) de terceros | **Inbound masivo — recomendado si usas total de horas** |
| `Put_Time_Clock_Events` | Agregar eventos de reloj individuales | Tiempo real o lotes pequeños |
| `Put_Reported_Time_Blocks_for_Worker` | Crear/editar bloques de tiempo por trabajador | Escala pequeña — **no recomendado para integraciones** |
| `Assign_Work_Schedule` | Importar asignaciones de horario | Cargas masivas de horarios |
| `Import_Ad_Hoc_Schedules` | Cargar bloques de horario masivamente | Una sola vez o infrecuente |
| `Get_Calculated_Time_Blocks` | Obtener tiempo calculado | Conciliación outbound |
| `Get_Time_Requests` | Obtener solicitudes de tiempo | Outbound si se necesita |
| `Put_Time_Requests` | Crear/actualizar solicitudes de tiempo | Si el origen maneja solicitudes de tiempo libre |

---

## 8. Recursos Adicionales

### Documentación Oficial (Workday Community — requiere login)

- [Workday Admin Guide: Setting Up Time Tracking](https://doc.workday.com/admin-guide/en-us/time-tracking/setting-up-time-tracking/tmk1466530755620.html)
- [Workday Admin Guide: Time Tracking Concepts](https://doc.workday.com/admin-guide/en-us/time-tracking/time-tracking-concepts/tmk1466530805752.html)
- [Time_Tracking Web Service API v44.1](https://community.workday.com/sites/default/files/file-hosting/productionapi/Time_Tracking/v44.1/Time_Tracking.html)
- [Descarga WSDL](https://community.workday.com/sites/default/files/file-hosting/productionapi/Time_Tracking/v44.1/Time_Tracking.wsdl)
- [Descarga XSD Schema](https://community.workday.com/sites/default/files/file-hosting/productionapi/Time_Tracking/v44.1/Time_Tracking.xsd)

### Tips de Búsqueda en Workday Community

Si no encuentras una tarea específica mencionada aquí:
1. Ve a [community.workday.com](https://community.workday.com)
2. Busca el nombre de la tarea entre comillas
3. Filtra por "Documentation" o "Knowledge Articles"
4. Revisa el **Resource Center** para guías de admin por módulo

### Referencias de Ley Federal del Trabajo (México)

- [Ley Federal del Trabajo (LFT)](https://www.diputados.gob.mx/LeyesBiblio/pdf/LFT.pdf) — Texto oficial
- Art. 58-68: Jornada de trabajo, tiempo extra
- Art. 69-75: Días de descanso, festivos, primas
- Art. 76-81: Vacaciones

---

> **Disclaimer:** Los nombres de tareas y la navegación pueden variar ligeramente entre versiones de Workday y configuraciones de cada tenant. Si no encuentras una tarea por nombre exacto, intenta buscar por palabras clave (ej. "time entry" o "time code") — la búsqueda de Workday es flexible y te muestra tareas relacionadas. En caso de duda, pídele a tu admin de Workday que verifique que tu acceso de seguridad incluya el área funcional correspondiente.
