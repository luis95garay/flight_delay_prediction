"""
Custom exceptions for the application.
"""


class ModelNotAvailableError(Exception):
    """Raised when the model is not available for prediction."""
    pass


class ModelTrainingError(Exception):
    """Raised when model training fails."""
    pass


class PredictionError(Exception):
    """Raised when prediction fails."""
    pass


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass
