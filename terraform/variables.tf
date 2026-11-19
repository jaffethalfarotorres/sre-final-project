variable "kubeconfig_path" {
  description = "Path to the kubeconfig that points at Minikube."
  type        = string
  default     = "~/.kube/config"
}

variable "kube_context" {
  description = "kubeconfig context to use."
  type        = string
  default     = "minikube"
}

variable "app_name" {
  description = "Name used for the Deployment, Service and namespace prefix."
  type        = string
  default     = "sre-metrics-app"
}

variable "app_version" {
  description = "Version string exposed to the app through the ConfigMap."
  type        = string
  default     = "1.0.0"
}

variable "image" {
  description = "Container image. The deploy script builds sre-metrics-app:1.0.0 inside Minikube."
  type        = string
  default     = "sre-metrics-app:1.0.0"
}

variable "image_pull_policy" {
  description = "Never = use the image built inside Minikube; IfNotPresent/Always for a registry image."
  type        = string
  default     = "Never"
}

variable "replicas" {
  description = "Number of pods."
  type        = number
  default     = 2

  validation {
    condition     = var.replicas >= 1 && var.replicas <= 5
    error_message = "replicas must be between 1 and 5 on a laptop cluster."
  }
}

variable "container_port" {
  description = "Port the app listens on."
  type        = number
  default     = 5000
}

variable "service_port" {
  description = "Port of the ClusterIP Service."
  type        = number
  default     = 5000
}
