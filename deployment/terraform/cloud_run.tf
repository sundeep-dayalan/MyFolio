# Artifact Registry for container images
resource "google_artifact_registry_repository" "repo" {
  depends_on    = [time_sleep.wait_for_apis]
  project       = var.project_id
  location      = var.region
  repository_id = "${var.app_name}-repo"
  description   = "Container repository for ${var.app_name}"
  format        = "DOCKER"

  labels = {
    app = var.app_name
  }
}

# Service account for Cloud Run
resource "google_service_account" "cloudrun_sa" {
  depends_on   = [time_sleep.wait_for_apis]
  project      = var.project_id
  account_id   = "${var.app_name}-cloudrun-sa"
  display_name = "Cloud Run Service Account for ${var.app_name}"
  description  = "Service account for Cloud Run backend service"
}

# IAM roles for Cloud Run service account
resource "google_project_iam_member" "cloudrun_sa_roles" {
  for_each = toset([
    "roles/datastore.user",
    "roles/firebase.admin",
    "roles/secretmanager.secretAccessor",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/cloudtrace.agent"
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.cloudrun_sa.email}"
}

# Cloud Run service
resource "google_cloud_run_v2_service" "backend" {
  depends_on = [
    time_sleep.wait_for_apis,
    google_secret_manager_secret_version.secret_versions,
    google_secret_manager_secret_version.firebase_credentials
  ]
  
  project  = var.project_id
  location = var.region
  name     = "${var.app_name}-backend"

  template {
    service_account = google_service_account.cloudrun_sa.email
    
    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }

    containers {
      # Placeholder image - will be updated during deployment
      image = "gcr.io/cloudrun/hello"
      
      ports {
        container_port = 8000
      }

      resources {
        limits = {
          cpu    = "1000m"
          memory = "1Gi"
        }
      }

      env {
        name  = "ENVIRONMENT"
        value = "production"
      }

      env {
        name  = "DEBUG"
        value = "false"
      }

      env {
        name = "SECRET_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.secrets["SECRET_KEY"].secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "FIREBASE_PROJECT_ID"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.secrets["FIREBASE_PROJECT_ID"].secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "GOOGLE_CLIENT_ID"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.secrets["GOOGLE_CLIENT_ID"].secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "GOOGLE_CLIENT_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.secrets["GOOGLE_CLIENT_SECRET"].secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "PLAID_CLIENT_ID"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.secrets["PLAID_CLIENT_ID"].secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "PLAID_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.secrets["PLAID_SECRET"].secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "PLAID_ENV"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.secrets["PLAID_ENV"].secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "FIREBASE_CREDENTIALS"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.secrets["FIREBASE_CREDENTIALS"].secret_id
            version = "latest"
          }
        }
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  labels = {
    app = var.app_name
  }
}

# Allow unauthenticated access to Cloud Run service
resource "google_cloud_run_service_iam_member" "public_access" {
  project  = var.project_id
  location = var.region
  service  = google_cloud_run_v2_service.backend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}