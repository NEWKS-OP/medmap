"""Test shift normalization map entries."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pipeline.cleaner import DataCleaner


class TestShiftMapEntries:
    """Test individual shift map entries."""

    def setup_method(self):
        self.shift_map = DataCleaner.SHIFT_MAP if hasattr(DataCleaner, 'SHIFT_MAP') else {}
        # If SHIFT_MAP is module-level, import it
        if not self.shift_map:
            from pipeline.cleaner import SHIFT_MAP
            self.shift_map = SHIFT_MAP

    def test_early_english(self):
        assert self.shift_map.get("early") == "Early"

    def test_early_shift(self):
        assert self.shift_map.get("early shift") == "Early"

    def test_fruhschicht(self):
        assert self.shift_map.get("frühschicht") == "Early"

    def test_late_english(self):
        assert self.shift_map.get("late") == "Late"

    def test_late_shift(self):
        assert self.shift_map.get("late shift") == "Late"

    def test_spatschicht(self):
        assert self.shift_map.get("spätschicht") == "Late"

    def test_night_english(self):
        assert self.shift_map.get("night") == "Night"

    def test_night_shift(self):
        assert self.shift_map.get("night shift") == "Night"

    def test_nachtschicht(self):
        assert self.shift_map.get("nachtschicht") == "Night"

    def test_all_values_are_valid(self):
        valid_shifts = {"Early", "Late", "Night"}
        for key, val in self.shift_map.items():
            assert val in valid_shifts, f"Key '{key}' maps to invalid shift '{val}'"

    def test_all_keys_are_lowercase(self):
        for key in self.shift_map:
            assert key == key.lower(), f"Key '{key}' is not lowercase"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
