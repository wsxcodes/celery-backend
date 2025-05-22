import os

from dotenv import load_dotenv

load_dotenv()

CODE_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.dirname(CODE_DIR)

API_V1_STR = "/api/v1"
API_URL = os.getenv("API_URL", "http://localhost:8000")

DEVELOPMENT = os.getenv("DEVELOPMENT", None)

SECRET_KEY = os.getenv("SECRET_KEY", "this-is-not-a-secret-key-make-it-secret")

origins_str = os.getenv("CORS_ORIGINS", "")
if origins_str:
    CORS_ORIGINS = origins_str.split(",")
else:
    CORS_ORIGINS = []

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "your-azure-openai-api-key")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "your-azure-openai-endpoint")
OPENAI_API_VERSION = os.getenv("OPENAI_API_VERSION", "2025-01-01-preview")

DB_PATH = os.getenv("DB_PATH", os.path.join(ROOT_DIR, "data", "file_records.db"))

BASE_UPLOAD_DIR = os.getenv("BASE_UPLOAD_DIR", "MISSING-BASE_UPLOAD_DIR")

RABBITMQ_USER = os.getenv("RABBITMQ_USER", "eternyiq")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "eternyiq")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "eternyiq-rabbitmq")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "eternyiq")
RABBITMQ_PORT = os.getenv("RABBITMQ_PORT", 5672)
RABBITMQ_BROKER = f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}/{RABBITMQ_VHOST}"

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "eternyiq")
