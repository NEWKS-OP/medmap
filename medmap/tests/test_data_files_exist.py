"""Test that expected data files exist on disk."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config.settings import DIRTY_DIR, CLEAN_DIR, SPLIT_DIR, DB_DIR


class TestDirtyFilesExist:
    """Verify dirty data files are present."""

    def test_dirty_dir_has_files(self):
        files = os.listdir(DIRTY_DIR)
        assert len(files) > 0

    def test_dirty_has_csv_files(self):
        files = [f for f in os.listdir(DIRTY_DIR) if f.endswith('.csv')]
        assert len(files) >= 7

    def test_dirty_has_xlsx_files(self):
        files = [f for f in os.listdir(DIRTY_DIR) if f.endswith('.xlsx')]
        assert len(files) >= 5

    def test_dirty_total_files(self):
        files = [f for f in os.listdir(DIRTY_DIR) if f.endswith(('.csv', '.xlsx'))]
        assert len(files) >= 12


class TestCleanFilesExist:
    """Verify clean reference files are present."""

    def test_clean_dir_has_files(self):
        files = os.listdir(CLEAN_DIR)
        assert len(files) > 0

    def test_clean_has_csv_files(self):
        files = [f for f in os.listdir(CLEAN_DIR) if f.endswith('.csv')]
        assert len(files) >= 9

    def test_clean_has_xlsx_files(self):
        files = [f for f in os.listdir(CLEAN_DIR) if f.endswith('.xlsx')]
        assert len(files) >= 1


class TestSplitFilesExist:
    """Verify split clinic files are present."""

    def test_split_dir_has_files(self):
        files = os.listdir(SPLIT_DIR)
        assert len(files) > 0

    def test_split_has_many_files(self):
        files = [f for f in os.listdir(SPLIT_DIR) if f.endswith(('.csv', '.xlsx', '.pdf'))]
        assert len(files) >= 25

    def test_split_has_clinic_1(self):
        files = [f for f in os.listdir(SPLIT_DIR) if 'clinic_1' in f.lower()]
        assert len(files) >= 1

    def test_split_has_clinic_2(self):
        files = [f for f in os.listdir(SPLIT_DIR) if 'clinic_2' in f.lower()]
        assert len(files) >= 1

    def test_split_has_clinic_3(self):
        files = [f for f in os.listdir(SPLIT_DIR) if 'clinic_3' in f.lower()]
        assert len(files) >= 1

    def test_split_has_clinic_4(self):
        files = [f for f in os.listdir(SPLIT_DIR) if 'clinic_4' in f.lower()]
        assert len(files) >= 1

    def test_split_has_pdf(self):
        files = [f for f in os.listdir(SPLIT_DIR) if f.endswith('.pdf')]
        assert len(files) >= 1

    def test_split_has_xlsx(self):
        files = [f for f in os.listdir(SPLIT_DIR) if f.endswith('.xlsx')]
        assert len(files) >= 1


class TestDBFilesExist:
    """Verify database files are present."""

    def test_medmap_db_exists(self):
        assert os.path.exists(os.path.join(DB_DIR, "medmap.db"))

    def test_create_tables_sql_exists(self):
        assert os.path.exists(os.path.join(DB_DIR, "CreateImportTables.sql"))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
