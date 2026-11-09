export type AnomalyLevel = "none" | "low" | "medium" | "high" | "critical";
export type DataQuality = "complete" | "missing" | "inconsistent" | "outdated";

export interface Patient {
  id: string;
  name: string;
  age: number;
  gender: "M" | "F" | "Other";
  ward: string;
  admissionDate: string;
  diagnosis: string;
  // Vitals
  heartRate: number;        // bpm
  bloodPressureSys: number; // mmHg systolic
  bloodPressureDia: number; // mmHg diastolic
  spo2: number;             // % oxygen saturation
  temperature: number;      // Celsius
  respiratoryRate: number;  // breaths/min
  // Status
  anomalyLevel: AnomalyLevel;
  anomalyFlags: string[];
  dataQuality: DataQuality;
  missingFields: string[];
  lastUpdated: string;
  status: "stable" | "monitoring" | "critical" | "discharged";
}

export interface MetricPoint {
  timestamp: string;
  value: number;
}

export interface ChartSeries {
  name: string;
  data: MetricPoint[];
  color?: string;
}

export interface KpiMetric {
  label: string;
  value: number | string;
  delta?: number; // percentage change (omit to hide the badge)
  hint?: string;
  unit?: string;
  trend: "up" | "down" | "flat";
  status: "good" | "warning" | "critical";
  icon?: string;
}

export interface ActivityEvent {
  id: string;
  timestamp: string;
  type: "alert" | "admission" | "discharge" | "update" | "anomaly" | "review";
  title: string;
  description: string;
  patient?: string;
  severity?: AnomalyLevel;
}

export interface AnomalyAlert {
  id: string;
  patientId: string;
  patientName: string;
  metric: string;
  value: number;
  threshold: number;
  level: AnomalyLevel;
  detectedAt: string;
  resolved: boolean;
}
