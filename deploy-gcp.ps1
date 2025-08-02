#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Deploy Texas School Psychology Assistant to Google Cloud Platform
    
.DESCRIPTION
    This script automates the deployment process to GCP Cloud Run
    including building, pushing, and deploying the application.
#>

param(
    [string]$ProjectId = "texas-school-psychology",
    [string]$Region = "us-central1",
    [string]$ServiceName = "texas-school-psychology-assistant",
    [switch]$SkipBuild = $false
)

Write-Host "🚀 TEXAS SCHOOL PSYCHOLOGY ASSISTANT - GCP DEPLOYMENT" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green

# Check if gcloud is installed
try {
    $gcloudVersion = gcloud --version 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "gcloud not found"
    }
    Write-Host "✅ Google Cloud SDK found" -ForegroundColor Green
} catch {
    Write-Host "❌ Google Cloud SDK not found. Please install it first:" -ForegroundColor Red
    Write-Host "   https://cloud.google.com/sdk/docs/install" -ForegroundColor Yellow
    exit 1
}

# Check if user is authenticated
try {
    $auth = gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>$null
    if (-not $auth) {
        Write-Host "🔐 Please authenticate with Google Cloud:" -ForegroundColor Yellow
        gcloud auth login
    } else {
        Write-Host "✅ Authenticated as: $auth" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Authentication failed" -ForegroundColor Red
    exit 1
}

# Set project
Write-Host "📋 Setting project to: $ProjectId" -ForegroundColor Blue
gcloud config set project $ProjectId

# Enable required APIs
Write-Host "🔧 Enabling required APIs..." -ForegroundColor Blue
$apis = @(
    "run.googleapis.com",
    "cloudbuild.googleapis.com", 
    "containerregistry.googleapis.com",
    "storage.googleapis.com"
)

foreach ($api in $apis) {
    Write-Host "   Enabling $api..." -ForegroundColor Gray
    gcloud services enable $api --quiet
}

# Configure Docker for GCP
Write-Host "🐳 Configuring Docker for GCP..." -ForegroundColor Blue
gcloud auth configure-docker --quiet

# Create GCS bucket for embeddings
Write-Host "Creating Google Cloud Storage bucket for embeddings..." -ForegroundColor Yellow
try {
    $bucketName = "texas-school-psychology-embeddings"
    gsutil mb gs://$bucketName 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ GCS bucket created: gs://$bucketName" -ForegroundColor Green
    } else {
        Write-Host "ℹ️  GCS bucket already exists or creation failed" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  GCS bucket creation failed: $_" -ForegroundColor Yellow
}

# Build and push Docker image
Write-Host "Building and pushing Docker image..." -ForegroundColor Yellow
try {
    docker build -t gcr.io/$ProjectId/$ServiceName:latest .
    if ($LASTEXITCODE -ne 0) {
        throw "Docker build failed"
    }
    
    docker push gcr.io/$ProjectId/$ServiceName:latest
    if ($LASTEXITCODE -ne 0) {
        throw "Docker push failed"
    }
    
    Write-Host "✅ Docker image built and pushed successfully" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker build/push failed: $_" -ForegroundColor Red
    exit 1
}

# Deploy to Cloud Run
Write-Host "🚀 Deploying to Cloud Run..." -ForegroundColor Blue
gcloud run deploy $ServiceName `
    --image gcr.io/$ProjectId/$ServiceName:latest `
    --region $Region `
    --platform managed `
    --allow-unauthenticated `
    --memory 2Gi `
    --cpu 2 `
    --max-instances 10 `
    --set-env-vars "OPENAI_API_KEY=$env:OPENAI_API_KEY" `
    --set-env-vars "ADMIN_PASSWORD=$env:ADMIN_PASSWORD" `
    --set-env-vars "GCP_PROJECT_ID=$ProjectId" `
    --set-env-vars "GCS_EMBEDDINGS_BUCKET=texas-school-psychology-embeddings" `
    --set-env-vars "GCS_USE_STORAGE=true"

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Deployment failed" -ForegroundColor Red
    exit 1
}

# Get service URL
Write-Host "🔍 Getting service URL..." -ForegroundColor Blue
$serviceUrl = gcloud run services describe $ServiceName --region $Region --format="value(status.url)"

Write-Host "============================================================" -ForegroundColor Green
Write-Host "🎉 DEPLOYMENT SUCCESSFUL!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "🌐 Service URL: $serviceUrl" -ForegroundColor Cyan
Write-Host "📊 Monitor: https://console.cloud.google.com/run/detail/$Region/$ServiceName" -ForegroundColor Cyan
Write-Host "🔧 Logs: gcloud logs tail --service=$ServiceName --region=$Region" -ForegroundColor Cyan
Write-Host "☁️  GCS Bucket: gs://texas-school-psychology-embeddings" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Green