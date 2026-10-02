output "data_bucket_name" { value = google_storage_bucket.data.name }
output "data_bucket_url" { value = google_storage_bucket.data.url }
output "backups_bucket_name" { value = google_storage_bucket.backups.name }
output "backups_bucket_url" { value = google_storage_bucket.backups.url }
