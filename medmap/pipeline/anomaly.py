"""
Module 5: Anomaly Detection (BONUS)
Cross-dataset correlation rules for clinical alerts.

6 rules that correlate data across labs, motion, medication, and nursing:
1. AKI probable     — creatinine > 3.0, eGFR < 20, potassium > 5.5
2. Sepsis possible  — CRP > 100, lactate > 2.0, WBC > 12
3. High fall risk   — fall_event=1, immobility > 15 min
4. Dangerous med + AKI — eGFR < 30 + nephrotoxic meds
5. Multi-source deterioration — nursing deterioration + fall or refused
6. Anticoagulant + abnormal INR — warfarin/phenprocoumon + INR outside 2.0-4.0
"""

import logging
import sqlite3
from datetime import datetime
from typing import Optional

from config.clinical_rules import ANOMALY_RULES
from contracts import ClinicalAlert, Severity

logger = logging.getLogger(__name__)


def _safe_float(val) -> Optional[float]:
    """Safely convert a value to float, returning None on failure."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """Check if a table has a specific column."""
    try:
        cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        return column in cols
    except sqlite3.OperationalError:
        return False


class AnomalyDetector:
    """Detects clinical anomalies by correlating data across multiple tables.

    Uses set-based SQL queries for efficiency (not per-case loops).
    """

    def __init__(self, db_path: str = None, conn: sqlite3.Connection = None):
        if conn:
            self.conn = conn
        elif db_path:
            self.conn = sqlite3.connect(db_path)
            self.conn.row_factory = sqlite3.Row
        else:
            self.conn = None

    def detect_all(self) -> list[ClinicalAlert]:
        """Run all 6 anomaly detection rules. Returns list of ClinicalAlert."""
        if not self.conn:
            logger.warning("No DB connection, skipping anomaly detection")
            return []

        alerts: list[ClinicalAlert] = []

        alerts.extend(self._check_aki_batch())
        alerts.extend(self._check_sepsis_batch())
        alerts.extend(self._check_fall_risk_batch())
        alerts.extend(self._check_dangerous_med_aki_batch())
        alerts.extend(self._check_multi_source_deterioration_batch())
        alerts.extend(self._check_anticoag_inr_batch())

        logger.info("Anomaly detection: %d alerts (%d patients)",
                     len(alerts), len({a.case_id for a in alerts}))
        return alerts

    # ─── Rule 1: AKI Probable ─────────────────────────────────────

    def _check_aki_batch(self) -> list[ClinicalAlert]:
        """Rule 1: AKI probable — creatinine > 3.0 AND eGFR < 20 AND K+ > 5.5."""
        rule = ANOMALY_RULES["AKI_PROBABLE"]
        alerts = []
        try:
            rows = self.conn.execute(
                """SELECT coCaseId,
                          CAST(coCreatinine_mg_dL AS REAL) as creat,
                          CAST(coEgfr_mL_min_1_73m2 AS REAL) as egfr,
                          CAST(coPotassium_mmol_L AS REAL) as k
                   FROM tbImportLabsData
                   WHERE CAST(coCreatinine_mg_dL AS REAL) > 3.0
                     AND CAST(coEgfr_mL_min_1_73m2 AS REAL) < 20
                     AND CAST(coPotassium_mmol_L AS REAL) > 5.5
                   GROUP BY coCaseId"""
            ).fetchall()

            for r in rows:
                alerts.append(ClinicalAlert(
                    case_id=str(r["coCaseId"]),
                    rule_name="AKI_PROBABLE",
                    severity=Severity.CRITICAL,
                    message=rule["message"],
                    sources_involved=["labs"],
                    triggered_values={
                        "creatinine_mg_dL": r["creat"],
                        "egfr_mL_min_1_73m2": r["egfr"],
                        "potassium_mmol_L": r["k"],
                    },
                ))
            logger.info("AKI rule: %d alerts", len(alerts))
        except sqlite3.OperationalError as e:
            logger.warning("AKI check failed: %s", e)
        return alerts

    # ─── Rule 2: Sepsis Possible ──────────────────────────────────

    def _check_sepsis_batch(self) -> list[ClinicalAlert]:
        """Rule 2: Sepsis — CRP > 100 AND lactate > 2.0 AND WBC > 12."""
        rule = ANOMALY_RULES["SEPSIS_POSSIBLE"]
        alerts = []
        try:
            rows = self.conn.execute(
                """SELECT coCaseId,
                          CAST(coCrp_mg_L AS REAL) as crp,
                          CAST(coLactate_mmol_L AS REAL) as lactate,
                          CAST(coWbc_10e9_L AS REAL) as wbc
                   FROM tbImportLabsData
                   WHERE CAST(coCrp_mg_L AS REAL) > 100
                     AND CAST(coLactate_mmol_L AS REAL) > 2.0
                     AND CAST(coWbc_10e9_L AS REAL) > 12
                   GROUP BY coCaseId"""
            ).fetchall()

            for r in rows:
                alerts.append(ClinicalAlert(
                    case_id=str(r["coCaseId"]),
                    rule_name="SEPSIS_POSSIBLE",
                    severity=Severity.CRITICAL,
                    message=rule["message"],
                    sources_involved=["labs"],
                    triggered_values={
                        "crp_mg_L": r["crp"],
                        "lactate_mmol_L": r["lactate"],
                        "wbc_10e9_L": r["wbc"],
                    },
                ))
            logger.info("Sepsis rule: %d alerts", len(alerts))
        except sqlite3.OperationalError as e:
            logger.warning("Sepsis check failed: %s", e)
        return alerts

    # ─── Rule 3: High Fall Risk ───────────────────────────────────

    def _check_fall_risk_batch(self) -> list[ClinicalAlert]:
        """Rule 3: Fall risk — fall_event=1 AND immobility > 15 min."""
        rule = ANOMALY_RULES["HIGH_FALL_RISK"]
        alerts = []
        try:
            rows = self.conn.execute(
                """SELECT coCaseId,
                          MAX(CAST(coPost_fall_immobility_minutes AS REAL)) as max_immobility
                   FROM tbImportDeviceMotionData
                   WHERE coFall_event_0_1 = '1'
                     AND CAST(coPost_fall_immobility_minutes AS REAL) > 15
                   GROUP BY coCaseId"""
            ).fetchall()

            for r in rows:
                alerts.append(ClinicalAlert(
                    case_id=str(r["coCaseId"]),
                    rule_name="HIGH_FALL_RISK",
                    severity=Severity.HIGH,
                    message=rule["message"],
                    sources_involved=["motion"],
                    triggered_values={
                        "fall_event": 1,
                        "post_fall_immobility_minutes": r["max_immobility"],
                    },
                ))
            logger.info("Fall risk rule: %d alerts", len(alerts))
        except sqlite3.OperationalError as e:
            logger.warning("Fall risk check failed: %s", e)
        return alerts

    # ─── Rule 4: Dangerous Medication + AKI ───────────────────────

    def _check_dangerous_med_aki_batch(self) -> list[ClinicalAlert]:
        """Rule 4: Dangerous med with eGFR < 30."""
        rule = ANOMALY_RULES["DANGEROUS_MED_AKI"]
        dangerous_meds = rule.get("med_names", [])
        alerts = []

        try:
            # Find patients with eGFR < 30
            low_egfr = self.conn.execute(
                """SELECT coCaseId, MIN(CAST(coEgfr_mL_min_1_73m2 AS REAL)) as min_egfr
                   FROM tbImportLabsData
                   WHERE CAST(coEgfr_mL_min_1_73m2 AS REAL) < 30
                     AND CAST(coEgfr_mL_min_1_73m2 AS REAL) > 0
                   GROUP BY coCaseId"""
            ).fetchall()

            low_egfr_map = {str(r["coCaseId"]): r["min_egfr"] for r in low_egfr}
            if not low_egfr_map:
                return []

            # Check medications for those patients
            placeholders = ",".join("?" for _ in low_egfr_map)
            med_rows = self.conn.execute(
                f"""SELECT DISTINCT coCaseId, coMedication_name
                    FROM tbImportMedicationInpatientData
                    WHERE coCaseId IN ({placeholders})
                      AND coMedication_name IS NOT NULL""",
                list(low_egfr_map.keys()),
            ).fetchall()

            seen_cases = set()
            for med_row in med_rows:
                cid = str(med_row["coCaseId"])
                if cid in seen_cases:
                    continue
                med_name = (med_row["coMedication_name"] or "").lower()
                for dangerous in dangerous_meds:
                    if dangerous.lower() in med_name:
                        seen_cases.add(cid)
                        alerts.append(ClinicalAlert(
                            case_id=cid,
                            rule_name="DANGEROUS_MED_AKI",
                            severity=Severity.CRITICAL,
                            message=f"{rule['message']}: {med_row['coMedication_name']}",
                            sources_involved=["labs", "medication"],
                            triggered_values={
                                "egfr_mL_min_1_73m2": low_egfr_map[cid],
                                "medication_name": med_row["coMedication_name"],
                            },
                        ))
                        break

            logger.info("Dangerous med+AKI rule: %d alerts", len(alerts))
        except sqlite3.OperationalError as e:
            logger.warning("Dangerous med check failed: %s", e)
        return alerts

    # ─── Rule 5: Multi-Source Deterioration ───────────────────────

    def _check_multi_source_deterioration_batch(self) -> list[ClinicalAlert]:
        """Rule 5: Deterioration from nursing + fall or refused medication."""
        rule = ANOMALY_RULES["MULTI_SOURCE_DETERIORATION"]
        alerts = []

        try:
            # Get cases with nursing deterioration
            det_case_ids = set()
            if _has_column(self.conn, "tbImportNursingDailyReportsData", "coDeterioration_flag"):
                rows = self.conn.execute(
                    """SELECT DISTINCT coCaseId
                       FROM tbImportNursingDailyReportsData
                       WHERE coDeterioration_flag = 1"""
                ).fetchall()
                det_case_ids = {str(r["coCaseId"]) for r in rows}
            else:
                # Fallback: scan notes with NLP on-the-fly
                from pipeline.nlp import analyze_note
                rows = self.conn.execute(
                    "SELECT DISTINCT coCaseId, coNursing_note_free_text FROM tbImportNursingDailyReportsData"
                ).fetchall()
                for r in rows:
                    nlp = analyze_note(r["coNursing_note_free_text"] or "")
                    if nlp["deterioration_flag"]:
                        det_case_ids.add(str(r["coCaseId"]))

            if not det_case_ids:
                return []

            # Get cases with falls
            fall_case_ids = set()
            try:
                fall_rows = self.conn.execute(
                    "SELECT DISTINCT coCaseId FROM tbImportDeviceMotionData WHERE coFall_event_0_1 = '1'"
                ).fetchall()
                fall_case_ids = {str(r["coCaseId"]) for r in fall_rows}
            except sqlite3.OperationalError:
                pass

            # Get cases with refused (from NLP signs)
            refused_case_ids = set()
            if _has_column(self.conn, "tbImportNursingDailyReportsData", "coDeterioration_signs"):
                refused_rows = self.conn.execute(
                    """SELECT DISTINCT coCaseId
                       FROM tbImportNursingDailyReportsData
                       WHERE coDeterioration_signs LIKE '%refused%'"""
                ).fetchall()
                refused_case_ids = {str(r["coCaseId"]) for r in refused_rows}

            # Intersect: deterioration + (fall OR refused)
            multi_source = det_case_ids & (fall_case_ids | refused_case_ids)

            for cid in multi_source:
                sources = ["nursing"]
                triggered = {"deterioration_flag": True}
                if cid in fall_case_ids:
                    sources.append("motion")
                    triggered["fall_event"] = True
                if cid in refused_case_ids:
                    triggered["refused_medication"] = True

                alerts.append(ClinicalAlert(
                    case_id=cid,
                    rule_name="MULTI_SOURCE_DETERIORATION",
                    severity=Severity.HIGH,
                    message=rule["message"],
                    sources_involved=sources,
                    triggered_values=triggered,
                ))

            logger.info("Multi-source deterioration rule: %d alerts", len(alerts))
        except sqlite3.OperationalError as e:
            logger.warning("Multi-source deterioration check failed: %s", e)
        return alerts

    # ─── Rule 6: Anticoagulant + INR Abnormal ────────────────────

    def _check_anticoag_inr_batch(self) -> list[ClinicalAlert]:
        """Rule 6: Anticoagulant + INR outside 2.0-4.0."""
        rule = ANOMALY_RULES["ANTICOAG_INR_ABNORMAL"]
        anticoag_meds = rule.get("med_names", [])
        inr_low, inr_high = rule.get("inr_range", (2.0, 4.0))
        alerts = []

        try:
            # Build LIKE conditions for anticoagulant names
            like_conditions = " OR ".join(
                f"LOWER(coMedication_name) LIKE '%{med.lower()}%'"
                for med in anticoag_meds
            )
            if not like_conditions:
                return []

            # Find patients on anticoagulants
            ac_rows = self.conn.execute(
                f"""SELECT DISTINCT coCaseId, coMedication_name
                    FROM tbImportMedicationInpatientData
                    WHERE {like_conditions}"""
            ).fetchall()

            if not ac_rows:
                return []

            ac_map = {}  # cid -> med_name
            for r in ac_rows:
                ac_map[str(r["coCaseId"])] = r["coMedication_name"]

            # Check INR for those patients
            placeholders = ",".join("?" for _ in ac_map)
            inr_rows = self.conn.execute(
                f"""SELECT coCaseId,
                           CAST(coInr AS REAL) as inr_val
                    FROM tbImportLabsData
                    WHERE coCaseId IN ({placeholders})
                      AND coInr IS NOT NULL
                      AND (CAST(coInr AS REAL) < ? OR CAST(coInr AS REAL) > ?)
                    GROUP BY coCaseId""",
                list(ac_map.keys()) + [inr_low, inr_high],
            ).fetchall()

            for r in inr_rows:
                cid = str(r["coCaseId"])
                alerts.append(ClinicalAlert(
                    case_id=cid,
                    rule_name="ANTICOAG_INR_ABNORMAL",
                    severity=Severity.HIGH,
                    message=f"{rule['message']}: {ac_map.get(cid, 'unknown')}, INR={r['inr_val']}",
                    sources_involved=["labs", "medication"],
                    triggered_values={
                        "inr": r["inr_val"],
                        "medication_name": ac_map.get(cid, "unknown"),
                    },
                ))

            logger.info("Anticoag+INR rule: %d alerts", len(alerts))
        except sqlite3.OperationalError as e:
            logger.warning("Anticoag+INR check failed: %s", e)
        return alerts

    # ─── Summary stats ────────────────────────────────────────────

    def get_summary(self, alerts: list[ClinicalAlert]) -> dict:
        """Get summary statistics from detected alerts."""
        by_rule: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        for a in alerts:
            by_rule[a.rule_name] = by_rule.get(a.rule_name, 0) + 1
            sev = a.severity.value if isinstance(a.severity, Severity) else str(a.severity)
            by_severity[sev] = by_severity.get(sev, 0) + 1

        return {
            "total_alerts": len(alerts),
            "by_rule": by_rule,
            "by_severity": by_severity,
            "affected_patients": len({a.case_id for a in alerts}),
        }
