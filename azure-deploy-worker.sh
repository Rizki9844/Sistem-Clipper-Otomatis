#!/bin/bash
# ============================================================
# AutoClipperPro — Deploy Worker to Azure Container Instances
# ============================================================
# Prerequisites:
#   - Azure CLI installed & logged in (az login)
#   - Azure Container Registry created
#   - GitHub Student Pack $100 Azure credit activated
# ============================================================

set -euo pipefail

# ---- Configuration ----
RESOURCE_GROUP="${ACI_RESOURCE_GROUP:-autoclipperpro-rg}"
REGISTRY="${ACI_REGISTRY:-autoclipperpro}"
CONTAINER_NAME="${ACI_CONTAINER_NAME:-autoclipperpro-worker}"
LOCATION="${ACI_LOCATION:-southeastasia}"          # Closest to Indonesia
IMAGE_TAG="${ACI_IMAGE_TAG:-latest}"
CPU="${ACI_CPU:-2}"
MEMORY="${ACI_MEMORY:-4}"                          # GB — Whisper needs ~2GB

echo "🚀 AutoClipperPro Worker Deployment to Azure Container Instances"
echo "================================================================"

# ---- Step 1: Create Resource Group ----
echo ""
echo "📦 Step 1: Ensuring resource group exists..."
az group create \
    --name "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --output none 2>/dev/null || true
echo "   ✅ Resource group: $RESOURCE_GROUP ($LOCATION)"

# ---- Step 2: Create Container Registry ----
echo ""
echo "🏗️ Step 2: Ensuring container registry exists..."
az acr create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$REGISTRY" \
    --sku Basic \
    --admin-enabled true \
    --output none 2>/dev/null || true

ACR_SERVER=$(az acr show --name "$REGISTRY" --query loginServer -o tsv)
ACR_USERNAME=$(az acr credential show --name "$REGISTRY" --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name "$REGISTRY" --query "passwords[0].value" -o tsv)
echo "   ✅ Registry: $ACR_SERVER"

# ---- Step 3: Build & Push Image ----
echo ""
echo "🐳 Step 3: Building and pushing worker image..."
az acr build \
    --registry "$REGISTRY" \
    --image "autoclipperpro-worker:$IMAGE_TAG" \
    --file Dockerfile.worker \
    .
echo "   ✅ Image pushed: $ACR_SERVER/autoclipperpro-worker:$IMAGE_TAG"

# ---- Step 4: Deploy Container Instance ----
echo ""
echo "🚀 Step 4: Deploying container instance..."

# Read env vars from .env file if exists
ENV_VARS=""
if [ -f ".env" ]; then
    echo "   📄 Loading environment variables from .env..."
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ "$key" =~ ^#.*$ ]] && continue
        [[ -z "$key" ]] && continue
        # Remove quotes from value
        value=$(echo "$value" | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
        ENV_VARS="$ENV_VARS $key=$value"
    done < .env
fi

az container create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$CONTAINER_NAME" \
    --image "$ACR_SERVER/autoclipperpro-worker:$IMAGE_TAG" \
    --registry-login-server "$ACR_SERVER" \
    --registry-username "$ACR_USERNAME" \
    --registry-password "$ACR_PASSWORD" \
    --cpu "$CPU" \
    --memory "$MEMORY" \
    --restart-policy Always \
    --environment-variables $ENV_VARS \
    --output none

echo "   ✅ Container deployed: $CONTAINER_NAME"

# ---- Step 5: Verify ----
echo ""
echo "📊 Step 5: Checking container status..."
STATUS=$(az container show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$CONTAINER_NAME" \
    --query "instanceView.state" -o tsv)
echo "   Status: $STATUS"

echo ""
echo "🔍 View logs:"
echo "   az container logs --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME --follow"
echo ""
echo "🎉 Deployment complete!"
