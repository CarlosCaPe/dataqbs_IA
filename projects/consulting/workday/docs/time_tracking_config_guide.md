# Workday Time Tracking — Configuration Guide

> **Audience:** Functional consultant configuring Workday Time Tracking for an inbound time integration project.
> **Workday API Version:** v44.1 (2025R1) — [WSDL](https://community.workday.com/sites/default/files/file-hosting/productionapi/Time_Tracking/v44.1/Time_Tracking.wsdl) | [Schema](https://community.workday.com/sites/default/files/file-hosting/productionapi/Time_Tracking/v44.1/Time_Tracking.xsd)
> **Last Updated:** Feb 18, 2026
> **Status:** Living document — update as configurations are completed.

---

## Table of Contents

1. [Where to Start — Configuration Roadmap](#1-where-to-start--configuration-roadmap)
2. [Step-by-Step Configuration Tasks](#2-step-by-step-configuration-tasks)
3. [Workday Search Tasks Reference](#3-workday-search-tasks-reference)
4. [Pre-Configuration Checklist (Questions to Ask)](#4-pre-configuration-checklist-questions-to-ask)
5. [Suggested Deliverables](#5-suggested-deliverables)
6. [First 48 Hours — What to Do First](#6-first-48-hours--what-to-do-first)
7. [Web Service Operations Reference](#7-web-service-operations-reference)
8. [Additional Resources](#8-additional-resources)

---

## 1. Where to Start — Configuration Roadmap

Think of Time Tracking configuration as a layered setup. Each layer depends on the one before it. Follow this order:

```
┌──────────────────────────────────────────────────────────────────┐
│  LAYER 1: FOUNDATION                                             │
│  Time Entry Codes → Time Code Groups → Time Entry Templates      │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 2: RULES                                                  │
│  Time Calculations → Overtime Rules → Rounding/Grace Rules       │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 3: POPULATION                                             │
│  Eligibility Rules → Work Schedules → Schedule Assignments       │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 4: PROCESS                                                │
│  Business Processes (Approvals) → Notifications → Alerts         │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 5: SECURITY                                               │
│  Security Groups → Domain Security → ISU (Integration User)      │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 6: REPORTING & INTEGRATION                                │
│  Reports → Integration System → sFTP → Web Service Config        │
└──────────────────────────────────────────────────────────────────┘
```

> **Key Principle:** Always configure bottom-up (Layer 1 first). You cannot assign a Time Entry Template without Time Entry Codes, and you cannot set up Time Calculations without a Template.

---

## 2. Step-by-Step Configuration Tasks

### LAYER 1: Foundation — Time Entry Codes, Groups & Templates

#### 2.1 Time Entry Codes

**What they are:** The individual types of time workers can report (Regular, Overtime, Holiday, Sick, etc.).

**How to find in Workday:**
- Search bar → type: `Maintain Time Entry Codes`
- This task lets you create, view, and edit all time entry codes in your tenant.

**What to configure:**
- [ ] Review existing time entry codes — are all time types from the source system represented?
- [ ] Create any missing codes (e.g., `REG` = Regular, `OT` = Overtime, `HOL` = Holiday, `EXTRA` = Extra Hours)
- [ ] For each code, define:
  - **Name** (user-friendly)
  - **Code** (for integration mapping)
  - **Time Entry Code Type** (Hours, Amount, Quantity)
  - **Worktag requirements** (cost center, project, etc.)

**Reference:** [Workday Admin Guide — Time Entry Codes](https://doc.workday.com/admin-guide/en-us/time-tracking/setting-up-time-tracking/tmk1466530755620.html) (requires Workday Community login)

> **Tip:** Export the current list first. Search → `Time Entry Codes` (as a report) to see what's already configured.

---

#### 2.2 Time Code Groups

**What they are:** Logical groupings of Time Entry Codes. They control *which* codes are available to *which* populations.

**How to find in Workday:**
- Search bar → type: `Create Time Code Group` or `Maintain Time Code Groups`

**What to configure:**
- [ ] Create groups that match your populations (e.g., "Mexico Plant Workers", "Corporate Mexico")
- [ ] Assign the relevant Time Entry Codes to each group
- [ ] Determine if different worker types (union vs. corporate) need different code groups

> **Why this matters:** If the source system sends a time code that isn't in the worker's Time Code Group, Workday will reject it.

---

#### 2.3 Time Entry Templates

**What they are:** Define *how* workers enter time — by hours, by in/out clock events, by project, etc. The template determines the user experience and what fields are available.

**How to find in Workday:**
- Search bar → type: `Create Time Entry Template` or `Maintain Time Entry Templates`

**What to configure:**
- [ ] Decide the template type:
  - **Enter Time by Duration** — worker enters total hours per day
  - **Enter Time by In/Out** — worker clocks in/out (timestamps)
  - **Enter Time by Project** — worker logs time against projects
- [ ] Assign Time Code Groups to the template
- [ ] Set default Time Entry Code (if applicable)
- [ ] Configure required vs. optional fields (e.g., cost center, comments)
- [ ] Determine if there's a **hybrid** need (some workers by in/out, others by duration)

> **Critical Decision:** Does the source system send **total hours** (duration) or **clock in/out events** (timestamps)? This determines your template type and the web service operation you'll use.

---

### LAYER 2: Rules — Calculations, Overtime, Rounding

#### 2.4 Time Calculations

**What they are:** Rules that Workday applies to reported time to produce calculated time (e.g., "first 8 hours = regular, hours 9+ = overtime").

**How to find in Workday:**
- Search bar → type: `Maintain Time Calculations`
- Also: `Create Time Calculation` for new rules

**What to configure:**
- [ ] Review existing calculations — do they cover your scenarios?
- [ ] Define rules for:
  - **Daily overtime** (e.g., > 8 hours/day = OT in Mexico per LFT Art. 67)
  - **Weekly overtime** (e.g., > 48 hours/week)
  - **Double/triple time** (e.g., Sunday premium, holidays per LFT Art. 73-75)
  - **Night shift differential** (if applicable)
- [ ] Set the **calculation order** (priority matters when rules overlap)
- [ ] Define **Time Calculation Tags** to label outputs (e.g., "Calculated_OT", "Calculated_REG")

**Mexico-specific considerations (Ley Federal del Trabajo):**
- Regular work week: 48 hours (6 days × 8 hrs) for day shift
- Overtime: first 9 hrs/week at 200%, beyond that at 300% (Art. 67-68)
- Sunday premium: 25% additional (Art. 71)
- Holidays: double pay if worked (Art. 75)
- Night shift: 7 hours = full shift (Art. 60)

> **Tip:** Search → `Time Calculation Tags` to see/create tags that label calculated time blocks.

---

#### 2.5 Overtime Rules

**How to find in Workday:**
- Overtime rules are typically part of **Time Calculations** (see 2.4)
- Search → `Maintain Time Calculations` → look for overtime-related calculations

**What to configure:**
- [ ] Daily overtime threshold
- [ ] Weekly overtime threshold
- [ ] Different rules per population (union vs. corporate)
- [ ] Consecutive day rules (if applicable)
- [ ] Holiday overtime rates

---

#### 2.6 Rounding & Grace Rules

**What they are:** Rules that round clock-in/out times (e.g., clock in at 8:07 → rounded to 8:00) and grace periods (e.g., 5-minute grace for tardiness).

**How to find in Workday:**
- Search bar → type: `Maintain Rounding Rules` or search within Time Calculations

**What to configure:**
- [ ] Rounding interval (5 min, 15 min, etc.)
- [ ] Rounding direction (nearest, up, down)
- [ ] Grace period for late arrivals
- [ ] Grace period for early departures
- [ ] Different rules per shift/population

> **Note:** Rounding rules only apply if you're using **In/Out (time clock)** entry. If the source sends total hours, rounding is handled by the source system.

---

### LAYER 3: Population — Eligibility, Schedules, Assignments

#### 2.7 Eligibility Rules

**What they are:** Determine *which workers* are eligible for time tracking and *which* Time Entry Template they get.

**How to find in Workday:**
- Search bar → type: `Maintain Time Tracking Eligibility Rules`

**What to configure:**
- [ ] Define eligibility criteria:
  - By **worker type** (employee, contingent worker)
  - By **location** (Mexico plants, specific sites)
  - By **job profile** or **job family**
  - By **supervisory organization**
  - By **company** (for multi-entity)
- [ ] Assign the correct **Time Entry Template** per eligibility group
- [ ] Assign the correct **Time Code Group** per eligibility group
- [ ] Set the **Time Entry Calendar** (which periods workers enter time for)

> **For phased rollout:** Use eligibility rules to control which populations can see and use Time Tracking. Enable Rollout 1 population first, then expand.

---

#### 2.8 Work Schedules

**What they are:** Define the expected work pattern (shift times, days of work, rest days).

**How to find in Workday:**
- Search bar → type: `Create Work Schedule Calendar` or `Maintain Work Schedule Calendars`
- Also: `Work Schedule Calendar Patterns` for rotating shifts

**What to configure:**
- [ ] Define schedule patterns (e.g., Mon-Fri 8:00-17:00, rotating 3-shift)
- [ ] Set rest days (typically Sunday in Mexico)
- [ ] Configure break times (meal periods)
- [ ] Handle special schedules (night shift = 7 hrs, mixed shift = 7.5 hrs per LFT)
- [ ] Create **Ad Hoc Schedules** for exceptions (holiday coverage, etc.)

---

#### 2.9 Schedule Assignments

**How to find in Workday:**
- Search bar → type: `Assign Work Schedule`
- For bulk: use `Import_Ad_Hoc_Schedules` or `Assign_Work_Schedule` web service

**What to configure:**
- [ ] Assign schedules to workers or organizations
- [ ] Determine if assignments are individual or org-level
- [ ] Plan for schedule changes (shift rotations)

---

### LAYER 4: Process — Business Processes & Approvals

#### 2.10 Business Processes (BPs)

**What they are:** Workflow definitions for how time entries flow through approval, calculation, and posting.

**How to find in Workday:**
- Search bar → type: `Business Process Type` → filter for Time Tracking
- Key BPs to find:
  - `Enter Time` (may appear as `Submit Time` or `Submit Timesheet` in some tenants)
  - `Time Clock Event` (for in/out)
  - `Correct Time Entry` (may appear as `Edit Time Entry`)
  - `Time Request`

**What to configure:**
- [ ] Review the **Enter Time** BP:
  - Who can initiate? (worker, manager, integration)
  - Approval steps (manager, skip-level, HR)
  - Auto-approve conditions (if any)
  - Delegation rules
  - Notification recipients
- [ ] Review the **Time Clock Event** BP (if using in/out):
  - Auto-processing after clock event?
  - Exception handling for missed punches
- [ ] Define **exception rules**:
  - Missed punch alerts
  - Overtime threshold alerts
  - Unapproved time at period close

> **Tip:** Search → `View Business Process` and enter "Time" to see all time-related BPs currently configured.

---

#### 2.11 Notifications & Alerts

**How to find in Workday:**
- Within each Business Process definition → Notifications tab
- Also: Search → `Create Alert` for operational alerts

**What to configure:**
- [ ] Manager notification when time is submitted for approval
- [ ] Worker notification when time is approved/rejected
- [ ] Escalation alert for unapproved time after X days
- [ ] Overtime threshold alert to manager
- [ ] Missing time entry alert

---

### LAYER 5: Security

#### 2.12 Security Groups & Domain Security

**How to find in Workday:**
- Search bar → type: `View Security Group` or `Maintain Domain Security Policies`
- Relevant domains: `Time Tracking`, `Worker Data: Time Tracking`, `Time Clock Events`

**What to configure:**
- [ ] Review **security groups** that have access to time entry/approval:
  - `Time Entry` — who can enter time?
  - `Time Approval` — who can approve?
  - `Time Admin` — who can correct/override?
- [ ] **Integration System User (ISU):**
  - Search → `Create Integration System User`
  - Assign to a security group with:
    - `Get` and `Put` access to Time Tracking domain
    - Access to relevant organizations
  - This ISU will be used by the Workday Studio integration to call web services
- [ ] **Domain Security Policies:**
  - Search → `Maintain Domain Security Policies` → filter by "Time"
  - Ensure the ISU's security group has access to:
    - `Time Tracking` domain
    - `Worker Data: Time` domain
    - `Integration: Build` (for Studio)
    - `Integration: Process` (to run integrations)
- [ ] After changes → Search: `Activate Pending Security Policy Changes` to apply

> **Important:** Security changes don't take effect until you activate them. Always activate in IMPL1 first, validate, then promote.

---

#### 2.13 Integration System User (ISU) Setup

**Step-by-step:**

1. Search → `Create Integration System User`
   - Username: `ISU_TIME_INTEGRATION` (or per your naming convention)
   - Set a strong password (use for sFTP/Studio)
   - Uncheck "Require New Password at Next Sign In"

2. Search → `Create Security Group` (type: Integration System Security Group)
   - Name: `ISSG_TIME_INTEGRATION`
   - Add the ISU as a member

3. Search → `Maintain Domain Security Policies`
   - Add the new ISSG to relevant domains (see 2.12)

4. Search → `Activate Pending Security Policy Changes`

5. Test: Log in as the ISU and verify access to time tracking areas

---

### LAYER 6: Reporting & Integration

#### 2.14 Reports

**How to find in Workday:**
- Search → `Create Custom Report` or review existing: `All Time Entry Reports`
- Standard useful reports to look for:
  - `Time Clock Events` — raw clock events
  - `Time Blocks` — reported and calculated time
  - `Time Entry Exceptions` — errors, missed punches
  - `Workers Missing Time` — compliance tracking

**What to create/configure:**
- [ ] **Reconciliation Report:** Source count vs. Workday loaded count per period
- [ ] **Rejection Report:** Records that failed validation (which workers, which codes, why)
- [ ] **Hours Summary:** Total hours by worker, time code, period
- [ ] **Overtime Report:** Workers exceeding OT thresholds
- [ ] **Approval Status Report:** Pending approvals by manager

> **Tip:** Use Workday's **Custom Report Builder** (Search → `Create Custom Report`). Data sources: `All Workers with Time Block` or `Time Clock Events`.

---

#### 2.15 Integration — Web Service Configuration

**How to find in Workday:**
- Search → `View Integration System` or `Create Integration System`
- For Studio: Search → `Workday Studio`

**Key web service operations for this project (v44.1):**

| Operation | Use Case | Direction |
|---|---|---|
| `Import_Time_Clock_Events` | Load clock in/out events from source | **Recommended for bulk loads** |
| `Put_Time_Clock_Events` | Load individual clock events | Real-time or small batches |
| `Import_Reported_Time_Blocks` | Load total hours (duration) | **Recommended for duration-based time** |
| `Put_Reported_Time_Blocks_for_Worker` | Load time per worker | Small scale (not recommended for integrations) |
| `Get_Time_Requests` | Retrieve time-off/requests | Outbound if needed |
| `Get_Calculated_Time_Blocks` | Retrieve calculated time | Outbound for reconciliation |
| `Assign_Work_Schedule` | Assign schedules via integration | Initial or bulk setup |

> **Reference:** [Time_Tracking Web Service v44.1](https://community.workday.com/sites/default/files/file-hosting/productionapi/Time_Tracking/v44.1/Time_Tracking.html)

**Which operation to use?**
- If source sends **clock in/out timestamps** → `Import_Time_Clock_Events`
- If source sends **total hours per day** → `Import_Reported_Time_Blocks`
- For **individual real-time events** → `Put_Time_Clock_Events`

---

## 3. Workday Search Tasks Reference

Use Workday's global search bar (top of any page) to find these tasks. Type the exact name or keywords.

### Configuration Tasks

| Search For | Alt. Search Terms | What It Does |
|---|---|---|
| `Maintain Time Entry Codes` | `time entry code`, `time code` | View/create/edit time entry codes |
| `Create Time Code Group` | `time code group` | Group codes for populations |
| `Create Time Entry Template` | `time entry template`, `time template` | Define how workers enter time |
| `Maintain Time Calculations` | `time calculation`, `calc rule` | View/create calculation rules |
| `Maintain Time Calculation Tags` | `time calc tag`, `calculation tag` | Label calculated time outputs |
| `Maintain Time Tracking Eligibility Rules` | `eligibility`, `time eligibility` | Define who gets time tracking |
| `Create Work Schedule Calendar` | `work schedule`, `schedule calendar` | Define shift patterns |
| `Assign Work Schedule` | `schedule assignment` | Assign schedules to workers |
| `Maintain Rounding Rules` | `rounding`, `time rounding` | Clock rounding configuration |

### Business Process Tasks

| Search For | What It Does |
|---|---|
| `View Business Process` | Review existing BP configuration |
| `Edit Business Process` | Modify approval steps, conditions |
| `Business Process Type` → filter "Time" | See all time-related BPs |
| `Create Condition Rule` | Build rules for BP routing |

### Security Tasks

| Search For | What It Does |
|---|---|
| `Create Integration System User` | Create ISU for integration |
| `Create Security Group` | Create ISSG for ISU |
| `Maintain Domain Security Policies` | Grant access to domains |
| `Activate Pending Security Policy Changes` | Apply security changes |
| `View Security Group` | Review current security setup |

### Reporting Tasks

| Search For | What It Does |
|---|---|
| `Create Custom Report` | Build new reports |
| `Time Entry Audit` | Review time entry activity |
| `Workers Missing Time` | Find who hasn't entered time |
| `Time Blocks` | View reported/calculated time |

### Integration Tasks

| Search For | What It Does |
|---|---|
| `Workday Studio` | Open Studio IDE (if configured) |
| `Launch Integration` | Manually trigger integrations |
| `View Integration Events` | See integration run history |
| `Create Integration System` | Register new integration |

> **Can't find a task?** Some tasks depend on your security role. If you can't find it, ask your Workday admin (Quantum or HR Path) to verify your security groups include the needed functional areas.

---

## 4. Pre-Configuration Checklist (Questions to Ask)

Before touching any configuration, get answers to these questions. Share this with the client / project lead.

### A. Time Entry Method

| # | Question | Options | Answer |
|---|---|---|---|
| A1 | How do workers record time at the source? | Physical clock / badge reader / biometric / manual entry / mobile app | |
| A2 | Does the source send clock in/out timestamps or total hours? | In/Out (timestamps) / Duration (total hours) | |
| A3 | Are breaks/meal periods tracked as separate events? | Yes (in/out for breaks) / No (auto-deducted) | |
| A4 | Is there a clock event for entry AND exit, or just one? | Both in + out / Entry only / Exit only | |

### B. Time Types & Codes

| # | Question | Options | Answer |
|---|---|---|---|
| B1 | What time types does the source system handle? | Regular / OT / Holiday / Sick / Vacation / Night / etc. | |
| B2 | Are there different codes for different populations? | Same for all / Different per union / location / etc. | |
| B3 | Is overtime calculated by the source or should Workday calculate it? | Source calculates / Workday calculates | |

### C. Population & Schedules

| # | Question | Options | Answer |
|---|---|---|---|
| C1 | How many distinct worker populations? | Number + description | |
| C2 | What are the work schedules? | Day / Night / Rotating / Mixed | |
| C3 | What is the standard work week? | 48 hrs (6 days) / 40 hrs (5 days) / Other | |
| C4 | Are there union-specific rules? | Yes (which unions?) / No | |
| C5 | Which population goes in Rollout 1 vs. 2? | List | |

### D. Integration & Frequency

| # | Question | Options | Answer |
|---|---|---|---|
| D1 | How often will files be sent? | Real-time / Daily / Weekly / Per pay period | |
| D2 | What is the pay period? | Weekly / Biweekly / Monthly | |
| D3 | What file format? | CSV / XML / Fixed-width / JSON | |
| D4 | What file encoding? | UTF-8 / Latin-1 / Other | |
| D5 | How are workers identified? | Employee ID / Badge # / National ID | |

### E. Approvals & Exceptions

| # | Question | Options | Answer |
|---|---|---|---|
| E1 | Who approves time? | Direct manager / Supervisor / HR / Auto-approve | |
| E2 | Is there an escalation if time is not approved? | Yes (after X days) / No | |
| E3 | What happens with missed punches? | Manager corrects / Worker corrects / Alert + manual | |
| E4 | Are there exceptions/overrides allowed? | Yes (who can?) / No | |

### F. Mexico-Specific (Ley Federal del Trabajo)

| # | Question | Options | Answer |
|---|---|---|---|
| F1 | Which shift types apply? | Day (8h) / Night (7h) / Mixed (7.5h) | |
| F2 | Is Sunday premium (25%) required? | Yes / No | |
| F3 | What are the mandatory holidays observed? | List per Art. 74 LFT | |
| F4 | How is overtime paid? | 200% first 9h/week, 300% beyond / Other | |
| F5 | Are there any CBAs (Contratos Colectivos) with special rules? | Yes (details) / No | |

---

## 5. Suggested Deliverables

### 5.1 Business Requirements Document (BRD)

| Section | Content |
|---|---|
| Overview | Project scope, objectives, success criteria |
| Stakeholders | Roles and responsibilities |
| Requirements | Functional requirements with priorities (MoSCoW) |
| Assumptions | What we're assuming to be true |
| Constraints | Technical, timeline, budget limitations |
| Out of Scope | What's NOT included |
| Sign-off | Client approval |

### 5.2 User Stories + Acceptance Criteria

Example format:

```
US-001: Import Time Clock Events
  As an integration system,
  I want to import time clock events from the sFTP file,
  So that workers' time is recorded in Workday for payroll processing.

  Acceptance Criteria:
  ✅ All valid clock events are created in Workday
  ✅ Invalid records are logged with error details
  ✅ Duplicate events are detected and skipped
  ✅ Error file is placed on sFTP for source team review
  ✅ Summary email is sent to admin after each run
```

### 5.3 Time Code Mapping Matrix

| Source Code | Source Description | Workday Time Entry Code | Workday Description | Time Code Group | Notes |
|---|---|---|---|---|---|
| `01` | Regular | `REG` | Regular Hours | Mexico Plant | |
| `02` | Overtime | `OT_DOUBLE` | Overtime 200% | Mexico Plant | First 9h/week |
| `03` | Overtime Triple | `OT_TRIPLE` | Overtime 300% | Mexico Plant | Beyond 9h |
| `04` | Holiday | `HOL` | Holiday Worked | All | Per Art. 74 LFT |
| ... | ... | ... | ... | ... | |

### 5.4 Field Mapping (Integration)

| Source Field | Workday Field | WS Element | Required | Transformation |
|---|---|---|---|---|
| `Employee_ID` | Worker Reference | `Worker_Reference` | Yes | Prefix with `EMP_` if needed |
| `Date` | Time Date | `Date` | Yes | Format: `YYYY-MM-DD` |
| `Clock_In` | Clock Event Time (In) | `Time_Clock_Moment` | Yes | ISO 8601 with timezone |
| `Clock_Out` | Clock Event Time (Out) | `Time_Clock_Moment` | Yes | ISO 8601 with timezone |
| `Time_Code` | Time Entry Code | `Time_Entry_Code_Reference` | Yes | Map via lookup table |
| ... | ... | ... | ... | ... |

---

## 6. First 48 Hours — What to Do First

### Hour 0-4: Discovery & Access

- [ ] **Get IMPL1 access** — confirm you can log in and search for tasks
- [ ] **Verify security role** — can you access time tracking configuration tasks?
- [ ] **Export current state:**
  - Run: `Time Entry Codes` report → export to Excel
  - Run: `Time Code Groups` report → export
  - Run: `Time Entry Templates` report → export
  - Note: Search → `View Business Process` → "Enter Time" → screenshot/export
- [ ] **Document what already exists** — IMPL1 may have partial configuration from a previous phase

### Hour 4-8: Foundation Review

- [ ] Search → `Maintain Time Entry Codes` → Are needed codes defined?
- [ ] Search → `Maintain Time Code Groups` → review or create groups
- [ ] Search → `Create Time Entry Template` → review existing or determine type needed
- [ ] **Decision:** Duration-based or In/Out? (This shapes everything downstream)

### Hour 8-16: Rules & Population

- [ ] Search → `Maintain Time Calculations` → review existing rules
- [ ] Search → `Maintain Time Tracking Eligibility Rules` → review who's eligible
- [ ] Search → `Create Work Schedule Calendar` → review existing schedules
- [ ] **Map source time types** to Workday codes (even without the file, use the code list as hypothesis)
- [ ] Identify gaps: missing codes, missing rules, missing schedules

### Hour 16-24: Business Process & Security

- [ ] Search → `View Business Process` → "Enter Time" → document current flow
- [ ] Review approval chain: who approves? how many levels?
- [ ] Search → `Create Integration System User` → check if ISU exists
- [ ] Review domain security for time tracking domains
- [ ] Document any **functional questions** that arise (add to [questions.md](questions.md))

### Hour 24-48: Documentation & Communication

- [ ] **Draft the time code mapping** (best guess based on what you've learned)
- [ ] **Draft the BRD** outline with what you know
- [ ] **Send questions** to client (from checklist above)
- [ ] **Send status update** to project team: "Here's what I found, here's what's missing"
- [ ] **Plan next steps** based on answers

---

## 7. Web Service Operations Reference

From the [Workday Time_Tracking Web Service v44.1](https://community.workday.com/sites/default/files/file-hosting/productionapi/Time_Tracking/v44.1/Time_Tracking.html):

| Operation | Description | Best For |
|---|---|---|
| `Import_Time_Clock_Events` | Load large batches of clock in/out events | **Bulk inbound — recommended for this project if using in/out** |
| `Import_Reported_Time_Blocks` | Import time blocks (duration) from 3rd party | **Bulk inbound — recommended if using total hours** |
| `Put_Time_Clock_Events` | Add individual clock events | Real-time or small batches |
| `Put_Reported_Time_Blocks_for_Worker` | Create/edit time blocks per worker | Small scale — **not recommended for integrations** |
| `Assign_Work_Schedule` | Import work schedule assignments | Bulk schedule loads |
| `Import_Ad_Hoc_Schedules` | Load schedule blocks in bulk | One-time or infrequent |
| `Get_Calculated_Time_Blocks` | Retrieve calculated time | Outbound reconciliation |
| `Get_Time_Requests` | Retrieve time requests | Outbound if needed |
| `Put_Time_Requests` | Create/update time requests | If source manages time-off requests |

---

## 8. Additional Resources

### Official Documentation (Workday Community — login required)

- [Workday Admin Guide: Setting Up Time Tracking](https://doc.workday.com/admin-guide/en-us/time-tracking/setting-up-time-tracking/tmk1466530755620.html)
- [Workday Admin Guide: Time Tracking Concepts](https://doc.workday.com/admin-guide/en-us/time-tracking/time-tracking-concepts/tmk1466530805752.html)
- [Time_Tracking Web Service API v44.1](https://community.workday.com/sites/default/files/file-hosting/productionapi/Time_Tracking/v44.1/Time_Tracking.html)
- [WSDL Download](https://community.workday.com/sites/default/files/file-hosting/productionapi/Time_Tracking/v44.1/Time_Tracking.wsdl)
- [XSD Schema Download](https://community.workday.com/sites/default/files/file-hosting/productionapi/Time_Tracking/v44.1/Time_Tracking.xsd)

### Workday Community Search Tips

If you can't find a specific task mentioned here:
1. Go to [community.workday.com](https://community.workday.com)
2. Search for the task name in quotes
3. Filter by "Documentation" or "Knowledge Articles"
4. Check the **Resource Center** for admin guides per module

### Mexico Labor Law References

- [Ley Federal del Trabajo (LFT)](https://www.diputados.gob.mx/LeyesBiblio/pdf/LFT.pdf) — Official text
- Art. 58-68: Work hours, overtime
- Art. 69-75: Rest days, holidays, premiums
- Art. 76-81: Vacation

---

> **Disclaimer:** Task names and navigation may vary slightly between Workday versions and tenant configurations. If you cannot find a task by exact name, try searching for keywords (e.g., "time entry" or "time code") — Workday's search is flexible and will show related tasks. When in doubt, ask your Workday admin to verify your security access to the functional area.
