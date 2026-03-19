import os
from dotenv import load_dotenv

load_dotenv()

DB_TYPE = os.getenv("DB_TYPE", "sqlite")
DB_PATH = os.getenv("DB_PATH", "data/db/medmap.db")
MSSQL_CONNECTION_STRING = os.getenv("MSSQL_CONNECTION_STRING", "")

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "5000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
NLP_MODEL = os.getenv("NLP_MODEL", "en_core_web_sm")
PID_PREFIX_STRATEGY = os.getenv("PID_PREFIX_STRATEGY", "true").lower() == "true"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DIRTY_DIR = os.path.join(DATA_DIR, "dirty")
CLEAN_DIR = os.path.join(DATA_DIR, "clean")
SPLIT_DIR = os.path.join(DATA_DIR, "split")
DB_DIR = os.path.join(DATA_DIR, "db")

IID_SID_ITEM_PATH = os.path.join(DATA_DIR, "IID-SID-ITEM.csv")
SQL_SCHEMA_PATH = os.path.join(DB_DIR, "CreateImportTables.sql")
