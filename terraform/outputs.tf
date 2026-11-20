output "environment" {
  description = "Environment derived from the Terraform workspace."
  value       = local.environment
}

output "namespace" {
  description = "Namespace that holds this environment."
  value       = kubernetes_namespace_v1.app.metadata[0].name
}

output "deployment_name" {
  description = "Name of the Kubernetes Deployment created for this environment."
  value       = kubernetes_deployment_v1.app.metadata[0].name
}

output "service_name" {
  description = "Name of the ClusterIP Service in front of the Deployment."
  value       = kubernetes_service_v1.app.metadata[0].name
}

output "try_it" {
  description = "Command to reach this environment from your computer."
  value       = "kubectl port-forward -n ${kubernetes_namespace_v1.app.metadata[0].name} service/${kubernetes_service_v1.app.metadata[0].name} 5001:${var.service_port}"
}
