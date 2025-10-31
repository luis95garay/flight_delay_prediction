"""
Script to train the flight delay prediction model.

This script loads training data, trains the model, and saves it to disk or Google Cloud Storage.
The trained model can then be loaded by the API service.

Usage:
    # Save to local file system (default)
    python -m challenge.train
    
    # Save to local file with custom path
    python -m challenge.train --model-path ./my_models/delay_model.pkl
    
    # Save to Google Cloud Storage bucket
    python -m challenge.train --model-path gs://your-bucket-name/models/delay_model.pkl
    
    # Use environment variable
    export MODEL_PATH=gs://your-bucket-name/models/delay_model.pkl
    python -m challenge.train
"""
import argparse
import logging
import os
import sys
from pathlib import Path

# Add the project root to Python path (parent of challenge folder)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from challenge.services.model_service import ModelService
from challenge.config.settings import settings
from challenge.core.logging import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


def parse_arguments():
    """
    Parse command-line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Train the flight delay prediction model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Save to local file (default)
  python -m challenge.train
  
  # Save to GCS bucket
  python -m challenge.train --model-path gs://my-bucket/models/delay_model.pkl
  
  # Save to local custom path
  python -m challenge.train --model-path ./output/delay_model.pkl
        """
    )
    
    parser.add_argument(
        "--model-path",
        type=str,
        default=None,
        help="Path where to save the trained model. Can be local (./models/delay_model.pkl) "
             "or GCS (gs://bucket-name/models/delay_model.pkl). "
             "Defaults to MODEL_PATH environment variable or settings.model_path"
    )
    
    parser.add_argument(
        "--data-path",
        type=str,
        default=None,
        help="Path to training data CSV file. "
             "Defaults to DATA_PATH environment variable or settings.data_path"
    )
    
    return parser.parse_args()


def validate_gcs_path(path: str) -> bool:
    """
    Validate GCS path format.
    
    Args:
        path: Path to validate
        
    Returns:
        bool: True if valid GCS path format, False otherwise
    """
    if not path.startswith("gs://"):
        return True  # Not a GCS path, assume valid (will be validated by filesystem later)
    
    # Check format: gs://bucket/path/to/file
    parts = path[5:].split("/", 1)  # Remove 'gs://' prefix
    if len(parts) < 2 or not parts[0] or not parts[1]:
        logger.error(f"Invalid GCS path format: {path}")
        logger.error("Expected format: gs://bucket-name/path/to/file.pkl")
        return False
    
    return True


def train_model(model_path: str = None, data_path: str = None):
    """
    Train the flight delay prediction model and save it.
    
    Args:
        model_path: Path where to save the model (local or GCS). 
                   If None, uses MODEL_PATH env var or settings default.
        data_path: Path to training data CSV. 
                  If None, uses DATA_PATH env var or settings default.
    
    Returns:
        bool: True if training succeeded, False otherwise
    """
    try:
        # Determine model path priority: argument > env var > settings
        if model_path is None:
            model_path = os.getenv("MODEL_PATH", settings.model_path)
        
        # Determine data path priority: argument > env var > settings
        if data_path is None:
            data_path = os.getenv("DATA_PATH", settings.data_path)
        
        # Validate GCS path format if it's a GCS path
        if model_path.startswith("gs://"):
            if not validate_gcs_path(model_path):
                return False
            
            logger.info("=" * 60)
            logger.info("GCS BUCKET MODE ENABLED")
            logger.info("=" * 60)
            logger.info("Make sure you have:")
            logger.info("  1. Google Cloud SDK installed and configured")
            logger.info("  2. Authentication set up (gcloud auth application-default login)")
            logger.info("  3. Appropriate permissions on the bucket")
            logger.info("=" * 60)
        
        logger.info("Starting model training process")
        logger.info(f"Data path: {data_path}")
        logger.info(f"Model will be saved to: {model_path}")
        
        # Initialize model service with custom paths
        model_service = ModelService(model_path=model_path, data_path=data_path)
        
        # Train the model
        logger.info("Training model...")
        if not model_service.train_model():
            logger.error("Failed to train model")
            return False
        
        # Save the trained model
        logger.info("Saving trained model...")
        if not model_service.save_model():
            logger.error("Failed to save model")
            return False
        
        logger.info("=" * 60)
        logger.info("Model training completed successfully!")
        logger.info(f"Model saved to: {model_path}")
        
        if model_path.startswith("gs://"):
            logger.info("=" * 60)
            logger.info("To use this model in your API, set:")
            logger.info(f"  export MODEL_PATH={model_path}")
            logger.info("or configure it in your Cloud Run environment variables")
            logger.info("=" * 60)
        else:
            logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"Error during model training: {str(e)}", exc_info=True)
        return False


if __name__ == "__main__":
    args = parse_arguments()
    success = train_model(
        model_path=args.model_path,
        data_path=args.data_path
    )
    sys.exit(0 if success else 1)

