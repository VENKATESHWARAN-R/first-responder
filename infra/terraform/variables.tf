variable "cluster_name" {
  description = "Name of the Kind cluster"
  type        = string
  default     = "first-responder"
}

variable "kubernetes_version" {
  description = "Kubernetes version to use (Kind node image tag)"
  type        = string
  default     = "v1.31.0"
}

variable "worker_nodes" {
  description = "Number of worker nodes"
  type        = number
  default     = 2
}

variable "argocd_chart_version" {
  description = "ArgoCD Helm chart version"
  type        = string
  default     = "7.7.5"
}

variable "git_repo_url" {
  description = "Git repository URL for ArgoCD to sync from"
  type        = string
  default     = "https://github.com/VENKATESHWARAN-R/first-responder.git"
}

variable "git_target_revision" {
  description = "Git branch, tag, or commit to sync"
  type        = string
  default     = "master"
}

variable "git_path" {
  description = "Path within the Git repository for cluster addons"
  type        = string
  default     = "infra/argocd/cluster-addons"
}

variable "argocd_namespace" {
  description = "Namespace for ArgoCD installation"
  type        = string
  default     = "argocd"
}

variable "enable_cluster_addons" {
  description = "Whether to deploy cluster addons via App of Apps"
  type        = bool
  default     = true
}

variable "enable_applications" {
  description = "Whether to deploy user applications via App of Apps"
  type        = bool
  default     = true
}

variable "git_applications_path" {
  description = "Path within the Git repository for user applications"
  type        = string
  default     = "infra/argocd/applications"
}

