"""Application configuration loaded from environment variables and an optional .env file."""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import os

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")


def _resolve_path(value: str, default: str) -> Path:
    path = Path(value or default).expanduser()
    return path if path.is_absolute() else (ROOT_DIR / path).resolve()


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str
    local_storage_path: Path
    sqlite_database_path: Path
    log_level: str
    backend_host: str
    backend_port: int
    cors_origins: tuple[str, ...]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    storage_path = _resolve_path(os.getenv("LOCAL_STORAGE_PATH", ""), "data/documents")
    database_path = _resolve_path(os.getenv("SQLITE_DATABASE_PATH", ""), "data/loan_verification.db")
    origins = tuple(
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:3001,http://localhost:5173",
        ).split(",")
        if origin.strip()
    )
    return Settings(
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip(),
        local_storage_path=storage_path,
        sqlite_database_path=database_path,
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        backend_host=os.getenv("BACKEND_HOST", "127.0.0.1"),
        backend_port=int(os.getenv("BACKEND_PORT", "8000")),
        cors_origins=origins,
    )
