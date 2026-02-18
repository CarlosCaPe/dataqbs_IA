# Project Plan — Workday Time Tracking Integration (DESICO)

> Last updated: Feb 18, 2026

## Timeline Summary

| Phase | Start | End | Status |
|---|---|---|---|
| 1. Planning | Jan 29 | Feb 23 | 🟡 In Progress |
| 2. Architecture & Development | Feb 10 | Mar 25 | 🟡 In Progress |
| 3. Testing (UAT) | Mar 2 | Apr 3 | ⬜ Not Started |
| 4. Deployment & Rollout | Apr 6 | Jun 1 | ⬜ Not Started |

---

## Phase 1: Planning

| # | Task | Duration | Start | End | Owner | Area | % | Status | Notes |
|---|---|---|---|---|---|---|---|---|---|
| 1.1 | Presentar planificación | — | Jan 29 | Jan 29 | HR Path | PM | 100% | ✅ Done | |
| 1.2 | Añadir anexo de contrato actual | 10d | Feb 2 | Feb 6 | Quantum/HRP | Ventas | 100% | ✅ Done | |
| 1.3 | Concretar fecha de inicio | 10d | Feb 2 | Feb 13 | Quantum/HRP | PM | 100% | ✅ Done | |
| 1.4 | Dar acceso a equipo a tenants (IMPL1) | 1d | Jan 29 | Feb 6 | HR Path | PM | 100% | ✅ Done | |
| 1.5 | **Confirmar formato de archivo (columnas/mapping)** | — | Feb 5 | Feb 13 | **DESICO** | Técnica | 20% | 🟡 IP | ⚠️ Esperando archivo de DESICO |
| 1.6 | Configurar/Habilitar acceso a sFTP | 10d | Feb 16 | Feb 23 | Quantum | PM | 20% | 🟡 IP | Quantum crea sFTP, definir credenciales para DESICO y HR Path |
| 1.7 | Generar archivos de prueba con formato confirmado | — | Jan 14 | Feb 20 | DESICO | Técnica | 20% | 🟡 IP | Depende de 1.5 |

## Phase 2: Architecture & Development

| # | Task | Duration | Start | End | Owner | Area | % | Status | Notes |
|---|---|---|---|---|---|---|---|---|---|
| 2.1 | Kick-off (revisión planificación con equipo) | 1d | Feb 10 | Feb 10 | Quantum/HRP | PM | 80% | 🟡 IP | |
| 2.2 | Revisar seguridad en IMPL1 (entrada/salida, extras) | 7d | Feb 10 | Feb 17 | HR Path | Funcional | 0% | 🟡 IP | Corporativos, sindicatos |
| 2.3 | Revisar Business Processes en IMPL1 | 7d | Feb 10 | Feb 17 | HR Path | Funcional | 0% | 🟡 IP | |
| 2.4 | Validación de tiempos en IMPL1 | 3d | Feb 10 | Feb 17 | HR Path | Funcional | 0% | 🟡 IP | |
| 2.5 | Revisar reportes en IMPL1 | 7d | Feb 10 | Feb 17 | HR Path | Funcional | 0% | 🟡 IP | |
| 2.6 | Habilitar servicio web IMPL1 | 7d | Feb 10 | Feb 17 | HR Path | Técnica | 50% | 🟡 IP | |
| 2.7 | Análisis y diseño de la integración | 5d | Feb 16 | Feb 20 | HR Path | Técnica | 30% | 🟡 IP | |
| 2.8 | **Desarrollar paquete en Workday Studio** | 18d | Feb 20 | Mar 18 | HR Path | Técnica | 0% | ⬜ NS | Core development |
| 2.9 | Publicar y configurar integración en IMPL1 | 2d | Mar 18 | Mar 19 | HR Path | Técnica | 0% | ⬜ NS | |
| 2.10 | SIT — Smoke Testing | 4d | Mar 20 | Mar 25 | HR Path | Técnica | 0% | ⬜ NS | |

## Phase 3: Testing

| # | Task | Duration | Start | End | Owner | Area | % | Status | Notes |
|---|---|---|---|---|---|---|---|---|---|
| 3.1 | Crear escenarios/casos de prueba | 15d | Mar 2 | Mar 23 | Quantum/HRP | Técnica/Funcional | 0% | ⬜ NS | |
| 3.2 | **UAT — Pruebas de aceptación (Planta)** | 5d | Mar 26 | Apr 3 | Quantum | Técnica/Funcional | 0% | ⬜ NS | |
| 3.3 | Preparar documentación técnica | 2d | Apr 9 | Apr 10 | HR Path | Técnica | 0% | ⬜ NS | |

## Phase 4: Deployment & Rollout

| # | Task | Duration | Start | End | Owner | Area | % | Status | Notes |
|---|---|---|---|---|---|---|---|---|---|
| 4.1 | **Go / No-Go meeting** | 1d | Apr 3 | Apr 3 | Quantum/HRP | Técnica/Funcional | 0% | ⬜ NS | |
| 4.2 | Mover IMPL1 → Sandbox | 2d | Apr 6 | Apr 8 | HR Path | Técnica | 0% | ⬜ NS | |
| 4.3 | Smoke testing Sandbox | 1d | Apr 8 | Apr 9 | HR Path | Técnica | 0% | ⬜ NS | |
| 4.4 | Mover Sandbox → Producción | 2d | Apr 9 | Apr 10 | HR Path | Técnica | 0% | ⬜ NS | |
| 4.5 | Ocultar visibilidad para otras localidades | 1d | Apr 10 | Apr 10 | HR Path | Técnica | 0% | ⬜ NS | Solo rollout 1 visible |
| 4.6 | **Rollout 1** | 1d | Apr 13 | Apr 13 | HR Path | Técnica/Funcional | 0% | ⬜ NS | |
| 4.7 | Hypercare Rollout 1 | 14d | Apr 13 | Apr 27 | HR Path | Técnica/Funcional | 0% | ⬜ NS | |
| 4.8 | **Rollout 2** | — | May 4 | May 4 | HR Path | Técnica/Funcional | 0% | ⬜ NS | |
| 4.9 | Hypercare Rollout 2 | 14d | May 4 | May 18 | HR Path | Técnica/Funcional | 0% | ⬜ NS | |
| 4.10 | **Go Live completo** | 8 sem | Apr 6 | ~Jun 1 | HR Path | Técnica/Funcional | 0% | ⬜ NS | |

---

## Critical Path

```
Archivo formato (DESICO) → Diseño integración → Studio Dev (18d) → SIT → UAT → Go/No-Go → Rollout 1
```

⚠️ **Blocker actual:** Tarea 1.5 — DESICO debe confirmar el formato de archivo (columnas/mapping). Sin esto no se puede avanzar con el diseño técnico detallado.

## Legend

- ✅ Done | 🟡 IP = In Progress | ⬜ NS = Not Started | 🔴 Blocked
