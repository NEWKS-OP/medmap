"""Test IID-SID-ITEM file exists and has expected columns."""

import os
import sys
import pytest
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config.settings import IID_SID_ITEM_PATH


class TestIIDSIDFile:
    """Test IID-SID-ITEM decoder file."""

    def test_file_exists(self):
        assert os.path.exists(IID_SID_ITEM_PATH)

    def test_is_csv(self):
        assert IID_SID_ITEM_PATH.endswith(".csv")

    def test_readable(self):
        df = pd.read_csv(IID_SID_ITEM_PATH, sep=";", nrows=5)
        assert len(df) > 0

    def test_has_ItmIID_column(self):
        df = pd.read_csv(IID_SID_ITEM_PATH, sep=";", nrows=1)
        assert "ItmIID" in df.columns

    def test_has_ItmSID_column(self):
        df = pd.read_csv(IID_SID_ITEM_PATH, sep=";", nrows=1)
        assert "ItmSID" in df.columns

    def test_has_name_column(self):
        df = pd.read_csv(IID_SID_ITEM_PATH, sep=";", nrows=1)
        name_cols = [c for c in df.columns if "name" in c.lower() or "Name" in c]
        assert len(name_cols) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
