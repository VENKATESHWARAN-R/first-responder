#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Kind Cluster with ArgoCD - Setup Script                   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Navigate to script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"
TERRAFORM_DIR="$INFRA_DIR/terraform"

# Function to check if a command exists
check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo -e "${RED}✗ $1 is not installed${NC}"
        return 1
    else
        echo -e "${GREEN}✓ $1 is installed${NC}"
        return 0
    fi
}

# Function to wait for pods in a namespace
wait_for_pods() {
    local namespace=$1
    local timeout=${2:-300}
    echo -e "${YELLOW}Waiting for pods in namespace '$namespace' to be ready...${NC}"
    
    for i in $(seq 1 $timeout); do
        if kubectl get pods -n "$namespace" 2>/dev/null | grep -v "Running\|Completed\|NAME" | grep -q .; then
            sleep 2
        else
            if kubectl get pods -n "$namespace" 2>/dev/null | grep -q "Running"; then
                echo -e "${GREEN}✓ All pods in '$namespace' are ready${NC}"
                return 0
            fi
        fi
        
        if [ $((i % 30)) -eq 0 ]; then
            echo -e "${YELLOW}Still waiting... ($i seconds)${NC}"
        fi
    done
    
    echo -e "${YELLOW}⚠ Timeout waiting for pods in '$namespace'. Some pods may still be starting.${NC}"
    kubectl get pods -n "$namespace"
    return 0
}

echo -e "${YELLOW}Checking prerequisites...${NC}"
echo ""

# Check prerequisites
PREREQS_OK=true

check_command "docker" || PREREQS_OK=false
check_command "terraform" || PREREQS_OK=false
check_command "kubectl" || PREREQS_OK=false
check_command "kind" || PREREQS_OK=false

echo ""

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}✗ Docker is not running. Please start Docker first.${NC}"
    PREREQS_OK=false
else
    echo -e "${GREEN}✓ Docker is running${NC}"
fi

if [ "$PREREQS_OK" = false ]; then
    echo ""
    echo -e "${RED}Please install missing prerequisites and try again.${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Setting up Kind cluster with ArgoCD...${NC}"
echo ""

# Navigate to terraform directory
cd "$TERRAFORM_DIR"

# Initialize Terraform
echo -e "${BLUE}[1/4] Initializing Terraform...${NC}"
terraform init -upgrade

echo ""
echo -e "${BLUE}[2/4] Planning infrastructure...${NC}"
terraform plan -out=tfplan

echo ""
echo -e "${BLUE}[3/4] Applying infrastructure...${NC}"
terraform apply tfplan

echo ""
echo -e "${BLUE}[4/4] Configuring kubectl context...${NC}"

# Get cluster name from terraform output
CLUSTER_NAME=$(terraform output -raw cluster_name 2>/dev/null || echo "first-responder")

# Set kubectl context
kubectl config use-context "kind-${CLUSTER_NAME}"

echo ""
echo -e "${YELLOW}Waiting for ArgoCD to be ready...${NC}"
wait_for_pods "argocd" 180

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Setup Complete!                                           ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Get ArgoCD password
echo -e "${BLUE}ArgoCD Access:${NC}"
echo -e "  URL: ${YELLOW}https://localhost:8080${NC} (after port-forward)"
echo -e "  Username: ${YELLOW}admin${NC}"
echo -e "  Password: ${YELLOW}$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' 2>/dev/null | base64 -d || echo "Run: kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d")${NC}"
echo ""
echo -e "${BLUE}Port-forward commands:${NC}"
echo -e "  ArgoCD:    ${YELLOW}kubectl port-forward svc/argocd-server -n argocd 8080:443${NC}"
echo -e "  Grafana:   ${YELLOW}kubectl port-forward svc/kube-prometheus-stack-grafana -n monitoring 3000:80${NC}"
echo -e "  Prometheus:${YELLOW}kubectl port-forward svc/kube-prometheus-stack-prometheus -n monitoring 9090:9090${NC}"
echo ""
echo -e "${BLUE}Or use NodePorts:${NC}"
echo -e "  ArgoCD:     ${YELLOW}http://localhost:30080${NC}"
echo -e "  Grafana:    ${YELLOW}http://localhost:30030${NC} (admin/admin)"
echo -e "  Prometheus: ${YELLOW}http://localhost:30090${NC}"
echo ""
echo -e "${YELLOW}Note: Cluster addons will be synced by ArgoCD automatically.${NC}"
echo -e "${YELLOW}      Check ArgoCD UI for sync status.${NC}"
echo ""
