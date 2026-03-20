# MEDMAP Frontend Implementation Plan

## Overview

Build a 9-page Next.js dashboard consuming the backend API (45 endpoints on `localhost:8000`). The backend is **100% complete** — every endpoint returns real data from SQLite.

**Stack**: Next.js 14+ (App Router) + shadcn/ui + Tailwind + Recharts + TanStack Table
**Template**: Copy from `frontend_temp/next-shadcn-dashboard-starter-main/` → `frontend/`

---

## Phase 0 — Setup

1. Copy starter template to `frontend/`
2. Remove Clerk/Sentry dependencies and imports (auth not needed)
3. Remove unneeded pages: Product, Kanban, Billing, Workspaces, Teams, Exclusive
4. Create `.env.local`:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000
   NEXT_PUBLIC_USE_MOCKS=false
   ```
5. Create `src/types/contracts.ts` (TypeScript mirror — see below)
6. Create `src/lib/api.ts` (fetch wrapper — see below)
7. Create `src/lib/constants.ts` (colors, icons — see below)
8. Create `src/config/nav-config.ts` (9-item sidebar)
9. Verify: `npm run dev` shows the dashboard shell with sidebar

---

## Phase 1 — Overview Page (`/dashboard/overview`)

**API calls**: `GET /api/overview/summary`, `GET /api/overview/quality-scores`, `GET /api/overview/ward-scores`, `POST /api/pipeline/start`, `GET /api/pipeline/progress`

**Components**:
- **Stats cards**: Total patients, total rows, critical issues, quarantined (from `/summary`)
- **Pipeline control**: Start button + progress bar (poll `/progress` every 1s while running)
- **Source quality grid**: Cards per file with score bar + error count (from `/quality-scores`)
- **Ward scoreboard**: Ranked list with score badges + radar chart per ward (from `/ward-scores`)
- **Report generator**: Button → `POST /generate-report` → render markdown

---

## Phase 2 — Patient View (`/dashboard/patient`)

**API calls**: `GET /api/patients?limit=50`, `GET /api/patients/search?q=...`, `GET /api/patients/{id}`, `GET /api/patients/{id}/labs`, `GET /api/patients/{id}/medications`, `GET /api/patients/{id}/nursing`, `GET /api/patients/{id}/convergence`, `GET /api/patients/{id}/motion-summary`, `GET /api/patients/{id}/sbar`, `GET /api/patients/{id}/passports`

**Layout**: Patient selector (search + dropdown) → detail panel with 5 tabs

**Tabs**:
1. **Labs**: Table with colored flags (H=orange, L=blue, HH=red, LL=dark blue), sparklines optional
2. **Motion/Falls**: Fall count, bed exits, avg movement, max impact (from `/motion-summary`)
3. **Medications**: Table of active meds with route, dose, frequency
4. **Nursing NLP**: Notes with extracted pain level, mobility status, wound grade, deterioration badges
5. **Data Lineage**: Data passports for this patient (from `/passports`)

**Top bar**: Convergence score badge (0-100, color-coded), demographics, SBAR button

---

## Phase 3 — SBAR Alerts (`/dashboard/alerts`)

**API calls**: `GET /api/alerts?severity=CRITICAL,HIGH`, `GET /api/alerts/summary`, `PATCH /api/alerts/{case_id}/{rule_name}`, `GET /api/alerts/export`, `GET /api/patients/{id}/explain-alert/{rule}`

**Components**:
- **Summary bar**: Total, critical count, high count, treated count (from `/summary`)
- **Filter bar**: Severity checkboxes, rule dropdown, treated toggle
- **Alert cards**: Each shows rule_name, severity badge, message, SBAR (S/B/A/R formatted), sources
- **Actions**: "View Patient" link, "Mark Treated" button (PATCH), "Explain" button (calls `/explain-alert`)
- **Export**: Download button → `/export` → CSV

---

## Phase 4 — Agent Orchestra (`/dashboard/agents`)

**API calls**: `GET /api/agents/stats`, `GET /api/agents/mappings?badge=AUTO,CHECK,REVIEW`, `GET /api/agents/decisions`, `GET /api/agents/nlp-stats`

**Components**:
- **4 metric cards**: Total columns, auto-mapped, conflicts, escalated (from `/stats`)
- **6 agent progress bars**: Schema Detective, Validation Agent, Clinical Reasoner, Nursing Analyst, Data Repair, Supervisor (from `/stats` → `agent_progress`)
- **Confidence Glass**: Filterable table of column mappings. Columns: source_file, source_column, target_column, confidence, badge (🟢🟡🔴). Filter by badge/source/status
- **NLP stats panel**: Pain/mobility/wound/deterioration extraction rates (from `/nlp-stats`)

---

## Phase 5 — Data Quality (`/dashboard/quality`)

**API calls**: `GET /api/quality/audit-log`, `GET /api/quality/error-categories`, `GET /api/quality/completeness`, `GET /api/quality/before-after`, `GET /api/quality/before-after/stats`

**4 tabs**:
1. **Errors**: Filterable table (source, column, error_type, severity, original → cleaned)
2. **Categories**: Bar chart of error types by count (Recharts)
3. **Completeness**: Heatmap of source × column completeness (from `/completeness`)
4. **Before/After**: Red (before) → green (after) view. Click row → Data Passport modal

---

## Phase 6 — Time Travel (`/dashboard/time-travel`)

**API calls**: `GET /api/patients?limit=50`, `GET /api/patients/{id}/timeline`

**Components**:
- **Patient selector**: Dropdown or search
- **Vertical timeline**: Events sorted by timestamp, color-coded by type:
  - LAB = blue, MEDICATION = green, MOTION = orange, NURSING = purple, ALERT = red
- **Event cards**: Timestamp, type icon, data summary, expandable detail
- **Alert injection**: Alert events from anomaly detection appear inline with red border

---

## Phase 7 — Corrections (`/dashboard/corrections`)

**API calls**: `GET /api/corrections/pending`, `POST /api/corrections/apply`, `POST /api/corrections/rollback`, `GET /api/corrections/history`, `GET /api/corrections/repair-proposals`

**2 tabs**:
1. **Pending**: Queue of items needing review. Each shows field, raw value, proposed repair (from `/repair-proposals`). Buttons: Accept (apply), Edit (modal), Quarantine
2. **History**: Table of past corrections with rollback button (AlertDialog confirmation)

---

## Phase 8 — Ask Your Data (`/dashboard/ask`)

**API calls**: `POST /api/ask`, `GET /api/ask/history`

**Components**:
- **Chat interface**: Input box + send button
- **Suggestion chips**: Clickable preset questions (see constants.ts)
- **Result display**: SQL (collapsible code block), result table, narrative text
- **History sidebar**: Past queries, click to re-display

---

## Phase 9 — ROI Calculator (`/dashboard/roi`)

**100% frontend — no API calls.**

**5 sliders**: nb_institutions (1-50), cases_per_year (100-10000), complication_rate (1-30%), avg_cost (1000-50000), prevention_rate (5-50%)

**4 result cards** (computed with `useMemo`):
- Preventable complications
- Cost savings per year
- Cost savings per institution
- 5-year projected savings

---

## Starter Files

### `src/types/contracts.ts`

```typescript
// Enums
export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
export type RiskLevel = 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
export type Shift = 'Early' | 'Late' | 'Night';
export type MobilityStatus = 'INDEPENDENT' | 'ASSISTED' | 'WHEELCHAIR' | 'BED_BOUND';
export type Badge = 'AUTO' | 'CHECK' | 'REVIEW';

// API response types
export interface OverviewSummary {
  total_patients: number;
  table_counts: Record<string, number>;
  audit_log: { total: number; critical: number; quarantined: number; auto_corrected: number };
  data_passports: { total: number; pending_review: number };
}

export interface QualityScore {
  source_file: string;
  overall_score: number;
  total_errors: number;
  rows_quarantined: number;
  errors_by_category: Record<string, number>;
}

export interface WardScore {
  ward_name: string;
  score: number;
  nb_patients: number;
  nb_errors: number;
  rank: number;
  axes: Record<string, number>;
}

export interface PatientSummary {
  case_id: string;
  patient_id: string | null;
  age: string | null;
  gender: string | null;
  ward: string | null;
  primary_icd10: string | null;
}

export interface LabResult {
  coSpecimen_datetime: string;
  [key: string]: string | number | null;  // lab values + flags
}

export interface TimelineEvent {
  event_type: string;
  timestamp: string;
  data: Record<string, unknown>;
  source_file: string | null;
  alert_message: string | null;
}

export interface NursingNLPResult {
  case_id: string;
  shift: Shift;
  report_date: string;
  pain_level: number | null;
  mobility_status: MobilityStatus | null;
  wound_grade: string | null;
  deterioration_flag: boolean;
  deterioration_signs: string[];
  note_preview: string;
}

export interface ClinicalAlert {
  case_id: string;
  rule_name: string;
  severity: Severity;
  message: string;
  sources_involved: string[];
  triggered_values: Record<string, unknown>;
  timestamp_generated: string;
  sbar: { S: string; B: string; A: string; R: string } | null;
  is_treated: boolean;
  treated_by: string | null;
  treated_at: string | null;
}

export interface AlertSummary {
  total_alerts: number;
  by_rule: Record<string, number>;
  by_severity: Record<string, number>;
  treated_count: number;
  untreated_count: number;
}

export interface ColumnMapping {
  source_file: string;
  source_column: string;
  target_column: string;
  confidence: number;
  badge: Badge;
  status: string;
  supervisor_decision: string | null;
}

export interface AgentStats {
  total_columns: number;
  auto_mapped: number;
  conflicts: number;
  escalated: number;
  agent_progress: Record<string, { processed: number; total: number }>;
}

export interface NLPStats {
  total_notes: number;
  pain_extracted: number;
  mobility_breakdown: Record<string, number>;
  wound_extracted: number;
  deterioration_flagged: number;
  top_signs: Record<string, number>;
  extraction_rate_pct: number;
}

export interface ConvergenceScore {
  case_id: string;
  total_score: number;
  risk_level: RiskLevel;
  breakdown: Record<string, number>;
  top_contributors: string[];
  computed_at: string;
}

export interface AskDataResult {
  question: string;
  sql_generated: string;
  results_as_dicts: Record<string, unknown>[] | null;
  narrative_answer: string | null;
  error: string | null;
  row_count: number;
  execution_time_ms: number;
  used_llm: boolean;
}

export interface CorrectionResult {
  success: boolean;
  audit_log_id: number;
  previous_value: string | null;
  new_value: string | null;
  action: string;
  error: string | null;
}

export interface RepairProposal {
  passport_id: number;
  case_id: string;
  field_name: string;
  raw_value: string;
  proposed_value: string | null;
  strategy: string;
  confidence: number;
  reasoning: string;
  auto_apply: boolean;
}

export interface PipelineProgress {
  status: 'IDLE' | 'RUNNING' | 'COMPLETED' | 'ERROR';
  current_step: string;
  step_number: number;
  total_steps: number;
  progress_pct: number;
  step_detail: string | null;
  errors: string[];
}
```

### `src/lib/api.ts`

```typescript
const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export async function api<T>(
  method: 'GET' | 'POST' | 'PATCH',
  path: string,
  body?: unknown
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  return res.json();
}

// Convenience helpers
export const get = <T>(path: string) => api<T>('GET', path);
export const post = <T>(path: string, body?: unknown) => api<T>('POST', path, body);
export const patch = <T>(path: string, body?: unknown) => api<T>('PATCH', path, body);
```

### `src/lib/constants.ts`

```typescript
export const SEVERITY_STYLES = {
  CRITICAL: { badge: 'destructive' as const, bg: 'bg-red-500/10', text: 'text-red-500', dot: '🔴' },
  HIGH:     { badge: 'outline' as const, bg: 'bg-orange-500/10', text: 'text-orange-500', dot: '🟠' },
  MEDIUM:   { badge: 'outline' as const, bg: 'bg-yellow-500/10', text: 'text-yellow-500', dot: '🟡' },
  LOW:      { badge: 'secondary' as const, bg: 'bg-green-500/10', text: 'text-green-500', dot: '🟢' },
};

export const TIMELINE_STYLES = {
  LAB:           { icon: '📊', color: 'border-l-blue-500',   label: 'Lab' },
  MEDICATION:    { icon: '💊', color: 'border-l-green-500',  label: 'Medication' },
  MOTION_HOURLY: { icon: '📡', color: 'border-l-orange-500', label: 'Motion' },
  NURSING:       { icon: '📝', color: 'border-l-purple-500', label: 'Nursing' },
  ASSESSMENT:    { icon: '📋', color: 'border-l-gray-500',   label: 'Assessment' },
  ALERT:         { icon: '⚠️', color: 'border-l-red-500',    label: 'Alert' },
};

export const BADGE_STYLES = {
  AUTO:   { color: 'bg-green-500/10 text-green-600', icon: '🟢' },
  CHECK:  { color: 'bg-yellow-500/10 text-yellow-600', icon: '🟡' },
  REVIEW: { color: 'bg-red-500/10 text-red-600', icon: '🔴' },
};

export const SUGGESTED_QUESTIONS = [
  "How many patients are in each ward?",
  "Which ward has the most data quality errors?",
  "Show me patients with fall events",
  "Which patients have critical lab values?",
  "What medications are most prescribed?",
];
```

---

## API Endpoint Reference (45 endpoints)

### Pipeline
| Method | Path | Returns |
|--------|------|---------|
| POST | `/api/pipeline/start` | `{ status, message }` |
| GET | `/api/pipeline/progress` | `PipelineProgress` |
| GET | `/api/pipeline/stats` | `PipelineStats` |
| GET | `/api/pipeline/streaming-progress` | streaming progress |

### Overview
| Method | Path | Returns |
|--------|------|---------|
| GET | `/api/overview/summary` | `OverviewSummary` |
| GET | `/api/overview/quality-scores` | `QualityScore[]` |
| GET | `/api/overview/ward-scores` | `WardScore[]` |
| POST | `/api/overview/generate-report` | `{ report: string }` (markdown) |
| POST | `/api/overview/executive-summary` | `{ summary: string }` |

### Patients
| Method | Path | Returns |
|--------|------|---------|
| GET | `/api/patients?ward=X&limit=50` | `PatientSummary[]` |
| GET | `/api/patients/search?q=term` | `PatientSummary[]` |
| GET | `/api/patients/{id}` | `PatientSummary` |
| GET | `/api/patients/{id}/labs` | `LabResult[]` |
| GET | `/api/patients/{id}/timeline` | `TimelineEvent[]` |
| GET | `/api/patients/{id}/medications` | medication dicts |
| GET | `/api/patients/{id}/nursing` | `NursingNLPResult[]` |
| GET | `/api/patients/{id}/nursing/summary` | NLP summary |
| GET | `/api/patients/{id}/convergence` | `ConvergenceScore` |
| GET | `/api/patients/{id}/motion-summary` | motion stats |
| GET | `/api/patients/{id}/passports` | passport dicts |
| GET | `/api/patients/{id}/sbar` | `{ case_id, sbar: {S,B,A,R} }` |
| GET | `/api/patients/{id}/explain-alert/{rule}` | `{ explanation }` |

### Alerts
| Method | Path | Returns |
|--------|------|---------|
| GET | `/api/alerts?severity=X&treated=bool&rule=X` | `ClinicalAlert[]` |
| GET | `/api/alerts/summary` | `AlertSummary` |
| PATCH | `/api/alerts/{case_id}/{rule_name}` | updated alert |
| GET | `/api/alerts/export` | flat alert dicts |

### Agents
| Method | Path | Returns |
|--------|------|---------|
| GET | `/api/agents/stats` | `AgentStats` |
| GET | `/api/agents/mappings?badge=X` | `ColumnMapping[]` |
| GET | `/api/agents/decisions` | `ColumnMapping[]` |
| GET | `/api/agents/nlp-stats` | `NLPStats` |

### Quality
| Method | Path | Returns |
|--------|------|---------|
| GET | `/api/quality/audit-log?severity=X` | audit entries |
| GET | `/api/quality/passports?status=X` | passport dicts |
| GET | `/api/quality/completeness` | completeness matrix |
| GET | `/api/quality/before-after` | before/after pairs |
| GET | `/api/quality/error-categories` | category counts |
| GET | `/api/quality/before-after/stats` | stats summary |
| GET | `/api/quality/export/{table}` | CSV data |

### Ask Your Data
| Method | Path | Returns |
|--------|------|---------|
| POST | `/api/ask` body: `{question}` | `AskDataResult` |
| GET | `/api/ask/history` | `AskDataResult[]` |

### Corrections
| Method | Path | Returns |
|--------|------|---------|
| GET | `/api/corrections/pending` | passport dicts |
| POST | `/api/corrections/apply` body: `{audit_log_id, new_value}` | `CorrectionResult` |
| POST | `/api/corrections/rollback` body: `{audit_log_id}` | `CorrectionResult` |
| GET | `/api/corrections/history` | `CorrectionResult[]` |
| GET | `/api/corrections/repair-proposals` | `RepairProposal[]` |

---

## Running Together

```bash
# Terminal 1 — Backend
cd medmap
uvicorn api.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm run dev
# → http://localhost:3000
```

CORS is already configured in the backend for `localhost:3000`, `3001`, `3002`.
