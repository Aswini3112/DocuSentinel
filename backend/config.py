"""
DocuSentinel AI - Application Configuration
Works locally and on Render (cloud) via environment variables.
All paths default to a /opt/data directory on Render (persistent disk).
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

_ENV_FILE = Path(__file__).parent / ".env"

# Detect whether we are running on Render
_ON_RENDER = os.environ.get("RENDER") == "true"

# Default data directory — /opt/data on Render (mounted persistent disk),
# <repo_root>/data locally
_DEFAULT_DATA_DIR = "/opt/data" if _ON_RENDER else str(Path(__file__).parent.parent / "data")


class Settings(BaseSettings):
    # App
    app_name: str = "DocuSentinel AI"
    app_version: str = "1.0.0"
    debug: bool = False

    # CORS — add your Vercel URL here or via env var
    # Example: "https://docusentinel.vercel.app,http://localhost:5173"
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    # ── LLM (any OpenAI-compatible API) ───────────────────────────────────
    llm_api_key: str = ""
    llm_model: str = "llama-3.3-70b-versatile"
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 1500
    openai_api_key: str = ""   # legacy alias

    # ── Paths — all overridable via env vars ──────────────────────────────
    upload_dir: str = f"{_DEFAULT_DATA_DIR}/uploads"
    vectorstore_dir: str = f"{_DEFAULT_DATA_DIR}/vectorstore"
    database_url: str = f"sqlite+aiosqlite:///{_DEFAULT_DATA_DIR}/docusentinel.db"

    # ── Processing ────────────────────────────────────────────────────────
    max_file_size_mb: int = 50
    chunk_size: int = 150
    chunk_overlap: int = 20
    top_k_retrieval: int = 8
    similarity_threshold: float = 0.05

    tesseract_cmd: str = ""

    class Config:
        env_file = str(_ENV_FILE)
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def effective_llm_api_key(self) -> str:
        return self.llm_api_key or self.openai_api_key or ""

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def vectorstore_path(self) -> Path:
        p = Path(self.vectorstore_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


@lru_cache()
def get_settings() -> Settings:
    return Settings()
