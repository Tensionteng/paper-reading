from pathlib import Path
from pydantic_settings import BaseSettings

# Locate .env at project root (arxiv-paper-web/.env)
# regardless of where uvicorn is started from
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    app_name: str = "ArXiv Paper Reader"
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'backend' / 'data' / 'papers.db'}"
    # Moonshot AI (Kimi) API
    moonshot_api_key: str = ""
    moonshot_base_url: str = "https://api.moonshot.cn/v1"
    moonshot_model: str = "kimi-k2.5"  # Latest model: kimi-k2.5 (256k context)
    # Paths (absolute, based on project root)
    data_dir: str = str(PROJECT_ROOT / "backend" / "data")
    papers_dir: str = str(PROJECT_ROOT / "backend" / "data" / "papers")
    images_dir: str = str(PROJECT_ROOT / "backend" / "data" / "images")
    latex_dir: str = str(PROJECT_ROOT / "backend" / "data" / "latex")
    # Processing
    max_workers: int = 2

    class Config:
        env_file = str(ENV_FILE)
        env_file_encoding = "utf-8"


settings = Settings()
