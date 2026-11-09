export interface Summary {
  total_patients: number;
  table_counts: Record<string, number>;
  audit_log: { total: number; critical: number; quarantined: number; auto_corrected: number };
  data_passports: { total: number; pending_review: number };
}

export interface QualityScore {
  source_file: string;
  score: number;
  rows_imported: number;
  rows_quarantined: number;
  values_auto_corrected: number;
  errors_by_category: Record<string, number>;
}

export interface PipelineProgress {
  status: string;
  current_step: string;
  step_number: number;
  total_steps: number;
  progress_pct: number;
  step_detail?: string | null;
  errors?: string[];
}

export interface WardScore {
  ward_name: string;
  score: number;
  nb_patients: number;
  nb_errors: number;
  rank: number;
  axes: Record<string, number>;
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

export interface Passport {
  passport_id: number;
  case_id: string | null;
  table_name: string;
  field_name: string;
  raw_value: string | null;
  cleaned_value: string | null;
  detected_by: string;
  problem_type: string;
  problem_detail: string;
  action_taken: string;
  confidence: number | null;
  validated_by: string | null;
  status: string;
  source_file: string;
  row_number: number | null;
  created_at: string;
  updated_at: string | null;
}

export interface Patient {
  case_id: string;
  patient_id: string | null;
  age: number | null;
  gender: string | null;
  ward: string | null;
  admission_date?: string | null;
  discharge_date?: string | null;
  primary_icd10: string | null;
  primary_icd10_desc?: string | null;
}

export interface LabValue {
  parameter_name: string;
  value: string | null;
  flag: string | null;
  ref_low: string | null;
  ref_high: string | null;
  original_value: string | null;
  was_corrected: boolean;
}

export interface TimelineEvent {
  event_type: "LAB" | "MOTION_HOURLY" | "MEDICATION" | "NURSING" | string;
  timestamp: string;
  data: Record<string, unknown>;
  source_file: string | null;
  alert_message: string | null;
}

export interface NursingNote {
  case_id: string;
  shift: string | null;
  report_date: string | null;
  pain_level: number | null;
  mobility_status: string | null;
  wound_grade: string | null;
  deterioration_flag: boolean;
  deterioration_signs: string[];
  note_preview: string;
}

export interface Convergence {
  case_id: string;
  total_score: number;
  risk_level: string;
  breakdown: Record<string, number>;
  top_contributors: string[];
}

export interface MotionSummary {
  case_id: string;
  total_records: number;
  fall_events: number;
  bed_exits: number;
  avg_movement_index: number | null;
  max_impact_g: number | null;
}

export interface Alert {
  case_id: string;
  rule_name: string;
  severity: string;
  message: string;
  sources_involved: string[];
  triggered_values: Record<string, unknown>;
  timestamp_generated: string;
  sbar: Record<string, string> | null;
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

export interface RepairProposal {
  passport_id: number;
  case_id: string | null;
  field_name: string;
  raw_value: string | null;
  proposed_value: string | null;
  strategy: string;
  confidence: number;
  reasoning: string;
  auto_apply: boolean;
}
