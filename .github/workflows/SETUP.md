# Configuración de GitHub Actions para Google Cloud Run

## Secrets necesarios

Para que los workflows de CI/CD funcionen correctamente, necesitas configurar los siguientes secrets en tu repositorio de GitHub:

### 1. GCP_PROJECT_ID

- **Descripción**: ID del proyecto de Google Cloud Platform
- **Valor**: Tu PROJECT_ID de GCP (ej: `mi-proyecto-123456`)

### 2. GCP_SA_KEY

- **Descripción**: Clave de la cuenta de servicio de Google Cloud Platform
- **Valor**: JSON completo de la cuenta de servicio

## Cómo configurar los secrets

1. Ve a tu repositorio en GitHub
2. Haz clic en **Settings** → **Secrets and variables** → **Actions**
3. Haz clic en **New repository secret**
4. Agrega cada uno de los secrets mencionados arriba

## Cómo crear la cuenta de servicio

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Selecciona tu proyecto
3. Ve a **IAM & Admin** → **Service Accounts**
4. Haz clic en **Create Service Account**
5. Nombre: `github-actions`
6. Descripción: `Service account for GitHub Actions CI/CD`
7. Asigna los siguientes roles (mínimos recomendados):
   - **Cloud Run Admin** (`roles/run.admin`)
   - **Service Account User** (`roles/iam.serviceAccountUser`)
   - **Artifact Registry Writer** (`roles/artifactregistry.writer`)
   - **Storage Admin** (`roles/storage.admin`) — requerido para compatibilidad con `gcr.io`
8. Haz clic en **Create Key** → **JSON**
9. Descarga el archivo JSON y copia su contenido como `GCP_SA_KEY`

## Habilitar APIs necesarias

Asegúrate de que las siguientes APIs estén habilitadas en tu proyecto:

```bash
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable storage.googleapis.com
```

## Crear bucket de Google Cloud Storage

Para almacenar el modelo entrenado y los datos de entrenamiento, necesitas crear un bucket de Google Cloud Storage:

### 1) Crear el bucket

```bash
# Reemplaza 'flights-bucket-92837465' con el nombre único que prefieras
BUCKET_NAME="flights-bucket-92837465"

gcloud storage buckets create gs://$BUCKET_NAME \
  --project="$PROJECT_ID" \
  --location=us-central1 \
  --uniform-bucket-level-access
```

**Nota**: Los nombres de buckets deben ser globalmente únicos en todo Google Cloud Storage. Elige un nombre único y significativo.

### 2) Crear estructura de carpetas

```bash
# Crear carpeta para modelos
gcloud storage mkdir gs://$BUCKET_NAME/models

# Crear carpeta para datos
gcloud storage mkdir gs://$BUCKET_NAME/data
```

### 3) Subir los datos de entrenamiento

```bash
# Subir tu archivo de datos de entrenamiento
gcloud storage cp /path/to/your/data.csv gs://$BUCKET_NAME/data/data.csv
```

**Nota**: Una vez que tengas el bucket creado y los datos subidos, puedes entrenar el modelo usando el script `train.py`:

```bash
python -m challenge.train \
  --data-path gs://$BUCKET_NAME/data/data.csv \
  --model-path gs://$BUCKET_NAME/models/delay_model.pkl
```

### 4) Otorgar permisos necesarios

Asegúrate de que tu cuenta de servicio tenga permisos para leer/escribir en el bucket:

```bash
# Otorgar Storage Object Admin al servicio de Cloud Run (para leer modelo)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:github-actions@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

# O si prefieres solo permisos de lectura para Cloud Run:
gcloud storage buckets add-iam-policy-binding gs://$BUCKET_NAME \
  --member="serviceAccount:YOUR_CLOUD_RUN_SA@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"
```

### 5) Configurar variables de entorno en Cloud Run

Después del despliegue, configura estas variables de entorno en Cloud Run:

- `MODEL_PATH`: `gs://$BUCKET_NAME/models/delay_model.pkl`
- `DATA_PATH`: `gs://$BUCKET_NAME/data/data.csv`

Esto se puede hacer a través de la consola de GCP o mediante `gcloud`:

```bash
gcloud run services update flight-delay-api \
  --region=us-central1 \
  --set-env-vars="MODEL_PATH=gs://$BUCKET_NAME/models/delay_model.pkl,DATA_PATH=gs://$BUCKET_NAME/data/data.csv"
```

## Actualizar Makefile

Después del primer despliegue, actualiza la línea 26 del Makefile con la URL real de tu servicio:

```makefile
STRESS_URL = https://flight-delay-api-<TU-PROJECT-ID>-uc.a.run.app
```

## Flujo de trabajo

- **CI**: Se ejecuta en cada push y PR a `main` y `develop`.
- **CD**: Se ejecuta en push a `main` y `develop`, y también se puede lanzar manualmente desde la pestaña **Actions** (workflow_dispatch). Despliega automáticamente a Cloud Run.

## Opción A (recomendada): Pre-crear el repositorio de compatibilidad `gcr.io`

En muchos proyectos `gcr.io` está respaldado por Artifact Registry y no se crea automáticamente. Para evitar errores como:

"denied: gcr.io repo does not exist. Creating on push requires the artifactregistry.repositories.createOnPush permission"

pre-crea el repositorio de compatibilidad `gcr.io` una sola vez y otorga los permisos correctos a la cuenta de servicio usada por GitHub Actions.

### 1) Habilitar Artifact Registry (si no lo hiciste antes)

```bash
gcloud services enable artifactregistry.googleapis.com --project "$PROJECT_ID"
```

### 2) Crear el repositorio `gcr.io` en la ubicación correcta

El repositorio de compatibilidad para `gcr.io` debe existir en la ubicación `us`.

```bash
gcloud artifacts repositories create gcr.io \
  --repository-format=docker \
  --location=us \
  --description="Docker repo for legacy gcr.io compatibility" \
  --project "$PROJECT_ID"
```

### 3) Otorgar permisos a la cuenta de servicio de CI/CD

Sustituye `YOUR_SA@YOUR_PROJECT.iam.gserviceaccount.com` por el email de tu cuenta de servicio.

```bash
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:YOUR_SA@YOUR_PROJECT.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:YOUR_SA@YOUR_PROJECT.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:YOUR_SA@YOUR_PROJECT.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:YOUR_SA@YOUR_PROJECT.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
```

### 4) Autenticación correcta en GitHub Actions

El workflow de CD debe autenticar con:

- `google-github-actions/auth@v2` usando `credentials_json: ${{ secrets.GCP_SA_KEY }}`
- `google-github-actions/setup-gcloud@v2` con `project_id`

Además, para publicar en `gcr.io` añade en el workflow:

```bash
gcloud auth configure-docker --quiet
```

Si usas Artifact Registry explícitamente (por ejemplo `us-central1-docker.pkg.dev`), configura el host:

```bash
gcloud auth configure-docker us-central1-docker.pkg.dev --quiet
```

### 5) Nombres de imagen y regiones

- Para `gcr.io`, usa: `gcr.io/$PROJECT_ID/$SERVICE_NAME:$GITHUB_SHA`
- Si decides usar Artifact Registry directamente, usa: `REGION-docker.pkg.dev/$PROJECT_ID/$REPO/$SERVICE_NAME:$GITHUB_SHA` y crea el repositorio en esa `REGION`.
