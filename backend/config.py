"""
DocuSentinel AI - Application Configuration
Supports any OpenAI-compatible LLM provider: OpenAI, Groq, Together, Ollama, etc.
"""

from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

_ENV_FILE = Path(__file__).parent / ".env"


class Settings(BaseSettings):
    # App
    app_name: str = "DocuSentinel AI"
    app_version: str = "1.0.0"
    debug: bool = False
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    # ── LLM (OpenAI-compatible) ────────────────────────────────────────────
    # Set LLM_API_KEY to enable real AI answers.
    # Leave blank to run in evidence-only mode (no LLM, shows NOT_CONFIGURED).
    llm_api_key: str = ""
    llm_model: str = "llama-3.3-70b-versatile"          # Groq default; use gpt-4o-mini for OpenAI
    llm_base_url: str = "https://api.groq.com/openai/v1" # Groq; leave blank for OpenAI default
    llm_temperature: float = 0.1
    llm_max_tokens: int = 1500

    # Legacy alias — maps OPENAI_API_KEY → llm_api_key if set
    openai_api_key: str = ""

    # ── Paths ──────────────────────────────────────────────────────────────
    upload_dir: str = str(Path(__file__).parent.parent / "data" / "uploads")
    vectorstore_dir: str = str(Path(__file__).parent.parent / "data" / "vectorstore")
    database_url: str = (
        f"sqlite+aiosqlite:///{Path(__file__).parent.parent / 'data' / 'docusentinel.db'}"
    )

    # ── Processing ─────────────────────────────────────────────────────────
    max_file_size_mb: int = 50
    chunk_size: int = 150       # words per chunk — small enough for demo docs to get many chunks
    chunk_overlap: int = 20
    top_k_retrieval: int = 8
    similarity_threshold: float = 0.05  # low threshold — TF-IDF scores are naturally lower

    tesseract_cmd: str = ""

    class Config:
        env_file = str(_ENV_FILE)
        env_file_encoding = "utf-8"
        extra = "ignore"

    # ── Derived properties ──────────────────────────────────────────────────

    @property
    def effective_llm_api_key(self) -> str:
        """Returns the first non-empty key from llm_api_key or legacy openai_api_key."""
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
