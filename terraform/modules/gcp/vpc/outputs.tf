output "vpc_id" { value = google_compute_network.main.id }
output "vpc_name" { value = google_compute_network.main.name }
output "gke_subnet_id" { value = google_compute_subnetwork.gke.id }
output "gke_subnet_name" { value = google_compute_subnetwork.gke.name }
output "gke_pods_cidr" { value = "10.3.0.0/16" }
output "gke_services_cidr" { value = "10.4.0.0/20" }
