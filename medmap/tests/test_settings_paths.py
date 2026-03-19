"""Test settings configuration paths and defaults."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config.settings import (
    DB_TYPE, DB_PATH, CHUNK_SIZE, LOG_LEVEL,
    PID_PREFIX_STRATEGY, DATA_DIR, DIRTY_DIR,
    CLEAN_DIR, SPLIT_DIR, DB_DIR,
)


class TestSettingsDefaults:
    """Test default setting values."""

    def test_db_type_default(self):
        assert DB_TYPE == "sqlite"

    def test_db_path_default(self):
        assert "medmap.db" in DB_PATH

    def test_chunk_size_default(self):
        assert CHUNK_SIZE == 5000

    def test_log_level_default(self):
        assert LOG_LEVEL == "INFO"

    def test_pid_prefix_strategy_default(self):
        assert PID_PREFIX_STRATEGY is True


class TestSettingsPaths:
    """Test path configuration."""

    def test_data_dir_ends_with_data(self):
        assert DATA_DIR.endswith("data")

    def test_dirty_dir_ends_with_dirty(self):
        assert DIRTY_DIR.endswith("dirty")

    def test_clean_dir_ends_with_clean(self):
        assert CLEAN_DIR.endswith("clean")

    def test_split_dir_ends_with_split(self):
        assert SPLIT_DIR.endswith("split")

    def test_db_dir_ends_with_db(self):
        assert DB_DIR.endswith("db")

    def test_dirty_dir_under_data(self):
        assert DIRTY_DIR.startswith(DATA_DIR)

    def test_clean_dir_under_data(self):
        assert CLEAN_DIR.startswith(DATA_DIR)

    def test_split_dir_under_data(self):
        assert SPLIT_DIR.startswith(DATA_DIR)

    def test_db_dir_under_data(self):
        assert DB_DIR.startswith(DATA_DIR)

    def test_data_dir_exists(self):
        assert os.path.isdir(DATA_DIR)

    def test_dirty_dir_exists(self):
        assert os.path.isdir(DIRTY_DIR)

    def test_clean_dir_exists(self):
        assert os.path.isdir(CLEAN_DIR)

    def test_split_dir_exists(self):
        assert os.path.isdir(SPLIT_DIR)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
