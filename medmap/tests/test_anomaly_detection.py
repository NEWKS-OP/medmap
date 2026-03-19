"""Tests for pipeline/anomaly.py — clinical anomaly detection engine."""

import sqlite3
import pytest
from pipeline.anomaly import AnomalyDetector, _safe_float


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite DB with test data."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    # Create tables
    conn.executescript("""
        CREATE TABLE tbCaseData (
            coId INTEGER PRIMARY KEY,
            coCaseIdAlpha TEXT,
            coPatientId TEXT
        );

        CREATE TABLE tbImportLabsData (
            coId INTEGER PRIMARY KEY AUTOINCREMENT,
            coCaseId INTEGER,
            coSpecimen_datetime TEXT,
            coCreatinine_mg_dL TEXT,
            coEgfr_mL_min_1_73m2 TEXT,
            coPotassium_mmol_L TEXT,
            coCrp_mg_L TEXT,
            coLactate_mmol_L TEXT,
            coWbc_10e9_L TEXT,
            coInr TEXT
        );

        CREATE TABLE tbImportDeviceMotionData (
            coId INTEGER PRIMARY KEY AUTOINCREMENT,
            coCaseId INTEGER,
            coTimestamp TEXT,
            coFall_event_0_1 TEXT,
            coPost_fall_immobility_minutes TEXT
        );

        CREATE TABLE tbImportMedicationInpatientData (
            coId INTEGER PRIMARY KEY AUTOINCREMENT,
            coCaseId INTEGER,
            coMedication_name TEXT
        );

        CREATE TABLE tbImportNursingDailyReportsData (
            coId INTEGER PRIMARY KEY AUTOINCREMENT,
            coCaseId INTEGER,
            coNursing_note_free_text TEXT,
            coDeterioration_flag INTEGER,
            coDeterioration_signs TEXT
        );
    """)

    # Insert test cases
    conn.executemany("INSERT INTO tbCaseData (coId, coCaseIdAlpha) VALUES (?, ?)",
                     [(1, "CASE-001"), (2, "CASE-002"), (3, "CASE-003"),
                      (4, "CASE-004"), (5, "CASE-005"), (6, "CASE-006")])

    # Case 1: AKI patient (creat > 3.0, egfr < 20, K > 5.5)
    conn.execute(
        """INSERT INTO tbImportLabsData (coCaseId, coSpecimen_datetime,
           coCreatinine_mg_dL, coEgfr_mL_min_1_73m2, coPotassium_mmol_L,
           coCrp_mg_L, coLactate_mmol_L, coWbc_10e9_L, coInr)
           VALUES (1, '2025-01-01', '4.5', '12', '6.1', '5', '1.0', '7', '1.0')"""
    )

    # Case 2: Sepsis patient (CRP > 100, lactate > 2.0, WBC > 12)
    conn.execute(
        """INSERT INTO tbImportLabsData (coCaseId, coSpecimen_datetime,
           coCreatinine_mg_dL, coEgfr_mL_min_1_73m2, coPotassium_mmol_L,
           coCrp_mg_L, coLactate_mmol_L, coWbc_10e9_L, coInr)
           VALUES (2, '2025-01-01', '1.0', '90', '4.0', '150', '3.5', '15', '1.0')"""
    )

    # Case 3: Fall risk (fall with immobility > 15)
    conn.execute(
        """INSERT INTO tbImportDeviceMotionData (coCaseId, coTimestamp,
           coFall_event_0_1, coPost_fall_immobility_minutes)
           VALUES (3, '2025-01-01 03:00', '1', '45')"""
    )

    # Case 4: Dangerous med + AKI (eGFR < 30 + Metformin)
    conn.execute(
        """INSERT INTO tbImportLabsData (coCaseId, coSpecimen_datetime,
           coCreatinine_mg_dL, coEgfr_mL_min_1_73m2, coPotassium_mmol_L,
           coCrp_mg_L, coLactate_mmol_L, coWbc_10e9_L, coInr)
           VALUES (4, '2025-01-01', '2.0', '22', '4.0', '5', '1.0', '7', '1.0')"""
    )
    conn.execute(
        "INSERT INTO tbImportMedicationInpatientData (coCaseId, coMedication_name) VALUES (4, 'Metformin 500mg')"
    )

    # Case 5: Anticoagulant + abnormal INR
    conn.execute(
        """INSERT INTO tbImportLabsData (coCaseId, coSpecimen_datetime,
           coCreatinine_mg_dL, coEgfr_mL_min_1_73m2, coPotassium_mmol_L,
           coCrp_mg_L, coLactate_mmol_L, coWbc_10e9_L, coInr)
           VALUES (5, '2025-01-01', '1.0', '90', '4.0', '5', '1.0', '7', '5.5')"""
    )
    conn.execute(
        "INSERT INTO tbImportMedicationInpatientData (coCaseId, coMedication_name) VALUES (5, 'Warfarin 5mg')"
    )

    # Case 6: Multi-source deterioration (nursing + fall)
    conn.execute(
        """INSERT INTO tbImportNursingDailyReportsData (coCaseId, coNursing_note_free_text,
           coDeterioration_flag, coDeterioration_signs)
           VALUES (6, 'Patient confused and agitated', 1, 'confused,agitated')"""
    )
    conn.execute(
        """INSERT INTO tbImportDeviceMotionData (coCaseId, coTimestamp,
           coFall_event_0_1, coPost_fall_immobility_minutes)
           VALUES (6, '2025-01-01 04:00', '1', '5')"""
    )

    conn.commit()
    yield conn
    conn.close()


class TestSafeFloat:
    def test_normal_float(self):
        assert _safe_float("3.14") == 3.14

    def test_int_string(self):
        assert _safe_float("42") == 42.0

    def test_none(self):
        assert _safe_float(None) is None

    def test_empty_string(self):
        assert _safe_float("") is None

    def test_garbage(self):
        assert _safe_float("abc") is None

    def test_actual_float(self):
        assert _safe_float(2.5) == 2.5


class TestAnomalyDetector:
    def test_detect_all_returns_list(self, in_memory_db):
        detector = AnomalyDetector(conn=in_memory_db)
        alerts = detector.detect_all()
        assert isinstance(alerts, list)

    def test_aki_detected(self, in_memory_db):
        detector = AnomalyDetector(conn=in_memory_db)
        alerts = detector.detect_all()
        aki = [a for a in alerts if a.rule_name == "AKI_PROBABLE"]
        assert len(aki) == 1
        assert aki[0].case_id == "1"
        assert aki[0].severity.value == "CRITICAL"
        assert aki[0].triggered_values["creatinine_mg_dL"] == 4.5

    def test_sepsis_detected(self, in_memory_db):
        detector = AnomalyDetector(conn=in_memory_db)
        alerts = detector.detect_all()
        sepsis = [a for a in alerts if a.rule_name == "SEPSIS_POSSIBLE"]
        assert len(sepsis) == 1
        assert sepsis[0].case_id == "2"
        assert sepsis[0].triggered_values["crp_mg_L"] == 150.0

    def test_fall_risk_detected(self, in_memory_db):
        detector = AnomalyDetector(conn=in_memory_db)
        alerts = detector.detect_all()
        falls = [a for a in alerts if a.rule_name == "HIGH_FALL_RISK"]
        assert len(falls) >= 1
        fall_case_ids = {a.case_id for a in falls}
        assert "3" in fall_case_ids

    def test_dangerous_med_detected(self, in_memory_db):
        detector = AnomalyDetector(conn=in_memory_db)
        alerts = detector.detect_all()
        meds = [a for a in alerts if a.rule_name == "DANGEROUS_MED_AKI"]
        assert len(meds) == 1
        assert meds[0].case_id == "4"
        assert "Metformin" in meds[0].triggered_values["medication_name"]

    def test_anticoag_inr_detected(self, in_memory_db):
        detector = AnomalyDetector(conn=in_memory_db)
        alerts = detector.detect_all()
        ac = [a for a in alerts if a.rule_name == "ANTICOAG_INR_ABNORMAL"]
        assert len(ac) == 1
        assert ac[0].case_id == "5"
        assert ac[0].triggered_values["inr"] == 5.5

    def test_multi_source_deterioration_detected(self, in_memory_db):
        detector = AnomalyDetector(conn=in_memory_db)
        alerts = detector.detect_all()
        multi = [a for a in alerts if a.rule_name == "MULTI_SOURCE_DETERIORATION"]
        assert len(multi) == 1
        assert multi[0].case_id == "6"
        assert "nursing" in multi[0].sources_involved
        assert "motion" in multi[0].sources_involved

    def test_summary_stats(self, in_memory_db):
        detector = AnomalyDetector(conn=in_memory_db)
        alerts = detector.detect_all()
        summary = detector.get_summary(alerts)
        assert summary["total_alerts"] >= 6
        assert summary["affected_patients"] >= 6
        assert "AKI_PROBABLE" in summary["by_rule"]
        assert "CRITICAL" in summary["by_severity"]

    def test_no_db_returns_empty(self):
        detector = AnomalyDetector()
        alerts = detector.detect_all()
        assert alerts == []

    def test_empty_db(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript("""
            CREATE TABLE tbCaseData (coId INTEGER PRIMARY KEY);
            CREATE TABLE tbImportLabsData (coId INTEGER PRIMARY KEY AUTOINCREMENT, coCaseId INTEGER, coSpecimen_datetime TEXT, coCreatinine_mg_dL TEXT, coEgfr_mL_min_1_73m2 TEXT, coPotassium_mmol_L TEXT, coCrp_mg_L TEXT, coLactate_mmol_L TEXT, coWbc_10e9_L TEXT, coInr TEXT);
            CREATE TABLE tbImportDeviceMotionData (coId INTEGER PRIMARY KEY AUTOINCREMENT, coCaseId INTEGER, coTimestamp TEXT, coFall_event_0_1 TEXT, coPost_fall_immobility_minutes TEXT);
            CREATE TABLE tbImportMedicationInpatientData (coId INTEGER PRIMARY KEY AUTOINCREMENT, coCaseId INTEGER, coMedication_name TEXT);
            CREATE TABLE tbImportNursingDailyReportsData (coId INTEGER PRIMARY KEY AUTOINCREMENT, coCaseId INTEGER, coNursing_note_free_text TEXT, coDeterioration_flag INTEGER, coDeterioration_signs TEXT);
        """)
        detector = AnomalyDetector(conn=conn)
        alerts = detector.detect_all()
        assert alerts == []
        conn.close()


class TestNoFalsePositives:
    """Verify that normal values don't trigger alerts."""

    def test_normal_labs_no_aki(self, in_memory_db):
        """Case 2 has normal creatinine — should not trigger AKI."""
        detector = AnomalyDetector(conn=in_memory_db)
        alerts = detector.detect_all()
        aki = [a for a in alerts if a.rule_name == "AKI_PROBABLE"]
        assert all(a.case_id == "1" for a in aki)

    def test_no_fall_without_event(self, in_memory_db):
        """Only cases with fall_event=1 + immobility>15 should fire."""
        detector = AnomalyDetector(conn=in_memory_db)
        alerts = detector.detect_all()
        falls = [a for a in alerts if a.rule_name == "HIGH_FALL_RISK"]
        # Case 6 has fall but immobility=5 (< 15), should not trigger
        assert all(a.case_id != "6" or False for a in falls if a.rule_name == "HIGH_FALL_RISK")
