"""Test DataMapper initialization and helpers."""

import os
import sys
import pytest
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pipeline.mapper import DataMapper


class TestDataMapperInit:
    """Test DataMapper initialization."""

    def test_default_no_iid_sid(self):
        m = DataMapper()
        assert m.iid_sid_map is None

    def test_mapped_tables_empty(self):
        m = DataMapper()
        assert m.mapped_tables == {}

    def test_mapping_warnings_empty(self):
        m = DataMapper()
        assert m.mapping_warnings == []

    def test_sap_decoder_empty_without_map(self):
        m = DataMapper()
        assert m.sap_decoder == {}

    def test_sid_to_iid_empty_without_map(self):
        m = DataMapper()
        assert m.sid_to_iid == {}


class TestDataMapperGroupByType:
    """Test _group_by_type helper."""

    def test_empty_input(self):
        m = DataMapper()
        result = m._group_by_type({})
        assert result == {}

    def test_single_labs_file(self):
        m = DataMapper()
        df = pd.DataFrame({"a": [1]})
        df.attrs["file_type"] = "labs"
        result = m._group_by_type({"test.csv": df})
        assert "labs" in result
        assert len(result["labs"]) == 1

    def test_two_files_same_type(self):
        m = DataMapper()
        df1 = pd.DataFrame({"a": [1]})
        df1.attrs["file_type"] = "labs"
        df2 = pd.DataFrame({"a": [2]})
        df2.attrs["file_type"] = "labs"
        result = m._group_by_type({"a.csv": df1, "b.csv": df2})
        assert len(result["labs"]) == 2

    def test_different_types(self):
        m = DataMapper()
        df1 = pd.DataFrame({"a": [1]})
        df1.attrs["file_type"] = "labs"
        df2 = pd.DataFrame({"a": [2]})
        df2.attrs["file_type"] = "nursing"
        result = m._group_by_type({"a.csv": df1, "b.csv": df2})
        assert "labs" in result
        assert "nursing" in result

    def test_unknown_type(self):
        m = DataMapper()
        df = pd.DataFrame({"a": [1]})
        result = m._group_by_type({"test.csv": df})
        assert "unknown" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
