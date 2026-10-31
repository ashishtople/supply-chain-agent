import os
from pathlib import Path
from pydantic_settings import BaseSettings

# Define root directory paths
ROOT_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "Enterprise Supply Chain Multi-Agent System"
    DEBUG: bool = True
    
    # LLM Settings (Ollama local model on your MacBook Air)
    OLLAMA_MODEL: str = "qwen2.5:7b"
    OLLAMA_TEMPERATURE: float = 0.0
    
    # Database Settings
    DB_PATH: str = str(ROOT_DIR / "supply_chain.db")
    
    # API Server Settings
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Instantiate global settings object (Make sure this line is present!)
settings = Settings()