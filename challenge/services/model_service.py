import os
import pickle
import logging
from typing import Optional
import pandas as pd
from sklearn.model_selection import train_test_split

from ..models.model import DelayModel
from ..config.settings import settings
from ..core.exceptions import ModelTrainingError, ModelNotAvailableError

logger = logging.getLogger(__name__)


class ModelService:
    """
    Service class to handle model training, loading, and persistence.
    """
    
    def __init__(self, model_path: Optional[str] = None, data_path: Optional[str] = None):
        self.model_path = model_path or settings.model_path
        self.data_path = data_path or settings.data_path
        self.model: Optional[DelayModel] = None
        self.is_trained = False
        
    def load_model(self) -> bool:
        """
        Load a pre-trained model from disk.
        
        Returns:
            bool: True if model loaded successfully, False otherwise
        """
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, 'rb') as f:
                    self.model = pickle.load(f)
                self.is_trained = True
                logger.info(f"Model loaded successfully from {self.model_path}")
                return True
            else:
                logger.warning(f"Model file not found at {self.model_path}")
                return False
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            return False
    
    def save_model(self) -> bool:
        """
        Save the trained model to disk.
        
        Returns:
            bool: True if model saved successfully, False otherwise
        """
        try:
            if self.model is None or not self.is_trained:
                logger.error("No trained model to save")
                return False
                
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            
            with open(self.model_path, 'wb') as f:
                pickle.dump(self.model, f)
            logger.info(f"Model saved successfully to {self.model_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving model: {str(e)}")
            return False
    
    def train_model(self) -> bool:
        """
        Train the model with the training data.
        
        Returns:
            bool: True if model trained successfully, False otherwise
        """
        try:
            # Load training data
            if not os.path.exists(self.data_path):
                logger.error(f"Training data not found at {self.data_path}")
                return False
                
            df = pd.read_csv(self.data_path)
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
        Initialize the model by loading from disk or training if necessary.
        
        Returns:
            bool: True if model initialized successfully, False otherwise
        """
        # Try to load existing model first
        if self.load_model():
            return True
        
        # If loading failed, train a new model
        logger.info("No pre-trained model found, training new model...")
        if self.train_model():
            # Save the newly trained model
            self.save_model()
            return True
        
        logger.error("Failed to initialize model")
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
