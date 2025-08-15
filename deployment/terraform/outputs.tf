# Terraform outputs
output "project_id" {
  description = "The GCP project ID"
  value       = var.project_id
}

output "region" {
  description = "The GCP region"
  value       = var.region
}

output "backend_url" {
  description = "Backend Cloud Run service URL"
  value       = google_cloud_run_v2_service.backend.uri
}

output "artifact_registry_repo" {
  description = "Artifact Registry repository for container images"
  value       = google_artifact_registry_repository.repo.name
}

output "firestore_database" {
  description = "Firestore database name"
  value       = google_firestore_database.database.name
}

output "firebase_hosting_site" {
  description = "Firebase Hosting site ID"
  value       = google_firebase_hosting_site.default.site_id
}

output "firebase_service_account_email" {
  description = "Firebase service account email"
  value       = google_service_account.firebase_sa.email
}

output "cloudrun_service_account_email" {
  description = "Cloud Run service account email"
  value       = google_service_account.cloudrun_sa.email
}

output "deployment_instructions" {
  description = "Next steps for deployment"
  value = <<-EOT
    Infrastructure has been created successfully!
    
    Next steps:
    1. Build and deploy the backend: ./scripts/deploy-backend.sh
    2. Build and deploy the frontend: ./scripts/deploy-frontend.sh
    3. Configure OAuth redirect URIs in Google Cloud Console
    4. Test the application
    
    Backend URL: ${google_cloud_run_v2_service.backend.uri}
    Frontend will be available at: https://${var.project_id}.web.app
  EOT
}