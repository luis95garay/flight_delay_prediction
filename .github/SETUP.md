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
