"""Application configuration settings."""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "11+ Deep Tutor"
    debug: bool = True
    google_cloud_project: str | None = "booming-order-424821-m1"

    # Database
    # Default to local path for dev. Dockerfile overrides this via ENV.
    database_url: str = "sqlite+aiosqlite:////home/amd/UTS/deepTutor/backend/data/tutor.db"

    # Paths
    base_dir: Path = Path(__file__).parent.parent
    data_dir: Path = base_dir / "data"
    questions_dir: Path = data_dir / "questions"
    materials_dir: Path = data_dir / "materials"

    # AI providers (optional - for explanation generation)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None

    # Practice settings
    default_session_length: int = 10  # questions per session
    hint_penalty: float = 0.5  # score reduction per hint used

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
