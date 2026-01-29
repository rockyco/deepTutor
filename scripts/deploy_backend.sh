#!/bin/bash
set -e

echo "🚀 Deploying DeepTutor Backend to Google Cloud Run..."

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: 'gcloud' CLI is not found."
    echo "Please install Google Cloud SDK: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Project ID (Prompt if not set)
if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
    echo "ℹ️  No GOOGLE_CLOUD_PROJECT set."
    read -p "Enter your Google Cloud Project ID: " GOOGLE_CLOUD_PROJECT
fi

echo "✅ Using Project: $GOOGLE_CLOUD_PROJECT"
gcloud config set project $GOOGLE_CLOUD_PROJECT

# Enable Services
echo "Enable Cloud Run & Build services..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com

# Deploy
echo "🚀 Building and Deploying..."
gcloud run deploy deeptutor-backend \
    --source backend \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --timeout 300 \
    --memory 1Gi \
    --set-env-vars DATABASE_URL="sqlite+aiosqlite:////tmp/tutor.db",SKIP_SEEDING="true"

echo "✅ Backend Deployment Complete!"
