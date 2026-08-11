"""Configuration management for Filebede bot."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Bot configuration from environment variables."""
    
    # Telegram
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    BOT_API_SERVER: str = os.getenv("BOT_API_SERVER", "http://127.0.0.1:8081")
    
    # Download
    DOWNLOAD_DIR: str = os.getenv("DOWNLOAD_DIR", "downloads")
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "5"))
    CONNECT_TIMEOUT: int = int(os.getenv("CONNECT_TIMEOUT", "30"))
    READ_TIMEOUT: int = int(os.getenv("READ_TIMEOUT", "60"))
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1048576"))  # 1MB
    MAX_DOWNLOAD_SIZE: int = int(os.getenv("MAX_DOWNLOAD_SIZE", "2147483648"))  # 2GB
    
    # Security
    ALLOWED_SCHEMES: list = ["http", "https"]
    MAX_REDIRECTS: int = 10
    
    # Progress
    PROGRESS_UPDATE_INTERVAL: float = 2.0  # seconds


config = Config()
