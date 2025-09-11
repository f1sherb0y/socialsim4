import os

STORAGE_PATH = os.environ.get("STORAGE_PATH", "./storage")
API_PREFIX = os.environ.get("API_PREFIX", "")
LISTEN_ADDRESS = os.environ.get("LISTEN_ADDRESS", "0.0.0.0")
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./socialsim.db")
