import os
import pickle
import logging
from io import BytesIO
from typing import Optional, Tuple
import pandas as pd
from sklearn.model_selection import train_test_split

from ..models.model import DelayModel
from ..config.settings import settings
from ..core.exceptions import ModelTrainingError, ModelNotAvailableError

logger = logging.getLogger(__name__)

# Try to import Google Cloud Storage, but make it optional
try:
    from google.cloud import storage
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False
    storage = None


class ModelService:
    """
    Service class to handle model training, loading, and persistence.
    Supports both local file system and Google Cloud Storage (GCS).
    """
    
    def __init__(self, model_path: Optional[str] = None, data_path: Optional[str] = None):
        self.model_path = model_path or settings.model_path
        self.data_path = data_path or settings.data_path
        self.model: Optional[DelayModel] = None
        self.is_trained = False
    
    def _is_gcs_path(self, path: str) -> bool:
        """
        Check if a path is a Google Cloud Storage path.
        
        Args:
            path: Path to check
            
        Returns:
            bool: True if path is a GCS path (starts with gs://)
        """
        return path.startswith("gs://")
    
    def _parse_gcs_path(self, gcs_path: str) -> Tuple[str, str]:
        """
        Parse a GCS path into bucket name and blob name.
        
        Args:
            gcs_path: GCS path in format gs://bucket/path/to/file
            
        Returns:
            tuple: (bucket_name, blob_name)
        """
        if not self._is_gcs_path(gcs_path):
            raise ValueError(f"Not a GCS path: {gcs_path}")
        
        # Remove gs:// prefix
        path_without_prefix = gcs_path[5:]  # Remove "gs://"
        
        # Split into bucket and blob
        parts = path_without_prefix.split("/", 1)
        bucket_name = parts[0]
        blob_name = parts[1] if len(parts) > 1 else ""
        
        return bucket_name, blob_name
        
    def load_model(self) -> bool:
        """
        Load a pre-trained model from disk or Google Cloud Storage.
        Automatically detects if path is local (file system) or GCS (gs://).
        
        Returns:
            bool: True if model loaded successfully, False otherwise
        """
        try:
            if self._is_gcs_path(self.model_path):
                return self._load_from_gcs()
            else:
                return self._load_from_local()
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            return False
    
    def _load_from_local(self) -> bool:
        """
        Load model from local file system.
        
        Returns:
            bool: True if model loaded successfully, False otherwise
        """
        if os.path.exists(self.model_path):
            with open(self.model_path, 'rb') as f:
                self.model = pickle.load(f)
            self.is_trained = True
            logger.info(f"Model loaded successfully from local path: {self.model_path}")
            return True
        else:
            logger.warning(f"Model file not found at {self.model_path}")
            return False
    
    def _load_from_gcs(self) -> bool:
        """
        Load model from Google Cloud Storage.
        
        Returns:
            bool: True if model loaded successfully, False otherwise
        """
        if not GCS_AVAILABLE:
            logger.error("Google Cloud Storage library not available. Install with: pip install google-cloud-storage")
            return False
        
        try:
            bucket_name, blob_name = self._parse_gcs_path(self.model_path)
            logger.info(f"Parsed GCS path - Bucket: {bucket_name}, Blob: {blob_name}")
            
            # Check for credentials
            creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if creds_path:
                logger.info(f"Using credentials from: {creds_path}")
                if not os.path.exists(creds_path):
                    logger.error(f"Credentials file not found at: {creds_path}")
                    return False
            else:
                logger.info("No GOOGLE_APPLICATION_CREDENTIALS set, will try Application Default Credentials")
            
            # Initialize GCS client
            # On Cloud Run, this automatically uses the service account credentials
            # For local dev, uses GOOGLE_APPLICATION_CREDENTIALS env var or ADC
            try:
                client = storage.Client()
                logger.info("GCS client initialized successfully")
            except Exception as auth_error:
                logger.error(f"Failed to initialize GCS client. Authentication error: {str(auth_error)}")
                logger.error(f"Error type: {type(auth_error).__name__}")
                logger.error("On Cloud Run, ensure the service account has Storage Object Viewer role.")
                logger.error("For Docker, ensure GOOGLE_APPLICATION_CREDENTIALS points to a valid service account key file.")
                logger.error("For local dev, run: gcloud auth application-default login")
                return False
            
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            
            # Check if blob exists
            logger.info(f"Checking if model exists in GCS: {self.model_path}")
            if not blob.exists():
                logger.warning(f"Model file not found in GCS: {self.model_path}")
                logger.warning("Please verify the bucket name and path are correct.")
                return False
            
            # Download and load model
            logger.info(f"Downloading model from GCS: {self.model_path}")
            logger.info(f"Model size: {blob.size} bytes")
            model_bytes = blob.download_as_bytes()
            self.model = pickle.loads(model_bytes)
            self.is_trained = True
            logger.info(f"Model loaded successfully from GCS: {self.model_path}")
            return True
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error loading model from GCS: {error_msg}")
            
            # Provide helpful error messages for common issues
            if "403" in error_msg or "permission" in error_msg.lower() or "access denied" in error_msg.lower():
                logger.error("Permission denied. Ensure the Cloud Run service account has:")
                logger.error("  - roles/storage.objectViewer role on the bucket, or")
                logger.error("  - Storage Object Viewer permission")
            elif "404" in error_msg or "not found" in error_msg.lower():
                logger.error("Bucket or file not found. Verify:")
                logger.error(f"  - Bucket exists: gsutil ls gs://{bucket_name}")
                logger.error(f"  - File path is correct: {blob_name}")
            elif "credentials" in error_msg.lower() or "authentication" in error_msg.lower():
                logger.error("Authentication failed. On Cloud Run, ensure service account is configured.")
            
            return False
    
    def save_model(self) -> bool:
        """
        Save the trained model to disk or Google Cloud Storage.
        Automatically detects if path is local (file system) or GCS (gs://).
        
        Returns:
            bool: True if model saved successfully, False otherwise
        """
        try:
            if self.model is None or not self.is_trained:
                logger.error("No trained model to save")
                return False
            
            if self._is_gcs_path(self.model_path):
                return self._save_to_gcs()
            else:
                return self._save_to_local()
        except Exception as e:
            logger.error(f"Error saving model: {str(e)}")
            return False
    
    def _save_to_local(self) -> bool:
        """
        Save model to local file system.
        
        Returns:
            bool: True if model saved successfully, False otherwise
        """
        # Create directory if it doesn't exist (only if path contains a directory)
        dir_path = os.path.dirname(self.model_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        with open(self.model_path, 'wb') as f:
            pickle.dump(self.model, f)
        logger.info(f"Model saved successfully to local path: {self.model_path}")
        return True
    
    def _save_to_gcs(self) -> bool:
        """
        Save model to Google Cloud Storage.
        
        Returns:
            bool: True if model saved successfully, False otherwise
        """
        if not GCS_AVAILABLE:
            logger.error("Google Cloud Storage library not available. Install with: pip install google-cloud-storage")
            return False
        
        try:
            bucket_name, blob_name = self._parse_gcs_path(self.model_path)
            
            # Initialize GCS client
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            
            # Serialize model to bytes
            model_bytes = pickle.dumps(self.model)
            
            # Upload to GCS
            logger.info(f"Uploading model to GCS: {self.model_path}")
            blob.upload_from_string(model_bytes, content_type='application/octet-stream')
            logger.info(f"Model saved successfully to GCS: {self.model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving model to GCS: {str(e)}")
            return False
    
    def _load_data_from_local(self) -> pd.DataFrame:
        """
        Load training data from local file system.
        
        Returns:
            pd.DataFrame: Loaded data, or None if failed
        """
        if not os.path.exists(self.data_path):
            logger.error(f"Training data not found at {self.data_path}")
            return None
        try:
            df = pd.read_csv(self.data_path)
            logger.info(f"Loaded training data from local path: {self.data_path}")
            return df
        except Exception as e:
            logger.error(f"Error loading data from local path: {str(e)}")
            return None
    
    def _load_data_from_gcs(self) -> pd.DataFrame:
        """
        Load training data from Google Cloud Storage.
        
        Returns:
            pd.DataFrame: Loaded data, or None if failed
        """
        if not GCS_AVAILABLE:
            logger.error("Google Cloud Storage library not available. Install with: pip install google-cloud-storage")
            return None
        
        try:
            bucket_name, blob_name = self._parse_gcs_path(self.data_path)
            
            # Initialize GCS client
            try:
                client = storage.Client()
            except Exception as auth_error:
                logger.error(f"Failed to initialize GCS client. Authentication error: {str(auth_error)}")
                logger.error("Run: gcloud auth application-default login")
                return None
            
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            
            # Check if blob exists
            if not blob.exists():
                logger.error(f"Training data not found in GCS: {self.data_path}")
                return None
            
            # Download data
            logger.info(f"Downloading training data from GCS: {self.data_path}")
            data_bytes = blob.download_as_bytes()
            
            # Read CSV from bytes
            df = pd.read_csv(BytesIO(data_bytes))
            logger.info(f"Loaded training data from GCS: {self.data_path}")
            return df
            
        except Exception as e:
            logger.error(f"Error loading data from GCS: {str(e)}")
            return None
    
    def train_model(self) -> bool:
        """
        Train the model with the training data.
        Supports loading data from local file system or Google Cloud Storage.
        
        Returns:
            bool: True if model trained successfully, False otherwise
        """
        try:
            # Load training data (supports both local and GCS)
            if self._is_gcs_path(self.data_path):
                df = self._load_data_from_gcs()
            else:
                df = self._load_data_from_local()
            
            if df is None:
                return False
                
            logger.info(f"Loaded training data with {len(df)} rows")
            
            # Initialize model
            self.model = DelayModel()
            
            # Preprocess data
            features, target = self.model.preprocess(
                data=df,
                target_column="delay"
            )
            
            # Split data
            x_train, _, y_train, _ = train_test_split(
                features, target, 
                test_size=0.33, 
                random_state=42
            )
            
            # Train model
            self.model.fit(features=x_train, target=y_train)
            self.is_trained = True
            
            logger.info("Model trained successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            raise ModelTrainingError(f"Failed to train model: {str(e)}")
    
    def initialize_model(self) -> bool:
        """
        Initialize the model by loading a pre-trained model from disk.
        
        Note: This method only loads pre-trained models. Use challenge.train to train
        and save models.
        
        Returns:
            bool: True if model initialized successfully, False otherwise
        """
        # Load existing model
        if self.load_model():
            return True
        
        logger.error(f"Failed to load pre-trained model from {self.model_path}")
        logger.error("Please run 'python -m challenge.train' or 'make train' to train and save a model before starting the API")
        return False
    
    def get_model(self) -> DelayModel:
        """
        Get the trained model.
        
        Returns:
            DelayModel: The trained model
            
        Raises:
            ModelNotAvailableError: If model is not trained or not available
        """
        if not self.is_trained or self.model is None:
            raise ModelNotAvailableError("Model not trained or not available")
        return self.model
