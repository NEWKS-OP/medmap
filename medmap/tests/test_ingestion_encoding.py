"""Test DataIngester encoding detection and initialization."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pipeline.ingestion import DataIngester


class TestDataIngesterInit:
    """Test DataIngester initialization."""

    def test_dataframes_empty(self):
        ing = DataIngester()
        assert ing.dataframes == {}

    def test_ingestion_results_empty(self):
        ing = DataIngester()
        assert ing.ingestion_results == {}

    def test_iid_sid_map_none(self):
        ing = DataIngester()
        assert ing.iid_sid_map is None

    def test_streaming_callback_none(self):
        ing = DataIngester()
        assert ing._streaming_callback is None

    def test_set_streaming_callback(self):
        ing = DataIngester()
        cb = lambda x: x
        ing.set_streaming_callback(cb)
        assert ing._streaming_callback is cb


class TestDataIngesterEncoding:
    """Test encoding detection method."""

    def test_detect_encoding_returns_string(self):
        ing = DataIngester()
        # Use any existing file
        test_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "config", "settings.py"
        )
        enc = ing._detect_encoding(test_file)
        assert isinstance(enc, str)
        assert len(enc) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
