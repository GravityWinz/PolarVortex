#!/bin/bash
set -e

# Change to script directory, then to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

REGISTRY=ghcr.io/gravitywinz
TAG=prod-$(date +%Y%m%d)
# Build for both Intel (amd64) and Raspberry Pi (arm64) architectures
PLATFORMS=linux/amd64,linux/arm64

# Ensure buildx is available and create a builder instance if needed
if ! docker buildx ls | grep -q "multiarch"; then
  echo "Creating multi-architecture buildx builder..."
  docker buildx create --name multiarch --driver docker-container --use
  docker buildx inspect --bootstrap
else
  echo "Using existing multi-architecture buildx builder..."
  docker buildx use multiarch
fi

echo "Building and pushing multi-architecture images..."
echo "Platforms: $PLATFORMS"
echo "Registry: $REGISTRY"
echo "Tag: $TAG"

# Backend (FastAPI) - Build for both architectures and push with manifest
echo "Building backend for $PLATFORMS..."
docker buildx build \
  --platform "$PLATFORMS" \
  -t $REGISTRY/polarvortex-backend:$TAG \
  -t $REGISTRY/polarvortex-backend:latest \
  -f backend/Dockerfile \
  backend \
  --push

# Frontend (nginx-served build) - Build for both architectures and push with manifest
echo "Building frontend for $PLATFORMS..."
docker buildx build \
  --platform "$PLATFORMS" \
  -t $REGISTRY/polarvortex-frontend:$TAG \
  -t $REGISTRY/polarvortex-frontend:latest \
  -f frontend/Dockerfile \
  frontend \
  --push

echo "Multi-architecture build and push completed successfully!"
echo "Images available at:"
echo "  - $REGISTRY/polarvortex-backend:$TAG"
echo "  - $REGISTRY/polarvortex-backend:latest"
echo "  - $REGISTRY/polarvortex-frontend:$TAG"
echo "  - $REGISTRY/polarvortex-frontend:latest"