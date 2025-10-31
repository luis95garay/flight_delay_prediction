import os
from typing import Optional
from pydantic import BaseModel


class Settings(BaseModel):
    """
    Application settings loaded from environment variables.
    """
    
    # API Settings
    app_name: str = "Flight Delay Prediction API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Model Settings
    model_path: str = "./models/delay_model.pkl"
    data_path: str = "./data/data.csv"
    
    # Logging Settings
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # API Settings
    # No versioning prefix needed
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance with default values
settings = Settings(
    app_name="Flight Delay Prediction API",
    app_version="1.0.0",
    debug=False,
    model_path="./models/delay_model.pkl",
    data_path="./data/data.csv",
    log_level="INFO",
    log_format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
