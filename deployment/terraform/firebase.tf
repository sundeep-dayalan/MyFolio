# Firebase project (assumes project already exists)
data "google_firebase_project" "default" {
  depends_on = [time_sleep.wait_for_apis]
  project    = var.project_id
}

# Enable Firebase Hosting
resource "google_firebase_hosting_site" "default" {
  depends_on = [data.google_firebase_project.default]
  project    = var.project_id
  site_id    = var.project_id
  app_id     = null # Will use default app
}

# Configure OAuth for Google Sign-In
resource "google_identity_platform_default_supported_idp_config" "google_sign_in" {
  depends_on    = [time_sleep.wait_for_apis]
  project       = var.project_id
  enabled       = true
  idp_id        = "google.com"
  client_id     = var.google_oauth_client_id
  client_secret = var.google_oauth_client_secret
}