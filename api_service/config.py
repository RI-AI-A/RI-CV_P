"""API service configuration."""
from pydantic_settings import BaseSettings
import os


class APIConfig(BaseSettings):
    """API service configuration."""
    
    # Database
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://retail_user:retail_pass@postgres:5432/retail_intel"
    )
    
    # Server
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    
    # CORS
    cors_origins: list = ["*"]
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_format: str = os.getenv("LOG_FORMAT", "json")
    
    # ETL
    etl_time_window_minutes: int = int(os.getenv("ETL_TIME_WINDOW_MINUTES", "60"))
    etl_historical_baseline_days: int = int(os.getenv("ETL_HISTORICAL_BASELINE_DAYS", "30"))
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Allow extra environment variables


# Global config instance
api_config = APIConfig()
