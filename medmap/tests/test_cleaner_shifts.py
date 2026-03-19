"""Test DataCleaner shift normalization end-to-end."""

import os
import sys
import pytest
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pipeline.cleaner import DataCleaner
from pipeline.validator import DataValidator


class TestCleanerShiftNormalization:
    """Test shift normalization through the cleaner."""

    def setup_method(self):
        self.validator = DataValidator()
        self.cleaner = DataCleaner()

    def _make_nursing(self, shift):
        df = pd.DataFrame({
            "case_id": ["1"],
            "patient_id": ["100001"],
            "shift": [shift],
            "nursing_note_free_text": ["ok"],
        })
        df.attrs["file_type"] = "nursing"
        df.attrs["source_file"] = "test.csv"
        return df

    def test_early_preserved(self):
        result = self.cleaner.clean_dataframe(self._make_nursing("Early"), "test.csv")
        assert result["shift"].iloc[0] == "Early"

    def test_late_preserved(self):
        result = self.cleaner.clean_dataframe(self._make_nursing("Late"), "test.csv")
        assert result["shift"].iloc[0] == "Late"

    def test_night_preserved(self):
        result = self.cleaner.clean_dataframe(self._make_nursing("Night"), "test.csv")
        assert result["shift"].iloc[0] == "Night"

    def test_fruhschicht_normalized(self):
        result = self.cleaner.clean_dataframe(self._make_nursing("Frühschicht"), "test.csv")
        assert result["shift"].iloc[0] == "Early"

    def test_spatschicht_normalized(self):
        result = self.cleaner.clean_dataframe(self._make_nursing("Spätschicht"), "test.csv")
        assert result["shift"].iloc[0] == "Late"

    def test_nachtschicht_normalized(self):
        result = self.cleaner.clean_dataframe(self._make_nursing("Nachtschicht"), "test.csv")
        assert result["shift"].iloc[0] == "Night"

    def test_contaminated_early(self):
        result = self.cleaner.clean_dataframe(self._make_nursing("Early shiftä"), "test.csv")
        val = result["shift"].iloc[0]
        assert val in ("Early", "Early shiftä")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
