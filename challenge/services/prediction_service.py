import logging
import pandas as pd
from typing import List

from ..models.schemas import FlightsRequest
from ..core.exceptions import PredictionError, ValidationError
from .model_service import ModelService

logger = logging.getLogger(__name__)


class PredictionService:
    """
    Service class to handle flight delay predictions.
    """
    
    def __init__(self, model_service: ModelService):
        self.model_service = model_service
    
    def predict_delays(self, request: FlightsRequest) -> List[int]:
        """
        Predict delays for a list of flights.
        
        Args:
            request: FlightsRequest containing flight data
            
        Returns:
            List[int]: List of predictions (0 or 1)
            
        Raises:
            PredictionError: If prediction fails
            ValidationError: If input validation fails
        """
        try:
            # Convert list of dicts to DataFrame
            data = pd.DataFrame([flight.model_dump() for flight in request.flights])
            
            # Get the trained model
            model = self.model_service.get_model()
            
            # Preprocess the input data
            features = model.preprocess(data)
            
            # Make predictions
            predictions = model.predict(features)
            
            logger.info(f"Successfully predicted delays for {len(predictions)} flights")
            return predictions
            
        except ValidationError as e:
            logger.error(f"Validation error in prediction: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error during prediction: {str(e)}")
            raise PredictionError(f"Failed to make predictions: {str(e)}")
    
    def is_model_available(self) -> bool:
        """
        Check if the model is available for predictions.
        
        Returns:
            bool: True if model is available, False otherwise
        """
        return self.model_service.is_trained
