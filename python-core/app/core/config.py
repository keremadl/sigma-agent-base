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

    # Tools
    tavily_api_key: str | None = None

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

# Create directories on import
settings.memory_dir.mkdir(parents=True, exist_ok=True)
settings.app_data_dir.mkdir(parents=True, exist_ok=True)

# Model tiers for hybrid mode system
MODEL_TIERS = {
    "pro": "gemini/gemini-3-pro-preview",  # Newest Gemini 3 Pro (Nov 2025)
    "auto": "gemini/gemini-3-flash-preview",  # Newest Gemini 3 Flash (Dec 2025)
    "fast": "gemini/gemini-3-flash-preview",  # Flash is fast enough
}

# Thinking settings per mode
THINKING_ENABLED = {
    "pro": True,  # Always use thinking
    "auto": "smart",  # Use thinking only for complex queries
    "fast": False,  # Never use thinking
}
