"""Tests for config/settings.py — environment configuration."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.settings import (
    DB_TYPE, DB_PATH, CHUNK_SIZE, LOG_LEVEL, NLP_MODEL,
    PID_PREFIX_STRATEGY, DATA_DIR, DIRTY_DIR, CLEAN_DIR,
    SPLIT_DIR, DB_DIR, IID_SID_ITEM_PATH, SQL_SCHEMA_PATH,
)


class TestDefaultValues:
    def test_db_type_default(self):
        assert DB_TYPE == "sqlite"

    def test_db_path_default(self):
        assert "medmap.db" in DB_PATH

    def test_chunk_size_is_int(self):
        assert isinstance(CHUNK_SIZE, int)
        assert CHUNK_SIZE > 0

    def test_log_level_default(self):
        assert LOG_LEVEL == "INFO"

    def test_nlp_model_default(self):
        assert NLP_MODEL == "en_core_web_sm"

    def test_pid_prefix_strategy_is_bool(self):
        assert isinstance(PID_PREFIX_STRATEGY, bool)


class TestDirectoryPaths:
    def test_data_dir_exists(self):
        assert os.path.isdir(DATA_DIR)

    def test_dirty_dir_exists(self):
        assert os.path.isdir(DIRTY_DIR)

    def test_clean_dir_exists(self):
        assert os.path.isdir(CLEAN_DIR)

    def test_split_dir_exists(self):
        assert os.path.isdir(SPLIT_DIR)

    def test_db_dir_exists(self):
        assert os.path.isdir(DB_DIR)


class TestFilePaths:
    def test_iid_sid_item_path_exists(self):
        assert os.path.isfile(IID_SID_ITEM_PATH)

    def test_sql_schema_path_exists(self):
        assert os.path.isfile(SQL_SCHEMA_PATH)

    def test_iid_sid_item_is_csv(self):
        assert IID_SID_ITEM_PATH.endswith(".csv")

    def test_sql_schema_is_sql(self):
        assert SQL_SCHEMA_PATH.endswith(".sql")


class TestPathConsistency:
    def test_dirty_dir_under_data(self):
        assert DIRTY_DIR.startswith(DATA_DIR)

    def test_clean_dir_under_data(self):
        assert CLEAN_DIR.startswith(DATA_DIR)

    def test_split_dir_under_data(self):
        assert SPLIT_DIR.startswith(DATA_DIR)

    def test_db_dir_under_data(self):
        assert DB_DIR.startswith(DATA_DIR)

    def test_iid_under_data(self):
        assert IID_SID_ITEM_PATH.startswith(DATA_DIR)

    def test_sql_schema_under_db(self):
        assert SQL_SCHEMA_PATH.startswith(DB_DIR)
