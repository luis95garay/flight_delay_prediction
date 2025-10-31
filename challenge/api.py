"""
Main FastAPI application.
"""
import logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Annotated

from .config.settings import settings
from .core.logging import setup_logging
from .core.exceptions import PredictionError, ValidationError
from .models.schemas import FlightsRequest
from .services.model_service import ModelService
from .services.prediction_service import PredictionService

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    description="API for predicting flight delays using machine learning"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances (singletons)
_model_service: ModelService = None
_prediction_service: PredictionService = None


def get_model_service() -> ModelService:
    """
    Get the model service instance (singleton).
    
    Returns:
        ModelService: The model service instance
    """
    global _model_service
    if _model_service is None:
        _model_service = ModelService()
        # Initialize the model
        if not _model_service.initialize_model():
            logger.error("Failed to initialize model service")
            raise RuntimeError("Failed to initialize model service")
    return _model_service


def get_prediction_service(
    model_service: Annotated[ModelService, Depends(get_model_service)]
) -> PredictionService:
    """
    Get the prediction service instance (singleton).
    
    Args:
        model_service: The model service dependency
        
    Returns:
        PredictionService: The prediction service instance
    """
    global _prediction_service
    if _prediction_service is None:
        _prediction_service = PredictionService(model_service)
    return _prediction_service


@app.get("/health", status_code=200)
async def get_health() -> dict:
    """
    Health check endpoint.
    
    Returns:
        dict: Health status
    """
    return {
        "status": "OK",
        "service": "Flight Delay Prediction API"
    }


@app.post("/predict", status_code=200)
async def post_predict(
    request: FlightsRequest,
    prediction_service: Annotated[PredictionService, Depends(get_prediction_service)]
) -> dict:
    """
    Predict flight delays.
    
    Args:
        request: Flight data for prediction
        prediction_service: Injected prediction service
        
    Returns:
        dict: Prediction results
        
    Raises:
        HTTPException: If prediction fails
    """
    try:
        # Check if model is available
        if not prediction_service.is_model_available():
            logger.error("Model not available for prediction")
            raise HTTPException(
                status_code=503, 
                detail="Model not available. Please try again later."
            )
        
        # Make predictions
        predictions = prediction_service.predict_delays(request)
        
        return {"predict": predictions}
        
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid input data")
    except PredictionError as e:
        logger.error(f"Prediction error: {str(e)}")
        raise HTTPException(status_code=500, detail="Prediction failed")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "message": "Flight Delay Prediction API",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health"
    }


# Startup event
@app.on_event("startup")
async def startup_event():
    """
    Application startup event.
    """
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info("Application startup completed")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event.
    """
    logger.info("Application shutdown")