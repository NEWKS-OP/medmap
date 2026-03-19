"""Test SQL table insertion order configuration."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pipeline.sql_export import TABLE_INSERT_ORDER


class TestTableInsertOrder:
    """Verify table insertion order respects FK constraints."""

    def test_case_data_is_first(self):
        assert TABLE_INSERT_ORDER[0] == "tbCaseData"

    def test_labs_after_case(self):
        idx_case = TABLE_INSERT_ORDER.index("tbCaseData")
        idx_labs = TABLE_INSERT_ORDER.index("tbImportLabsData")
        assert idx_labs > idx_case

    def test_icd10_after_case(self):
        idx_case = TABLE_INSERT_ORDER.index("tbCaseData")
        idx_icd = TABLE_INSERT_ORDER.index("tbImportIcd10Data")
        assert idx_icd > idx_case

    def test_ac_after_case(self):
        idx_case = TABLE_INSERT_ORDER.index("tbCaseData")
        idx_ac = TABLE_INSERT_ORDER.index("tbImportAcData")
        assert idx_ac > idx_case

    def test_device_motion_after_case(self):
        idx_case = TABLE_INSERT_ORDER.index("tbCaseData")
        idx_dm = TABLE_INSERT_ORDER.index("tbImportDeviceMotionData")
        assert idx_dm > idx_case

    def test_device_1hz_after_case(self):
        idx_case = TABLE_INSERT_ORDER.index("tbCaseData")
        idx_1hz = TABLE_INSERT_ORDER.index("tbImportDevice1HzMotionData")
        assert idx_1hz > idx_case

    def test_medication_after_case(self):
        idx_case = TABLE_INSERT_ORDER.index("tbCaseData")
        idx_med = TABLE_INSERT_ORDER.index("tbImportMedicationInpatientData")
        assert idx_med > idx_case

    def test_nursing_after_case(self):
        idx_case = TABLE_INSERT_ORDER.index("tbCaseData")
        idx_nur = TABLE_INSERT_ORDER.index("tbImportNursingDailyReportsData")
        assert idx_nur > idx_case

    def test_all_8_tables(self):
        assert len(TABLE_INSERT_ORDER) == 8

    def test_no_duplicates(self):
        assert len(TABLE_INSERT_ORDER) == len(set(TABLE_INSERT_ORDER))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
