output "cluster_name" { value = google_container_cluster.main.name }
output "cluster_endpoint" { value = google_container_cluster.main.endpoint sensitive = true }
output "cluster_ca_cert" { value = google_container_cluster.main.master_auth[0].cluster_ca_certificate sensitive = true }
output "access_token" { value = data.google_client_config.default.access_token sensitive = true }
output "cluster_id" { value = google_container_cluster.main.id }
