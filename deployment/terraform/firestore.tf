# Create Firestore database
resource "google_firestore_database" "database" {
  depends_on  = [time_sleep.wait_for_apis]
  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  # Prevent deletion protection for easier automation
  deletion_policy = "ABANDON"
}

# Create Firestore indexes for better query performance
resource "google_firestore_index" "user_transactions_by_date" {
  depends_on = [google_firestore_database.database]
  project    = var.project_id
  database   = google_firestore_database.database.name
  collection = "users/{user_id}/transactions"

  fields {
    field_path = "date"
    order      = "DESCENDING"
  }

  fields {
    field_path = "__name__"
    order      = "DESCENDING"
  }
}

resource "google_firestore_index" "user_transactions_by_category" {
  depends_on = [google_firestore_database.database]
  project    = var.project_id
  database   = google_firestore_database.database.name
  collection = "users/{user_id}/transactions"

  fields {
    field_path = "category"
    order      = "ASCENDING"
  }

  fields {
    field_path = "date"
    order      = "DESCENDING"
  }

  fields {
    field_path = "__name__"
    order      = "DESCENDING"
  }
}