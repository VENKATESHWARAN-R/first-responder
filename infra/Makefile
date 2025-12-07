.PHONY: setup destroy init plan apply argocd-password port-forward port-forward-grafana port-forward-prometheus clean status build-images

# Default target
.DEFAULT_GOAL := help

# Directories
TERRAFORM_DIR := $(shell pwd)/terraform
SCRIPTS_DIR := $(shell pwd)/scripts

##@ General

help: ## Display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Cluster Lifecycle

setup: ## Full setup - create Kind cluster with ArgoCD and addons
	@chmod +x $(SCRIPTS_DIR)/setup.sh
	@$(SCRIPTS_DIR)/setup.sh

destroy: ## Destroy the Kind cluster and all resources
	@chmod +x $(SCRIPTS_DIR)/destroy.sh
	@$(SCRIPTS_DIR)/destroy.sh

clean: ## Remove all Terraform files (except state)
	@rm -rf $(TERRAFORM_DIR)/.terraform
	@rm -f $(TERRAFORM_DIR)/.terraform.lock.hcl
	@rm -f $(TERRAFORM_DIR)/tfplan
	@echo "Cleaned up Terraform working files"

clean-all: ## Remove ALL Terraform files including state
	@rm -rf $(TERRAFORM_DIR)/.terraform
	@rm -f $(TERRAFORM_DIR)/.terraform.lock.hcl
	@rm -f $(TERRAFORM_DIR)/tfplan
	@rm -f $(TERRAFORM_DIR)/terraform.tfstate*
	@echo "Cleaned up ALL Terraform files"

##@ Terraform Operations

init: ## Initialize Terraform
	@cd $(TERRAFORM_DIR) && terraform init -upgrade

plan: ## Run Terraform plan
	@cd $(TERRAFORM_DIR) && terraform plan

apply: ## Apply Terraform changes
	@cd $(TERRAFORM_DIR) && terraform apply

validate: ## Validate Terraform configuration
	@cd $(TERRAFORM_DIR) && terraform validate

format: ## Format Terraform files
	@cd $(TERRAFORM_DIR) && terraform fmt -recursive

##@ Access

argocd-password: ## Get ArgoCD admin password
	@kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d && echo

port-forward: port-forward-argocd ## Alias for port-forward-argocd

port-forward-argocd: ## Port-forward ArgoCD server (https://localhost:8080)
	@echo "ArgoCD available at https://localhost:8080"
	@echo "Username: admin"
	@echo "Password: $$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d)"
	@kubectl port-forward svc/argocd-server -n argocd 8080:443

port-forward-grafana: ## Port-forward Grafana (http://localhost:3000)
	@echo "Grafana available at http://localhost:3000"
	@echo "Username: admin, Password: admin"
	@kubectl port-forward svc/kube-prometheus-stack-grafana -n monitoring 3000:80

port-forward-prometheus: ## Port-forward Prometheus (http://localhost:9090)
	@echo "Prometheus available at http://localhost:9090"
	@kubectl port-forward svc/kube-prometheus-stack-prometheus -n monitoring 9090:9090

port-forward-load-tester-frontend: ## Port-forward Load Tester Frontend (http://localhost:3001)
	@echo "Load Tester Frontend available at http://localhost:3001"
	@kubectl port-forward svc/local-frontend -n load-tester 3001:3000

port-forward-load-tester-backend: ## Port-forward Load Tester Backend (http://localhost:8000)
	@echo "Load Tester Backend available at http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"
	@kubectl port-forward svc/local-backend -n load-tester 8000:8000

##@ Status

status: ## Show cluster and ArgoCD status
	@echo "=== Kind Clusters ==="
	@kind get clusters 2>/dev/null || echo "No Kind clusters found"
	@echo ""
	@echo "=== Kubernetes Context ==="
	@kubectl config current-context 2>/dev/null || echo "No context set"
	@echo ""
	@echo "=== ArgoCD Applications ==="
	@kubectl get applications -n argocd 2>/dev/null || echo "ArgoCD not installed or not accessible"
	@echo ""
	@echo "=== Cluster Namespaces ==="
	@kubectl get namespaces 2>/dev/null || echo "Cannot connect to cluster"

pods: ## Show all pods in important namespaces
	@echo "=== ArgoCD Pods ==="
	@kubectl get pods -n argocd 2>/dev/null || echo "Namespace not found"
	@echo ""
	@echo "=== cert-manager Pods ==="
	@kubectl get pods -n cert-manager 2>/dev/null || echo "Namespace not found"
	@echo ""
	@echo "=== Monitoring Pods ==="
	@kubectl get pods -n monitoring 2>/dev/null || echo "Namespace not found"
	@echo ""
	@echo "=== Envoy Gateway Pods ==="
	@kubectl get pods -n envoy-gateway-system 2>/dev/null || echo "Namespace not found"

apps: ## Show ArgoCD applications sync status
	@kubectl get applications -n argocd -o custom-columns=NAME:.metadata.name,SYNC:.status.sync.status,HEALTH:.status.health.status 2>/dev/null || echo "ArgoCD not accessible"

##@ Development

sync: ## Force sync all ArgoCD applications
	@echo "Force syncing all applications..."
	@for app in $$(kubectl get applications -n argocd -o jsonpath='{.items[*].metadata.name}' 2>/dev/null); do \
		echo "Syncing $$app..."; \
		kubectl patch application $$app -n argocd --type merge -p '{"operation": {"sync": {}}}' 2>/dev/null || true; \
	done

logs-argocd: ## Show ArgoCD server logs
	@kubectl logs -n argocd -l app.kubernetes.io/name=argocd-server -f --tail=100

build-images: ## Build and load application Docker images into Kind cluster
	@chmod +x $(SCRIPTS_DIR)/build-images.sh
	@$(SCRIPTS_DIR)/build-images.sh
