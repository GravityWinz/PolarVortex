REGISTRY=ghcr.io/gravitywinz
TAG=prod-$(date +%Y%m%d)
PLATFORM=linux/arm64  #Build for Raspberry Pi
# PLATFORM=linux/amd64  #Build for intel


# Backend (FastAPI)
docker buildx build \
  --platform "$PLATFORM" \
  -t $REGISTRY/polarvortex-backend:$TAG \
  -f backend/Dockerfile backend \
  -t $REGISTRY/polarvortex-backend:latest \
  --push

# Frontend (nginx-served build)
docker buildx build \
  --platform "$PLATFORM" \
  -t $REGISTRY/polarvortex-frontend:$TAG \
  -f frontend/Dockerfile frontend \
  -t $REGISTRY/polarvortex-frontend:latest \
  --push