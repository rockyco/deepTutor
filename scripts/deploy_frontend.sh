#!/bin/bash
set -e

# Default to current project if not set
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"$(gcloud config get-value project)"}

if [ -z "$PROJECT_ID" ]; then
    echo "❌ No Google Cloud Project ID found. Please set GOOGLE_CLOUD_PROJECT."
    exit 1
fi

echo "🚀 Deploying DeepTutor Frontend to Google Cloud Run..."
echo "✅ Using Project: $PROJECT_ID"
echo "ℹ️  Backend URL: $NEXT_PUBLIC_API_URL"

if [ -z "$NEXT_PUBLIC_API_URL" ]; then
    echo "❌ NEXT_PUBLIC_API_URL is not set. Using default (localhost) which WON'T work in cloud."
    echo "export NEXT_PUBLIC_API_URL=<your-backend-url> before running this script."
    exit 1
fi

# Build Frontend
echo "📦 Building Frontend..."
cd frontend
npm install
npm run build
cd ..

# Deploy
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy deeptutor-frontend \
    --source frontend/ \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --project $PROJECT_ID \
    --port 8080

echo "✅ Frontend Deployed Successfully!"
