# Integration Analysis — Workday Time Tracking (DESICO)

> Status: Draft — waiting for DESICO source file format to refine

## 1. Integration Pattern

| Aspect | Detail |
|---|---|
| **Direction** | Inbound (Source → Workday) |
| **Method** | Workday Studio (EIB or custom) |
| **Transport** | sFTP (managed by Quantum) |
| **Format** | Flat file (CSV/delimited) — TBD per DESICO format |
| **Frequency** | TBD — likely daily or per pay period |
| **API** | `Put_Time_Clock_Events` or `Submit_Time_Sheet` WS |

## 2. Functional Scope

### 2.1 Time Structure Validation
- Verify Workday time entry templates support the time types sent by DESICO
- Time code mapping: source system codes → Workday time entry codes
- Handle: regular hours, overtime, shifts, absences (if applicable)

### 2.2 Business Rules to Validate
- [ ] Maximum hours per day/week
- [ ] Overtime calculation rules
- [ ] Shift differential rules
- [ ] Holiday / rest day rules
- [ ] Union-specific rules (sindicatos)
- [ ] Corporate vs. plant workforce differences

### 2.3 Business Processes (Approvals)
- [ ] Time entry submission BP
- [ ] Manager approval flow
- [ ] Escalation rules
- [ ] Delegation / proxy approvals
- [ ] Auto-approve scenarios (if any)

### 2.4 Reports for Reconciliation
- [ ] Loaded vs. source record count
- [ ] Rejected records report
- [ ] Hours summary by employee / period
- [ ] Payroll impact preview
- [ ] Audit trail report

## 3. Data Flow

```
┌─────────────┐    ┌──────────────┐    ┌────────────────────┐    ┌──────────┐
│   DESICO    │───▶│  sFTP Server │───▶│  Workday Studio    │───▶│ Workday  │
│ Source Sys  │    │  (Quantum)   │    │  Integration Pkg   │    │   HCM    │
└─────────────┘    └──────────────┘    │                    │    │          │
                                       │ 1. Parse file      │    │ Time     │
                                       │ 2. Validate codes  │    │ Tracking │
                                       │ 3. Map fields      │    │          │
                                       │ 4. Call WS         │    │ BP →     │
                                       │ 5. Log results     │    │ Approval │
                                       └────────────────────┘    └──────────┘
```

## 4. Expected File Structure (Preliminary)

> ⚠️ **Waiting on DESICO to confirm the actual format.** Below is a typical structure for time integrations:

| Column | Description | Example | Required |
|---|---|---|---|
| Employee_ID | Worker identifier | `EMP001` | Yes |
| Date | Work date | `2026-02-18` | Yes |
| Time_Code | Type of time | `REG`, `OT`, `HOL` | Yes |
| Hours | Number of hours | `8.00` | Yes |
| In_Time | Clock-in time | `08:00` | Depends |
| Out_Time | Clock-out time | `17:00` | Depends |
| Cost_Center | Where to charge | `CC-100` | Maybe |
| Comments | Notes | `Holiday makeup` | No |

## 5. Key Technical Considerations

### 5.1 Security (IMPL1)
- Integration System User (ISU) setup
- Domain security for time tracking
- Constrained vs. unconstrained access
- Entry/exit types — confirm if extras involved

### 5.2 Error Handling
- Row-level error capture and logging
- Retry mechanism for transient failures
- Email notification on failure
- Error file output to sFTP for DESICO review

### 5.3 Population Segmentation
- **Rollout 1:** Initial population (TBD — likely one plant/location)
- **Rollout 2:** Remaining populations
- Visibility restriction via security segments until rollout

### 5.4 Conciliation
- Source count vs. Workday loaded count
- Hash/checksum validation (if supported)
- Delta detection for reprocessing

## 6. Workday Components to Review in IMPL1

- [ ] Time Entry Templates (configured time types)
- [ ] Time Code Groups
- [ ] Eligibility Rules
- [ ] Time Calculation Tags
- [ ] Business Process: Submit Time Sheet
- [ ] Business Process: Time Entry approval
- [ ] Security Groups: Time entry, time admin
- [ ] Custom Reports: time reconciliation
- [ ] Web Service: enabled and configured
- [ ] Integration System User: created with proper permissions

## 7. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| File format not confirmed | Blocks development (18d task) | Escalate to DESICO — critical path |
| Time codes don't match | Wrong time entries loaded | Mapping validation in SIT |
| BP not configured correctly | Approvals fail | Review BP in IMPL1 before dev |
| Union-specific rules missed | Compliance issues | Document all rule variations |
| sFTP access delayed | Can't test end-to-end | Quantum to prioritize setup |
