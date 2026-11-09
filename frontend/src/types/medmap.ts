export interface DashboardOverview {
  kpis: {
    cases: number;
    clinical_alerts: number;
    patients_with_alerts: number;
    data_quality_pct: number;
    auto_corrected: number;
    pending_review: number;
    sources: number;
    rows_imported: number;
    rows_quarantined: number;
  };
  movement_by_hour: { time: string; avg_movement: number; falls: number; bed_exits: number }[];
  admissions_by_day: { date: string; admissions: number; discharges: number }[];
  issues_by_group: { group: string; critical: number; high: number; medium: number; low: number }[];
  wards: { ward: string; patients: number }[];
}

export interface ClinicalAlert {
  case_id: string;
  case_label: string;
  rule_name: string;
  rule_label: string;
  severity: string;
  message: string;
  sources_involved: string[];
  triggered_values: Record<string, unknown>;
  timestamp_generated: string;
  is_treated: boolean;
  age: number | null;
  gender: string | null;
}

export type Level = "critical" | "high" | "medium" | "low" | "none";

export interface MonitorPatient {
  id: string;
  case_id: string;
  patient_id: string | null;
  age: number | null;
  gender: string | null;
  ward: string | null;
  admission_date: string | null;
  discharge_date: string | null;
  diagnosis_code: string | null;
  diagnosis: string | null;
  labs: Record<string, { value: string | null; flag: string | null }>;
  falls: number;
  motion_records: number;
  deterioration_notes: number;
  nursing_notes: number;
  medication_events: number;
  sources: number;
  anomaly_level: Level;
  anomaly_flags: string[];
  issues: number;
  data_quality: "complete" | "missing" | "inconsistent";
  status: "stable" | "monitoring" | "critical" | "discharged";
}

export interface MonitorResponse {
  total: number;
  matched: number;
  counts: Record<string, number>;
  patients: MonitorPatient[];
}

export interface QualityScore {
  source_file: string;
  score: number;
  rows_imported: number;
  rows_quarantined: number;
  values_auto_corrected: number;
  errors_by_category: Record<string, number>;
}

export interface ErrorCategory {
  error_type: string;
  total: number;
  by_severity: Record<string, number>;
}

export interface AuditEntry {
  coId: number;
  source_file: string;
  case_id: string | null;
  table_name: string;
  column_name: string;
  original_value: string | null;
  cleaned_value: string | null;
  error_type: string;
  severity: string;
  action_taken: string;
  corrected_by: string | null;
  correction_timestamp: string | null;
  row_number: number | null;
}

export interface PatientDetail {
  case_id: string;
  patient_id: string | null;
  age: number | null;
  gender: string | null;
  ward: string | null;
  admission_date: string | null;
  discharge_date: string | null;
  primary_icd10: string | null;
  primary_icd10_desc: string | null;
}

export interface LabValue {
  parameter_name: string;
  value: string | null;
  flag: string | null;
  ref_low: string | null;
  ref_high: string | null;
}

export interface TimelineEvent {
  event_type: string;
  timestamp: string;
  data: Record<string, unknown>;
  alert_message: string | null;
}

export interface NursingNote {
  shift: string | null;
  report_date: string | null;
  pain_level: number | null;
  mobility_status: string | null;
  deterioration_flag: boolean;
  deterioration_signs: string[];
  note_preview: string;
}

export interface Convergence {
  total_score: number;
  risk_level: string;
  breakdown: Record<string, number>;
  top_contributors: string[];
}

export interface Passport {
  passport_id: number;
  field_name: string;
  raw_value: string | null;
  cleaned_value: string | null;
  problem_detail: string;
  status: string;
  source_file: string;
  row_number: number | null;
}

export interface CorrectionResult {
  success: boolean;
  audit_log_id: number;
  previous_value: string | null;
  new_value: string | null;
  action: string;
  error: string | null;
}
