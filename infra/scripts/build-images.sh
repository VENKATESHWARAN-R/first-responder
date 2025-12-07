#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Building application Docker images for Kind cluster...${NC}"
echo ""

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
APP_DIR="$PROJECT_ROOT/../application"

echo -e "${YELLOW}[1/2] Building backend image...${NC}"
cd "$APP_DIR/backend"
docker build -t backend:test .
echo -e "${GREEN}✓ Backend image built${NC}"
echo ""

echo -e "${YELLOW}[2/2] Building frontend image...${NC}"
cd "$APP_DIR/frontend/my-app"
docker build -t frontend:test .
echo -e "${GREEN}✓ Frontend image built${NC}"
echo ""

echo -e "${YELLOW}Loading images into Kind cluster...${NC}"
CLUSTER_NAME="${KIND_CLUSTER_NAME:-first-responder}"

kind load docker-image backend:test --name "$CLUSTER_NAME"
echo -e "${GREEN}✓ Backend image loaded into Kind${NC}"

kind load docker-image frontend:test --name "$CLUSTER_NAME"
echo -e "${GREEN}✓ Frontend image loaded into Kind${NC}"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Images built and loaded successfully!                    ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Images:${NC}"
echo -e "  - backend:test"
echo -e "  - frontend:test"
echo ""
echo -e "${YELLOW}Note: Backend URL is configured via ConfigMap at runtime.${NC}"
echo -e "${YELLOW}      Edit the ConfigMap to change the backend URL without rebuilding.${NC}"
echo ""
