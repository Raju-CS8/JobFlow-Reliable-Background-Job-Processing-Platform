"""Configuration for JobFlow."""

from dataclasses import dataclass


@dataclass
class Config:
    """Application configuration."""
    
    # Database
    database_url: str = "postgresql://jobflow:jobflow@localhost:5432/jobflow"
    
    # Job processing
    default_max_attempts: int = 3
    stuck_job_threshold_seconds: int = 300  # 5 minutes
    
    # Logging
    log_level: str = "INFO"


def get_config() -> Config:
    """Get application configuration."""
    return Config()