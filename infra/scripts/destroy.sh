#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Kind Cluster with ArgoCD - Destroy Script                 ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Navigate to script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"
TERRAFORM_DIR="$INFRA_DIR/terraform"

# Get cluster name (default if terraform not initialized)
CLUSTER_NAME="first-responder"
if [ -f "$TERRAFORM_DIR/terraform.tfstate" ]; then
    cd "$TERRAFORM_DIR"
    CLUSTER_NAME=$(terraform output -raw cluster_name 2>/dev/null || echo "first-responder")
fi

echo -e "${YELLOW}This will destroy the Kind cluster and all resources.${NC}"
echo -e "${YELLOW}Cluster: ${CLUSTER_NAME}${NC}"
echo ""

# Confirm destruction
read -p "Are you sure you want to continue? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Destruction cancelled.${NC}"
    exit 0
fi

echo ""
echo -e "${YELLOW}Destroying infrastructure...${NC}"
echo ""

cd "$TERRAFORM_DIR"

# Try Terraform destroy first
if [ -f "terraform.tfstate" ]; then
    echo -e "${BLUE}[1/3] Running Terraform destroy...${NC}"
    terraform destroy -auto-approve || true
else
    echo -e "${YELLOW}[1/3] No Terraform state found, skipping...${NC}"
fi

# Ensure Kind cluster is deleted (backup)
echo ""
echo -e "${BLUE}[2/3] Ensuring Kind cluster is deleted...${NC}"
if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
    kind delete cluster --name "${CLUSTER_NAME}"
    echo -e "${GREEN}✓ Kind cluster '${CLUSTER_NAME}' deleted${NC}"
else
    echo -e "${YELLOW}Kind cluster '${CLUSTER_NAME}' not found or already deleted${NC}"
fi

# Clean up kubeconfig context
echo ""
echo -e "${BLUE}[3/3] Cleaning up kubeconfig...${NC}"
kubectl config delete-context "kind-${CLUSTER_NAME}" 2>/dev/null || true
kubectl config delete-cluster "kind-${CLUSTER_NAME}" 2>/dev/null || true

# Clean up terraform files
echo ""
echo -e "${YELLOW}Cleaning up Terraform files...${NC}"
rm -f "$TERRAFORM_DIR/tfplan"
rm -f "$TERRAFORM_DIR/.terraform.lock.hcl"
rm -rf "$TERRAFORM_DIR/.terraform"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Destruction Complete!                                     ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Note: terraform.tfstate has been preserved for reference.${NC}"
echo -e "${YELLOW}      Delete it manually if you want a completely clean slate.${NC}"
echo ""
