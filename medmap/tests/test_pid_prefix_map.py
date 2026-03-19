"""Test PID prefix mapping configuration."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pipeline.cleaner import PID_PREFIX_MAP


class TestPIDPrefixMap:
    """Verify PID prefix mappings for all file types."""

    def test_labs_prefix(self):
        assert PID_PREFIX_MAP["labs"] == "LAB"

    def test_device_motion_prefix(self):
        assert PID_PREFIX_MAP["device_motion"] == "MOT"

    def test_device_1hz_prefix(self):
        assert PID_PREFIX_MAP["device_1hz"] == "MOT"

    def test_medication_prefix(self):
        assert PID_PREFIX_MAP["medication"] == "MED"

    def test_nursing_prefix(self):
        assert PID_PREFIX_MAP["nursing"] == "NUR"

    def test_epac_german_prefix(self):
        assert PID_PREFIX_MAP["epaAC_german"] == "EPA"

    def test_epac_sap_prefix(self):
        assert PID_PREFIX_MAP["epaAC_sap"] == "EPA"

    def test_epac_pivot_prefix(self):
        assert PID_PREFIX_MAP["epaAC_pivot"] == "EPA"

    def test_icd10_prefix(self):
        assert PID_PREFIX_MAP["icd10_ops"] == "ICD"

    def test_all_prefixes_are_uppercase(self):
        for ftype, prefix in PID_PREFIX_MAP.items():
            assert prefix == prefix.upper(), f"{ftype}: prefix {prefix} not uppercase"

    def test_all_prefixes_are_3_chars(self):
        for ftype, prefix in PID_PREFIX_MAP.items():
            assert len(prefix) == 3, f"{ftype}: prefix {prefix} length {len(prefix)}"

    def test_expected_file_types_covered(self):
        expected = {"labs", "device_motion", "device_1hz", "medication",
                    "nursing", "epaAC_german", "epaAC_sap", "epaAC_pivot", "icd10_ops"}
        actual = set(PID_PREFIX_MAP.keys())
        assert expected <= actual


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
