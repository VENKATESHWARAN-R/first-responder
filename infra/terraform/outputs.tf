output "cluster_name" {
  description = "Name of the Kind cluster"
  value       = kind_cluster.this.name
}

output "cluster_endpoint" {
  description = "Kubernetes API endpoint"
  value       = kind_cluster.this.endpoint
}

output "kubeconfig" {
  description = "Kubeconfig for the cluster"
  value       = kind_cluster.this.kubeconfig
  sensitive   = true
}

output "argocd_namespace" {
  description = "ArgoCD namespace"
  value       = var.argocd_namespace
}

output "argocd_server_url" {
  description = "ArgoCD server URL (via port-forward)"
  value       = "https://localhost:8080"
}

output "argocd_admin_password_command" {
  description = "Command to get ArgoCD admin password"
  value       = "kubectl -n ${var.argocd_namespace} get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d"
}

output "port_forward_command" {
  description = "Command to port-forward ArgoCD server"
  value       = "kubectl port-forward svc/argocd-server -n ${var.argocd_namespace} 8080:443"
}
