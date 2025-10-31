# Challenge Decisions Explanation

This document explains the architectural decisions, design patterns, and implementation choices made throughout the development of the Flight Delay Prediction API challenge.

---

## Repository Structure

The repository follows a modular, layered architecture that promotes separation of concerns, maintainability, and scalability:

```
challenge/
├── api.py                    # Main FastAPI application entry point
├── config/                   # Configuration management
│   └── settings.py          # Application settings (Pydantic-based)
├── core/                     # Core functionality and infrastructure
│   ├── exceptions.py        # Custom exception classes
│   └── logging.py           # Logging configuration
├── models/                   # ML model implementation
│   ├── model.py             # DelayModel class with preprocessing and training
│   └── schemas.py           # Pydantic schemas for API request/response validation
├── services/                 # Business logic layer
│   ├── model_service.py     # Model training, loading, and persistence
│   └── prediction_service.py # Prediction orchestration
└── utils/                    # Utility functions
    └── helpers.py           # Helper functions (get_min_diff, feature selection)
```

### Design Principles

- **Separation of Concerns**: Each module has a single responsibility (Business logic, model management, configuration)
- **Dependency Injection**: Services are injected via FastAPI's dependency system, promoting testability and loose coupling
- **Service Layer Pattern**: Business logic is encapsulated in service classes, keeping API endpoints thin
- **Configuration Management**: Centralized settings using Pydantic, allowing environment-based configuration
- **Error Handling**: Custom exceptions provide clear error boundaries and meaningful error messages

---

## Part I: Model Training

### Model Selection Decision

After analyzing the exploration notebook, the **XGBClassifier** was selected as the optimal model based on the following criteria:

- **Best F1 Score**: The XGBClassifier achieved superior F1 score performance among the models tested
- **Hyperparameters**:
  - `random_state=1`: Ensures reproducibility
  - `learning_rate=0.01`: Lower learning rate for better generalization and stability
  - `scale_pos_weight=scale`: Automatically calculated based on class imbalance (ratio of negative to positive samples)

### Class Imbalance Handling

The dataset exhibits significant class imbalance. To address this:

- The `scale_pos_weight` parameter is dynamically calculated as `n_y0/n_y1` (ratio of non-delayed to delayed flights)
- This ensures the model gives appropriate weight to the minority class (delayed flights) during training

### Future Improvements

While the current model performs well, potential enhancements include:

- Grid search or Bayesian optimization for hyperparameter tuning
- Testing alternative algorithms (Random Forest, LightGBM, CatBoost)
- Feature engineering improvements (time-based features, airline-specific trends)
- Consideration of Recall optimization for business-critical delay detection
- Cross-validation for more robust model evaluation

---

## Part II: FastAPI Development

### Architecture Decisions

The API follows a clean, modular architecture with the following components:

#### 1. **API Layer** (`api.py`)

- Thin controllers that handle HTTP requests/responses
- Dependency injection for service layer access
- CORS middleware for cross-origin requests
- Global exception handling with appropriate HTTP status codes

#### 2. **Service Layer** (`services/`)

- **ModelService**: Handles model lifecycle (training, loading, saving)
- **PredictionService**: Orchestrates prediction workflow

#### 3. **Data Validation** (`models/schemas.py`)

- Pydantic models for request/response validation
- Field-level validation (allowed values for OPERA, TIPOVUELO, MES)
- Clear error messages for invalid inputs
- Example values in schema documentation

#### 4. **Configuration Management** (`config/settings.py`)

- Environment-based configuration
- Pydantic settings with default values
- Supports `.env` files for local development
- Centralized configuration for easy environment-specific adjustments

#### 5. **Error Handling** (`core/exceptions.py`)

- Custom exception hierarchy:
  - `ModelNotAvailableError`: Model not loaded or trained
  - `ModelTrainingError`: Training process failures
  - `PredictionError`: Prediction execution failures
  - `ValidationError`: Input validation failures
- Proper HTTP status code mapping (400, 500, 503)

#### 6. **Logging** (`core/logging.py`)

- Structured logging configuration
- Appropriate log levels (INFO, ERROR, WARNING)
- Logs model initialization, predictions, and errors for debugging

### API Endpoints

1. **`GET /`**: Root endpoint with API information
2. **`GET /health`**: Health check endpoint for monitoring and load balancers
3. **`POST /predict`**: Main prediction endpoint
   - Accepts JSON with list of flights
   - Returns predictions (0 or 1 for each flight)
   - Includes comprehensive error handling

---

## Part III: GCP Cloud Run Deployment

### Docker Configuration

The `Dockerfile` implements production best practices:

- **Multi-stage optimization**: Uses Python 3.10-slim for smaller image size
- **Security**: Runs as non-root user
- **Health checks**: Built-in health check for container orchestration
- **Layer caching**: Optimized layer ordering for better build cache utilization
- **System dependencies**: Installs only necessary build tools

### Deployment Configuration

The Cloud Run service is configured with:

- **Memory**: 1Gi (sufficient for ML model inference)
- **CPU**: 1 vCPU
- **Scaling**: 0-10 instances (cost optimization with scale-to-zero)
- **Concurrency**: 80 requests per instance
- **Timeout**: 300 seconds
- **Port**: 8000 (standardized)
- **Authentication**: Unauthenticated access (configurable for production)

### Deployment Process

1. **Build**: Docker image built with Git commit SHA as tag
2. **Push**: Image pushed to Google Container Registry (GCR)
3. **Deploy**: Cloud Run service updated with new image
4. **Verify**: Health check and stress tests run post-deployment
5. **Tagging**: Latest tag maintained for easy rollback

---

## Part IV: CI/CD Implementation

### Continuous Integration (CI) Pipeline

**Location**: `.github/workflows/ci.yml`

**Triggers**:

- Push to `main` or `develop` branches
- Pull requests targeting `main` or `develop`

**Pipeline Steps**:

1. **Test Job**:

   - Python 3.10 setup
   - Dependency caching for faster builds
   - Installs production, development, and test dependencies
   - Runs model tests (`make model-test`)
   - Runs API tests (`make api-test`)
   - Uploads coverage reports as artifacts

2. **Build Job** (runs after successful tests):
   - Docker Buildx setup for multi-platform builds
   - Builds production Docker image
   - Tests Docker image by running container and checking health endpoint
   - Triggers Continuous Delivery workflow on success

### Continuous Delivery (CD) Pipeline

**Location**: `.github/workflows/cd.yml`

**Triggers**:

- Repository dispatch event (triggered by CI pipeline)
- Manual workflow dispatch

**Pipeline Steps**:

1. **Authentication**:

   - Google Cloud authentication using service account key
   - Cloud SDK setup for GCP CLI commands

2. **Build and Push**:

   - Builds Docker image tagged with Git SHA
   - Pushes to Google Container Registry (GCR)
   - Tags image as `latest` for easy reference

3. **Deploy**:

   - Deploys to Cloud Run using the new image
   - Configures service settings (memory, CPU, scaling, etc.)
   - Updates service without downtime (blue-green deployment)

4. **Verification**:

   - Retrieves deployed service URL
   - Waits for service to be healthy (retry logic)
   - Runs health check endpoint validation

5. **Stress Testing**:

   - Executes Locust stress test (100 users, 60 seconds)
   - Generates HTML report
   - Uploads stress test results as artifacts

6. **Notifications**:
   - Posts deployment status to PR comments (if triggered from PR)

---
