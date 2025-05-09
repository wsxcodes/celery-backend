import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

CODE_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.dirname(CODE_DIR)

API_V1_STR = "/api/v1"

DEVELOPMENT = os.getenv("DEVELOPMENT", None)

SECRET_KEY = os.getenv("SECRET_KEY", "this-is-not-a-secret-key-make-it-secret")

origins_str = os.getenv("CORS_ORIGINS", "")
if origins_str:
    CORS_ORIGINS = origins_str.split(",")
else:
    CORS_ORIGINS = []

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "MISSING-OPENAI_API_KEY")

DB_PATH = os.getenv("DB_PATH", os.path.join(ROOT_DIR, "data", "file_records.db"))
