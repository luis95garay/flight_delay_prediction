import os
from typing import Optional
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """
    Application settings loaded from environment variables.
    Environment variables take precedence over defaults.
    """
    
    # API Settings
    app_name: str = Field(default="Flight Delay Prediction API", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Model Settings - defaults to GCS bucket paths, can be overridden via environment variables
    # Replace 'flights-bucket' with your actual bucket name
    model_path: str = Field(
        default="gs://flights-bucket-92837465/models/delay_model.pkl",
        env="MODEL_PATH"
    )
    data_path: str = Field(
        default="gs://flights-bucket-92837465/data/data.csv",
        env="DATA_PATH"
    )
    
    # Logging Settings
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance - automatically reads from environment variables
settings = Settings()
