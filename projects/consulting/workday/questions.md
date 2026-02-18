# Open Questions — DESICO / HR Path / Quantum

> Track open questions and answers here. Update as responses come in.

## For DESICO (Client)

| # | Question | Priority | Status | Answer |
|---|---|---|---|---|
| D1 | **Compartir el archivo con el formato confirmado (columnas/mapping).** Sin esto no podemos avanzar con el diseño técnico. | 🔴 Critical | ⏳ Waiting | — |
| D2 | ¿Cuántas localidades/plantas se incluyen en el rollout 1 vs rollout 2? | High | ⏳ Waiting | — |
| D3 | ¿El archivo se generará diario, semanal, o por periodo de nómina? | High | ⏳ Waiting | — |
| D4 | ¿Existen tipos de tiempo especiales (sindicatos, turnos, extras)? | High | ⏳ Waiting | — |
| D5 | ¿Hay reglas específicas por tipo de trabajador (corporativo vs. planta)? | Medium | ⏳ Waiting | — |
| D6 | ¿Quién será el punto de contacto para UAT? | Medium | ⏳ Waiting | — |
| D7 | ¿El sistema origen puede generar archivos de prueba con datos reales anonimizados? | Medium | ⏳ Waiting | — |

## For HR Path (Workday)

| # | Question | Priority | Status | Answer |
|---|---|---|---|---|
| H1 | ¿Qué Web Service se usará — `Put_Time_Clock_Events` o `Submit_Time_Sheet`? | High | ⏳ Waiting | — |
| H2 | ¿Los Business Processes de time entry ya están configurados en IMPL1? | High | ⏳ Waiting | — |
| H3 | ¿Seguridad: se necesita ISU nuevo o se reutiliza uno existente? | High | ⏳ Waiting | — |
| H4 | ¿Las entradas y salidas (in/out) son parte del scope o es solo horas totales? | High | ⏳ Waiting | — |
| H5 | ¿Hay Time Entry Templates ya configurados? ¿Para qué tipos de tiempo? | Medium | ⏳ Waiting | — |
| H6 | ¿Se necesitan reportes custom o los estándar de Workday son suficientes? | Medium | ⏳ Waiting | — |

## For Quantum (Infra / PM)

| # | Question | Priority | Status | Answer |
|---|---|---|---|---|
| Q1 | ¿Fechas estimadas para tener el sFTP habilitado con credenciales? | High | ⏳ Waiting | — |
| Q2 | ¿Se usará una carpeta separada para Workday Studio? | Medium | ⏳ Waiting | — |
| Q3 | ¿Credenciales sFTP serán compartidas vía canal seguro (no email)? | Medium | ⏳ Waiting | — |

---

## Next Steps (Immediate)

1. **Esperar el archivo de DESICO** con el formato/mapping — es el blocker principal
2. Mientras tanto, revisar en IMPL1:
   - Time Entry Templates existentes
   - Business Processes de time tracking
   - Security groups y domains relacionados
   - Reportes disponibles
3. Dar seguimiento a Quantum para sFTP (deadline: Feb 23)
4. Preparar ideas preliminares de diseño para cuando llegue el archivo

## Ideas Preliminares (mientras esperamos el archivo)

- Proponer un **mapping template** estándar que DESICO pueda llenar
- Documentar los **time codes** que Workday ya soporta en IMPL1
- Definir la **estrategia de error handling** (archivo de errores en sFTP)
- Crear un **checklist de validación** para SIT y UAT
