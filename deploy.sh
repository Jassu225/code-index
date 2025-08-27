#!/bin/bash

# Deployment script for Serverless Code Index System on Google Cloud Run
# This script sets up all necessary GCP services and deploys the application

set -e

# Configuration
PROJECT_ID=${1:-$(gcloud config get-value project)}
REGION=${2:-us-central1}
SERVICE_NAME="code-index-system"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🚀 Deploying Serverless Code Index System to GCP"
echo "Project ID: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service Name: ${SERVICE_NAME}"

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI is not installed. Please install it first."
    exit 1
fi

if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Not authenticated with gcloud. Please run 'gcloud auth login' first."
    exit 1
fi

# Set the project
echo "📋 Setting GCP project..."
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo "🔌 Enabling required GCP APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    firestore.googleapis.com \
    cloudresourcemanager.googleapis.com

# Create Firestore database if it doesn't exist
echo "🗄️ Setting up Firestore database..."
gcloud firestore databases create --region=${REGION} --project=${PROJECT_ID} || echo "Firestore database already exists"

# Create Cloud Run Jobs service account
echo "📋 Creating Cloud Run Jobs service account..."
gcloud iam service-accounts create ${SERVICE_NAME}-jobs \
    --display-name="Code Index System Cloud Run Jobs Service Account" \
    --description="Service account for Cloud Run Jobs processing" || echo "Service account already exists"

# Build and push Docker image
echo "🐳 Building and pushing Docker image..."
gcloud builds submit --tag ${IMAGE_NAME} .

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --concurrency 80 \
    --max-instances 10 \
    --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID},GCP_REGION=${REGION}" \
    --set-env-vars="FIRESTORE_COLLECTION_PREFIX=code_index" \
    --set-env-vars="CLOUD_RUN_JOBS_LOCATION=${REGION}" \
    --set-env-vars="CLOUD_RUN_JOBS_TIMEOUT=86400" \
    --set-env-vars="CLOUD_RUN_JOBS_CPU=2" \
    --set-env-vars="CLOUD_RUN_JOBS_MEMORY=4Gi"

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format="value(status.url)")

echo "✅ Deployment completed successfully!"
echo "🌐 Service URL: ${SERVICE_URL}"
echo "📚 API Documentation: ${SERVICE_URL}/docs"
echo "💚 Health Check: ${SERVICE_URL}/health"

# Grant necessary permissions for Cloud Run Jobs
echo "🔐 Granting necessary permissions..."
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_NAME}-jobs@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/datastore.user"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_NAME}-jobs@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/run.invoker"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_NAME}-jobs@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/cloudbuild.builds.builder"

echo "🎉 Setup complete! Your Serverless Code Index System is now running on Google Cloud Run."
echo ""
echo "Next steps:"
echo "1. Set up your environment variables in the Cloud Run service"
echo "2. Configure authentication (service account key or workload identity)"
echo "3. Test the API endpoints"
echo "4. Monitor logs: gcloud logging tail --project=${PROJECT_ID}"
