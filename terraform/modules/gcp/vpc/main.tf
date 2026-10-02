# GCP VPC Module - Network infrastructure for APEX-OS

variable "name_prefix" {
  description = "Name prefix for resources"
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

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.2.0.0/16"
}

variable "tags" {
  description = "Labels to apply to resources"
  type        = map(string)
  default     = {}
}

# VPC Network
resource "google_compute_network" "main" {
  name                    = "${var.name_prefix}-vpc"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"

  labels = var.tags
}

# GKE Subnet
resource "google_compute_subnetwork" "gke" {
  name          = "${var.name_prefix}-gke-subnet"
  ip_cidr_range = "10.2.0.0/22"
  region        = var.region
  network       = google_compute_network.main.id

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.3.0.0/16"
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.4.0.0/20"
  }

  private_ip_google_access = true

  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }

  labels = var.tags
}

# Cloud Router
resource "google_compute_router" "main" {
  name    = "${var.name_prefix}-router"
  region  = var.region
  network = google_compute_network.main.id

  labels = var.tags
}

# Cloud NAT
resource "google_compute_router_nat" "main" {
  name                               = "${var.name_prefix}-nat"
  router                             = google_compute_router.main.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }

  labels = var.tags
}

# Firewall Rules
resource "google_compute_firewall" "allow_internal" {
  name    = "${var.name_prefix}-allow-internal"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = [var.vpc_cidr, "10.3.0.0/16", "10.4.0.0/20"]

  labels = var.tags
}

resource "google_compute_firewall" "allow_https" {
  name    = "${var.name_prefix}-allow-https"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = ["443", "80"]
  }

  source_ranges = ["0.0.0.0/0"]

  labels = var.tags
}

# Outputs
output "vpc_id" {
  value = google_compute_network.main.id
}

output "vpc_name" {
  value = google_compute_network.main.name
}

output "gke_subnet_id" {
  value = google_compute_subnetwork.gke.id
}

output "gke_subnet_name" {
  value = google_compute_subnetwork.gke.name
}

output "gke_pods_cidr" {
  value = "10.3.0.0/16"
}

output "gke_services_cidr" {
  value = "10.4.0.0/20"
}
