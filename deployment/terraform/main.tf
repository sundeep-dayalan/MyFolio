# Terraform configuration for Sage Financial Management App deployment
terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.84"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 4.84"
    }
  }
}

# Variables
variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region"
  type        = string
  default     = "us-central1"
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "sage"
}

variable "domain" {
  description = "Custom domain for the application (optional)"
  type        = string
  default     = ""
}

variable "plaid_client_id" {
  description = "Plaid client ID"
  type        = string
  sensitive   = true
}

variable "plaid_secret" {
  description = "Plaid secret"
  type        = string
  sensitive   = true
}

variable "plaid_env" {
  description = "Plaid environment (sandbox/production)"
  type        = string
  default     = "sandbox"
}

variable "google_oauth_client_id" {
  description = "Google OAuth client ID"
  type        = string
  sensitive   = true
}

variable "google_oauth_client_secret" {
  description = "Google OAuth client secret"
  type        = string
  sensitive   = true
}

# Configure the Google Cloud Provider
provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# Data sources
data "google_project" "project" {
  project_id = var.project_id
}

# Generate a random secret key for JWT
resource "random_password" "jwt_secret" {
  length  = 32
  special = true
}

# Local values
locals {
  services = [
    "cloudbuild.googleapis.com",
    "run.googleapis.com",
    "firestore.googleapis.com",
    "secretmanager.googleapis.com",
    "firebase.googleapis.com",
    "identitytoolkit.googleapis.com",
    "oauth2.googleapis.com",
    "iamcredentials.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "storage.googleapis.com",
    "artifactregistry.googleapis.com"
  ]
}