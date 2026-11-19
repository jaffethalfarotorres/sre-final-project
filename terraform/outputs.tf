output "environment" {
  description = "Environment derived from the Terraform workspace."
  value       = local.environment
}

output "namespace" {
  description = "Namespace that holds this environment."
  value       = kubernetes_namespace.app.metadata[0].name
}

output "deployment_name" {
  value = kubernetes_deployment.app.metadata[0].name
}

output "service_name" {
  value = kubernetes_service.app.metadata[0].name
}

output "try_it" {
  description = "Command to reach this environment from your computer."
  value       = "kubectl port-forward -n ${kubernetes_namespace.app.metadata[0].name} service/${kubernetes_service.app.metadata[0].name} 5001:${var.service_port}"
}
