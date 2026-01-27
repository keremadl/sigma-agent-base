from pydantic_settings import BaseSettings
from pathlib import Path
import os


class Settings(BaseSettings):
    # Application directories
    app_data_dir: Path = Path(os.getenv("APPDATA", ".")) / "SigmaAgent"
    memory_dir: Path = app_data_dir / "memory"
    db_path: Path = app_data_dir / "conversations.db"

    # Server settings
    host: str = "127.0.0.1"
    port: int = 8765  # Avoid common ports like 8000

    # Model settings
    default_model: str = "gpt-4o-mini"
    router_model: str = "gpt-4o-mini"  # Fast & cheap for classification

    # Embedding settings
    embedding_model: str = "all-MiniLM-L6-v2"  # Local, no API cost

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

# Create directories on import
settings.memory_dir.mkdir(parents=True, exist_ok=True)
settings.app_data_dir.mkdir(parents=True, exist_ok=True)

