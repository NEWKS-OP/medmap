"""
═══════════════════════════════════════════════════════════
MEDMAP — SHARED INTERFACE CONTRACTS
═══════════════════════════════════════════════════════════
CE FICHIER EST LE PONT ENTRE LE BACKEND ET LE FRONTEND.
NE PAS MODIFIER SANS ACCORD DES DEUX DÉVELOPPEURS.

Le backend PRODUIT ces structures.
Le frontend CONSOMME ces structures.

Toute modification de ce fichier doit être communiquée
immédiatement à l'autre développeur.
═══════════════════════════════════════════════════════════
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


# ═══════════════════════════════════════════════════════
# ENUMS PARTAGÉS
# ═══════════════════════════════════════════════════════

class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RiskLevel(str, Enum):
    LOW = "LOW"          # 0-25
    MODERATE = "MODERATE" # 26-50
    HIGH = "HIGH"        # 51-75
    CRITICAL = "CRITICAL" # 76-100


class ActionTaken(str, Enum):
    QUARANTINE = "QUARANTINE"
    AUTO_CORRECT = "AUTO_CORRECT"
    FLAGGED = "FLAGGED"
    ACCEPTED = "ACCEPTED"
    MANUAL_CORRECT = "MANUAL_CORRECT"
    ROLLBACK = "ROLLBACK"


class ProblemType(str, Enum):
    INVALID = "INVALID"
    MISSING = "MISSING"
    OUTLIER = "OUTLIER"
    CORRECTED = "CORRECTED"
    STRUCTURAL = "STRUCTURAL"
    DUPLICATE = "DUPLICATE"


class PassportStatus(str, Enum):
    QUARANTINE = "QUARANTINE"
    CLEAN = "CLEAN"
    PENDING_REVIEW = "PENDING_REVIEW"


class AgentConfidenceBadge(str, Enum):
    AUTO = "AUTO"       # >= 0.90 vert
    CHECK = "CHECK"     # 0.70-0.89 jaune
    REVIEW = "REVIEW"   # < 0.70 rouge


class PipelineStatus(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class MobilityStatus(str, Enum):
    INDEPENDENT = "INDEPENDENT"
    ASSISTED = "ASSISTED"
    WHEELCHAIR = "WHEELCHAIR"
    BED_BOUND = "BED_BOUND"


class EventType(str, Enum):
    ORDER = "ORDER"
    CHANGE = "CHANGE"
    ADMIN = "ADMIN"


class Shift(str, Enum):
    EARLY = "Early"
    LATE = "Late"
    NIGHT = "Night"


class TimelineEventType(str, Enum):
    LAB = "LAB"
    MOTION_HOURLY = "MOTION_HOURLY"
    MOTION_1HZ = "MOTION_1HZ"
    MEDICATION = "MEDICATION"
    NURSING = "NURSING"
    ASSESSMENT = "ASSESSMENT"
    ALERT = "ALERT"


# ═══════════════════════════════════════════════════════
# CONTRAT 1 — RÉSULTAT D'INGESTION
# Produit par : pipeline/ingestion.py
# Consommé par : dashboard/overview.py
# ═══════════════════════════════════════════════════════

@dataclass
class IngestionResult:
    source_file: str
    rows_total: int
    rows_loaded: int
    encoding_detected: str
    delimiter_detected: str
    warnings: list[str] = field(default_factory=list)
    # Le DataFrame n'est PAS dans le contrat — il est stocké
    # dans st.session_state.dataframes[source_file]


# ═══════════════════════════════════════════════════════
# CONTRAT 2 — SCORE QUALITÉ PAR SOURCE
# Produit par : pipeline/validator.py
# Consommé par : dashboard/overview.py, dashboard/quality.py
# ═══════════════════════════════════════════════════════

@dataclass
class SourceQualityScore:
    source_file: str
    score: int                  # 0-100
    rows_imported: int
    rows_quarantined: int
    values_auto_corrected: int
    errors_by_category: dict[str, int]
    # errors_by_category exemple:
    # {
    #   "MISSING_VALUES": 23,
    #   "INVALID_DATE": 7,
    #   "CLINICAL_OUTLIER": 12,
    #   "GENDER_INVALID": 3,
    #   "STRUCTURAL_ERROR": 1,
    #   "DUPLICATE": 5,
    #   "ID_INVALID": 2,
    #   "LAB_FLAG_INVALID": 1
    # }


# ═══════════════════════════════════════════════════════
# CONTRAT 3 — ENTRÉE DU LOG D'AUDIT
# Produit par : pipeline/validator.py, pipeline/cleaner.py
# Consommé par : dashboard/quality.py, dashboard/correction.py
# Aussi stocké dans : table tbAuditLog (SQLite)
# ═══════════════════════════════════════════════════════

@dataclass
class AuditLogEntry:
    source_file: str
    case_id: str
    table_name: str
    column_name: str
    original_value: str
    cleaned_value: Optional[str]
    error_type: str              # ex: "CLINICAL_OUTLIER", "INVALID_DATE"
    severity: Severity
    action_taken: ActionTaken
    corrected_by: Optional[str]  # None = auto, sinon user_id
    correction_timestamp: Optional[datetime] = None
    row_number: Optional[int] = None


# ═══════════════════════════════════════════════════════
# CONTRAT 4 — RÉSULTAT D'AGENT
# Produit par : tous les agents (pipeline/agents/)
# Consommé par : dashboard/agent_activity.py
# ═══════════════════════════════════════════════════════

@dataclass
class AgentResult:
    agent_name: str
    decision: str
    confidence: float            # 0.0 à 1.0
    reasoning: str
    alternative: Optional[str] = None
    needs_human_review: bool = False
    metadata: dict = field(default_factory=dict)

    @property
    def badge(self) -> AgentConfidenceBadge:
        if self.confidence >= 0.90:
            return AgentConfidenceBadge.AUTO
        elif self.confidence >= 0.70:
            return AgentConfidenceBadge.CHECK
        else:
            return AgentConfidenceBadge.REVIEW


# ═══════════════════════════════════════════════════════
# CONTRAT 5 — MAPPING DE COLONNE (Schema Detective)
# Produit par : pipeline/agents/schema_detective.py
# Validé par : pipeline/agents/validation_agent.py
# Arbitré par : pipeline/agents/supervisor.py
# Consommé par : dashboard/agent_activity.py
# ═══════════════════════════════════════════════════════

@dataclass
class ColumnMapping:
    source_file: str
    source_column: str
    target_column: str
    confidence: float
    badge: AgentConfidenceBadge
    status: str                   # "CONSENSUS" | "CONFLICT" | "UNCERTAIN"
    detective_result: Optional[AgentResult] = None
    validation_result: Optional[AgentResult] = None
    supervisor_decision: Optional[str] = None
    alternative_target: Optional[str] = None


# ═══════════════════════════════════════════════════════
# CONTRAT 6 — STATS DES AGENTS (Supervisor)
# Produit par : pipeline/agents/supervisor.py
# Consommé par : dashboard/agent_activity.py
# ═══════════════════════════════════════════════════════

@dataclass
class AgentStats:
    total_columns: int = 0
    auto_mapped: int = 0
    conflicts: int = 0
    escalated: int = 0
    # Stats par agent individuel
    agent_progress: dict[str, dict] = field(default_factory=dict)
    # agent_progress exemple:
    # {
    #   "Schema Detective": {"processed": 247, "total": 247},
    #   "Validation Agent": {"processed": 247, "total": 247},
    #   "Clinical Reasoner": {"processed": 892, "total": 1000},
    #   "Nursing Analyst": {"processed": 109, "total": 182},
    #   "Data Repair": {"processed": 34, "total": 34},
    #   "Supervisor": {"processed": 12, "total": 12},
    # }


# ═══════════════════════════════════════════════════════
# CONTRAT 7 — ALERTE CLINIQUE
# Produit par : pipeline/anomaly.py
# Enrichi par : pipeline/agents/clinical_reasoner.py (SBAR)
# Consommé par : dashboard/anomaly_alerts.py
# ═══════════════════════════════════════════════════════

@dataclass
class ClinicalAlert:
    case_id: str
    rule_name: str               # ex: "AKI_PROBABLE", "SEPSIS_POSSIBLE"
    severity: Severity
    message: str
    sources_involved: list[str]  # ex: ["labs", "medication"]
    triggered_values: dict       # ex: {"creatinine": 4.2, "egfr": 15}
    timestamp_generated: datetime = field(default_factory=datetime.now)
    sbar: Optional[dict] = None  # {S: str, B: str, A: str, R: str}
    is_treated: bool = False
    treated_by: Optional[str] = None
    treated_at: Optional[datetime] = None


# ═══════════════════════════════════════════════════════
# CONTRAT 8 — RÉSULTAT NLP (Notes infirmières)
# Produit par : pipeline/nlp.py
# Consommé par : dashboard/patient_view.py,
#                dashboard/time_travel.py
# ═══════════════════════════════════════════════════════

@dataclass
class NursingNLPResult:
    case_id: str
    shift: Shift
    report_date: str             # ISO format
    pain_level: Optional[int]    # 0-10
    mobility_status: Optional[MobilityStatus]
    wound_grade: Optional[str]   # "1"-"4" ou "HEALING"
    deterioration_flag: bool = False
    deterioration_signs: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════
# CONTRAT 9 — CONVERGENCE SCORE (Patient Risk)
# Produit par : pipeline/agents/clinical_reasoner.py
# Consommé par : dashboard/patient_view.py,
#                dashboard/overview.py
# ═══════════════════════════════════════════════════════

@dataclass
class ConvergenceScore:
    case_id: str
    total_score: int             # 0-100
    risk_level: RiskLevel
    breakdown: dict              # {"labs": int, "motion": int, ...}
    # breakdown = {
    #   "labs": 0-35,
    #   "motion": 0-25,
    #   "medication": 0-20,
    #   "nursing": 0-15,
    #   "assessment": 0-5
    # }
    top_contributors: list[str]  # 3 raisons principales
    computed_at: datetime = field(default_factory=datetime.now)


# ═══════════════════════════════════════════════════════
# CONTRAT 10 — RÉSUMÉ PATIENT
# Produit par : assemblé depuis plusieurs sources
# Consommé par : dashboard/patient_view.py
# ═══════════════════════════════════════════════════════

@dataclass
class PatientSummary:
    case_id: str
    patient_id: Optional[str]
    age: Optional[int]
    gender: Optional[str]        # "M" | "F" | None
    ward: Optional[str]
    admission_date: Optional[str]
    discharge_date: Optional[str]
    primary_icd10: Optional[str]
    primary_icd10_desc: Optional[str]
    convergence_score: Optional[ConvergenceScore] = None


# ═══════════════════════════════════════════════════════
# CONTRAT 11 — RÉSULTAT LABO PATIENT
# Produit par : requête tbImportLabsData
# Consommé par : dashboard/patient_view.py
# ═══════════════════════════════════════════════════════

@dataclass
class LabResult:
    parameter_name: str          # ex: "Sodium", "Creatinine"
    value: Optional[str]         # stocké en string (nvarchar)
    flag: Optional[str]          # "H" | "L" | "HH" | "LL" | None
    ref_low: Optional[str]
    ref_high: Optional[str]
    original_value: Optional[str]  # valeur brute si corrigée
    was_corrected: bool = False


# ═══════════════════════════════════════════════════════
# CONTRAT 12 — ÉVÉNEMENT TIMELINE (Time Travel)
# Produit par : dashboard/time_travel.py (requêtes SQL)
# Consommé par : dashboard/time_travel.py (rendu)
# ═══════════════════════════════════════════════════════

@dataclass
class TimelineEvent:
    event_type: TimelineEventType
    timestamp: str               # ISO format
    data: dict                   # contenu variable selon type
    source_file: Optional[str] = None
    alert_message: Optional[str] = None  # si type=ALERT
    # data exemples par type :
    # LAB: {"egfr": "45", "creatinine": "1.2", "crp": "50"}
    # MEDICATION: {"name": "Metformin", "dose": "500mg",
    #              "event_type": "ORDER", "status": "GIVEN"}
    # MOTION_HOURLY: {"movement_index": 45, "fall_event": 0,
    #                 "bed_exit": 1}
    # NURSING: {"shift": "Early", "pain": 3,
    #           "mobility": "ASSISTED", "note": "..."}
    # ASSESSMENT: {"dekubitus_grade": 2}
    # ALERT: {"rule": "AKI_PROBABLE", "severity": "CRITICAL"}


# ═══════════════════════════════════════════════════════
# CONTRAT 13 — DATA PASSPORT
# Produit par : pipeline/sql_export.py + agents
# Consommé par : dashboard/patient_view.py,
#                dashboard/quality.py
# Aussi stocké dans : table tbDataPassport (SQLite)
# ═══════════════════════════════════════════════════════

@dataclass
class DataPassport:
    passport_id: Optional[int]
    case_id: str
    table_name: str
    field_name: str
    raw_value: str
    cleaned_value: Optional[str]
    detected_by: str             # nom de l'agent
    problem_type: ProblemType
    problem_detail: str          # explication en langage naturel
    action_taken: ActionTaken
    confidence: float
    validated_by: Optional[str]  # None = auto
    fhir_alignment: Optional[str]
    status: PassportStatus
    source_file: Optional[str] = None
    row_number: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ═══════════════════════════════════════════════════════
# CONTRAT 14 — WARD QUALITY SCORE
# Produit par : dashboard/overview.py (compute_ward_scores)
# Consommé par : dashboard/overview.py
# ═══════════════════════════════════════════════════════

@dataclass
class WardScore:
    ward_name: str
    score: int                   # 0-100
    nb_patients: int
    nb_errors: int
    rank: int                    # 1-based
    axes: dict = field(default_factory=dict)
    # axes pour le graphique radar :
    # {
    #   "completude": 0-100,
    #   "dates": 0-100,
    #   "valeurs_cliniques": 0-100,
    #   "ids": 0-100,
    #   "encodage": 0-100
    # }


# ═══════════════════════════════════════════════════════
# CONTRAT 15 — ASK YOUR DATA (Résultat query)
# Produit par : pipeline/agents/data_analyst_agent.py
# Consommé par : dashboard/ask_data.py
# ═══════════════════════════════════════════════════════

@dataclass
class AskDataResult:
    question: str
    sql_generated: str
    results_as_dicts: Optional[list[dict]] = None
    narrative_answer: Optional[str] = None
    error: Optional[str] = None
    row_count: int = 0
    execution_time_ms: float = 0.0


# ═══════════════════════════════════════════════════════
# CONTRAT 16 — CORRECTION MANUELLE
# Envoyé par : dashboard/correction.py (frontend)
# Traité par : pipeline/validator.py ou sql_export.py (backend)
# ═══════════════════════════════════════════════════════

@dataclass
class CorrectionRequest:
    audit_log_id: int            # ou passport_id
    case_id: str
    table_name: str
    column_name: str
    original_value: str
    current_value: Optional[str]
    new_value: Optional[str]     # None si quarantaine
    action: ActionTaken          # ACCEPTED | MANUAL_CORRECT | QUARANTINE
    corrected_by: str = "manual"


@dataclass
class CorrectionResult:
    success: bool
    audit_log_id: int
    previous_value: Optional[str]
    new_value: Optional[str]
    action: ActionTaken
    error: Optional[str] = None


# ═══════════════════════════════════════════════════════
# CONTRAT 17 — PIPELINE PROGRESS (streaming)
# Produit par : pipeline/orchestrator.py (yield)
# Consommé par : dashboard/overview.py
# ═══════════════════════════════════════════════════════

@dataclass
class PipelineProgress:
    status: PipelineStatus
    current_step: str            # ex: "Ingestion synth_labs..."
    step_number: int             # 1-based
    total_steps: int
    progress_pct: float          # 0.0 à 1.0
    step_detail: Optional[str] = None  # détail fin
    errors: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════
# CONTRAT 18 — 1Hz STREAMING PROGRESS
# Produit par : pipeline/ingestion.py (callback)
# Consommé par : dashboard/overview.py
# ═══════════════════════════════════════════════════════

@dataclass
class StreamingProgress:
    processed: int
    total: int
    pct: float
    falls: int
    anomalies: int
    patients: int


# ═══════════════════════════════════════════════════════
# CONTRAT 19 — PIPELINE FINAL STATS
# Produit par : pipeline/orchestrator.py
# Consommé par : dashboard/overview.py, doc_generator
# ═══════════════════════════════════════════════════════

@dataclass
class PipelineStats:
    sources_processed: int
    total_rows: int
    rows_imported: int
    rows_quarantined: int
    errors_by_category: dict[str, int]
    errors_by_dataset: dict[str, int]
    critical_alerts: list[ClinicalAlert] = field(default_factory=list)
    ward_scores: dict[str, WardScore] = field(default_factory=dict)
    processing_time_seconds: float = 0.0
    top_patient_risk: Optional[ConvergenceScore] = None


# ═══════════════════════════════════════════════════════
# CONTRAT 20 — ROI CALCULATOR INPUTS/OUTPUTS
# Produit et consommé par : dashboard/roi_calculator.py
# (Pas de backend, tout côté front — mais contrat
#  documenté pour cohérence)
# ═══════════════════════════════════════════════════════

@dataclass
class ROIInputs:
    nb_institutions: int = 1400
    nb_cases_per_year: int = 500
    complication_rate: float = 0.05
    cost_per_complication: int = 4000
    prevention_rate: float = 0.15


@dataclass
class ROIOutputs:
    cases_total: int = 0
    complications: int = 0
    prevented: int = 0
    savings_per_year: int = 0
    time_saved_hours: int = 0


# ═══════════════════════════════════════════════════════
# SESSION STATE KEYS — CONVENTION PARTAGÉE
# ═══════════════════════════════════════════════════════
# Le frontend et le backend utilisent ces clés dans
# st.session_state. NE PAS changer ces noms.

SESSION_KEYS = {
    # Pipeline
    "pipeline_status": PipelineStatus,        # PipelineStatus enum
    "pipeline_stats": PipelineStats,          # Stats finales du pipeline
    "pipeline_progress": PipelineProgress,    # Progress en cours

    # Données chargées (DataFrames)
    "dataframes": dict,                       # {filename: pd.DataFrame}
    "ingestion_results": dict,                # {filename: IngestionResult}

    # Qualité
    "quality_scores": dict,                   # {filename: SourceQualityScore}
    "audit_log": list,                        # [AuditLogEntry, ...]

    # Agents
    "agent_stats": AgentStats,                # Stats agents
    "column_mappings": list,                  # [ColumnMapping, ...]

    # Alertes
    "clinical_alerts": list,                  # [ClinicalAlert, ...]

    # NLP
    "nlp_results": dict,                      # {case_id: [NursingNLPResult]}

    # Patient
    "selected_case": str,                     # case_id sélectionné
    "convergence_scores": dict,               # {case_id: ConvergenceScore}

    # DB
    "db_conn": object,                        # sqlite3.Connection
    "db_path": str,                           # chemin vers .db

    # Chat (Ask Your Data)
    "chat_history": list,                     # [AskDataResult, ...]

    # Corrections
    "pending_corrections": list,              # [DataPassport, ...]
    "correction_history": list,               # [CorrectionResult, ...]
}


# ═══════════════════════════════════════════════════════
# HELPER : initialiser le session_state
# Appelé au démarrage dans app.py
# ═══════════════════════════════════════════════════════

def init_session_state(st):
    """Initialise toutes les clés du session_state avec des valeurs par défaut."""
    defaults = {
        "pipeline_status": PipelineStatus.IDLE,
        "pipeline_stats": None,
        "pipeline_progress": None,
        "dataframes": {},
        "ingestion_results": {},
        "quality_scores": {},
        "audit_log": [],
        "agent_stats": AgentStats(),
        "column_mappings": [],
        "clinical_alerts": [],
        "nlp_results": {},
        "selected_case": None,
        "convergence_scores": {},
        "db_conn": None,
        "db_path": "data/db/medmap.db",
        "chat_history": [],
        "pending_corrections": [],
        "correction_history": [],
    }
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value
