# Infrastructure as Code with Terraform (SRE Academy exercise 15).
# Creates a separate "staging" copy of the app in its own namespace, fully declared in code:
# namespace, ConfigMap, Deployment (with probes and a rolling update strategy) and Service.
#
#   cd terraform
#   terraform init
#   terraform apply              # or: terraform workspace new dev && terraform apply
#   terraform destroy

terraform {
  required_version = ">= 1.5"
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 3.5"
    }
  }
}

provider "kubernetes" {
  config_path    = var.kubeconfig_path
  config_context = var.kube_context
}

locals {
  # Each Terraform workspace gets its own namespace: staging (default workspace), dev, qa...
  environment = terraform.workspace == "default" ? "staging" : terraform.workspace
  namespace   = "${var.app_name}-${local.environment}"
  labels = {
    app         = var.app_name
    environment = local.environment
    managed-by  = "terraform"
  }
}

resource "kubernetes_namespace_v1" "app" {
  metadata {
    name   = local.namespace
    labels = local.labels
  }
}

resource "kubernetes_config_map_v1" "app" {
  metadata {
    name      = "${var.app_name}-config"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
    labels    = local.labels
  }
  data = {
    APP_VERSION       = var.app_version
    OTEL_SERVICE_NAME = "${var.app_name}-${local.environment}"
  }
}

resource "kubernetes_deployment_v1" "app" {
  metadata {
    name      = var.app_name
    namespace = kubernetes_namespace_v1.app.metadata[0].name
    labels    = local.labels
  }

  spec {
    replicas = var.replicas

    strategy {
      type = "RollingUpdate"
      rolling_update {
        max_surge       = "1"
        max_unavailable = "0"
      }
    }

    selector {
      match_labels = { app = var.app_name }
    }

    template {
      metadata {
        labels = local.labels
        annotations = {
          "prometheus.io/scrape" = "true"
          "prometheus.io/port"   = tostring(var.container_port)
          "prometheus.io/path"   = "/metrics"
        }
      }

      spec {
        container {
          name              = "app"
          image             = var.image
          image_pull_policy = var.image_pull_policy

          port {
            container_port = var.container_port
          }

          env_from {
            config_map_ref {
              name = kubernetes_config_map_v1.app.metadata[0].name
            }
          }

          resources {
            requests = { cpu = "50m", memory = "96Mi" }
            limits   = { cpu = "300m", memory = "256Mi" }
          }

          readiness_probe {
            http_get {
              path = "/"
              port = var.container_port
            }
            initial_delay_seconds = 3
            period_seconds        = 5
          }

          liveness_probe {
            http_get {
              path = "/"
              port = var.container_port
            }
            initial_delay_seconds = 10
            period_seconds        = 10
          }
        }
      }
    }
  }

  wait_for_rollout = true
}

resource "kubernetes_service_v1" "app" {
  metadata {
    name      = "${var.app_name}-service"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
    labels    = local.labels
  }
  spec {
    selector = { app = var.app_name }
    port {
      port        = var.service_port
      target_port = var.container_port
    }
    type = "ClusterIP"
  }
}
