"""Test DataCleaner event type normalization end-to-end."""

import os
import sys
import pytest
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pipeline.cleaner import DataCleaner


class TestCleanerEventTypeNormalization:
    """Test event type normalization through the cleaner."""

    def setup_method(self):
        self.cleaner = DataCleaner()

    def _make_med(self, event_type):
        df = pd.DataFrame({
            "case_id": ["1"],
            "patient_id": ["100001"],
            "record_type": [event_type],
            "medication_name": ["Aspirin"],
            "medication_code_atc": ["B01AC06"],
        })
        df.attrs["file_type"] = "medication"
        df.attrs["source_file"] = "test.csv"
        return df

    def test_order_preserved(self):
        result = self.cleaner.clean_dataframe(self._make_med("ORDER"), "test.csv")
        assert result["record_type"].iloc[0] == "ORDER"

    def test_admin_preserved(self):
        result = self.cleaner.clean_dataframe(self._make_med("ADMIN"), "test.csv")
        assert result["record_type"].iloc[0] == "ADMIN"

    def test_change_preserved(self):
        result = self.cleaner.clean_dataframe(self._make_med("CHANGE"), "test.csv")
        assert result["record_type"].iloc[0] == "CHANGE"

    def test_lowercase_normalized(self):
        result = self.cleaner.clean_dataframe(self._make_med("order"), "test.csv")
        assert result["record_type"].iloc[0] == "ORDER"

    def test_contaminated_admin(self):
        result = self.cleaner.clean_dataframe(self._make_med("ADMINä"), "test.csv")
        assert result["record_type"].iloc[0] == "ADMIN"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
