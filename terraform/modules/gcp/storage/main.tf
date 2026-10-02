# GCP Storage Module - Cloud Storage buckets for APEX-OS

variable "name_prefix" {
  description = "Name prefix for storage buckets"
  type        = string
}

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "tags" {
  description = "Labels to apply to resources"
  type        = map(string)
  default     = {}
}

# Data Bucket
resource "google_storage_bucket" "data" {
  name          = "${var.name_prefix}-data-${var.project_id}"
  location      = var.region
  project       = var.project_id
  storage_class = "STANDARD"

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }

  lifecycle_rule {
    condition {
      age = 2555
    }
    action {
      type = "Delete"
    }
  }

  encryption {
    default_kms_key_name = google_kms_crypto_key.storage.id
  }

  labels = var.tags

  depends_on = [google_kms_crypto_key_iam_member.storage]
}

# Backups Bucket
resource "google_storage_bucket" "backups" {
  name          = "${var.name_prefix}-backups-${var.project_id}"
  location      = var.region
  project       = var.project_id
  storage_class = "NEARLINE"

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }

  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type          = "SetStorageClass"
      storage_class = "ARCHIVE"
    }
  }

  encryption {
    default_kms_key_name = google_kms_crypto_key.storage.id
  }

  labels = var.tags

  depends_on = [google_kms_crypto_key_iam_member.storage]
}

# KMS Key Ring
resource "google_kms_key_ring" "storage" {
  name     = "${var.name_prefix}-storage-keyring"
  location = var.region
  project  = var.project_id
}

# KMS Crypto Key
resource "google_kms_crypto_key" "storage" {
  name            = "${var.name_prefix}-storage-key"
  key_ring        = google_kms_key_ring.storage.id
  rotation_period = "7776000s" # 90 days

  lifecycle {
    prevent_destroy = true
  }
}

# Allow Cloud Storage to use the KMS key
resource "google_kms_crypto_key_iam_member" "storage" {
  crypto_key_id = google_kms_crypto_key.storage.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = "serviceAccount:service-${var.project_id}@gs-project-accounts.iam.gserviceaccount.com"
}

# Outputs
output "data_bucket_name" {
  value = google_storage_bucket.data.name
}

output "data_bucket_url" {
  value = google_storage_bucket.data.url
}

output "backups_bucket_name" {
  value = google_storage_bucket.backups.name
}

output "backups_bucket_url" {
  value = google_storage_bucket.backups.url
}
