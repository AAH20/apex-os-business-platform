variable "cluster_name" { type = string }
variable "project_id" { type = string }
variable "region" { type = string default = "us-central1" }
variable "kubernetes_version" { type = string default = "1.28" }
variable "vpc_id" { type = string }
variable "subnet_id" { type = string }
variable "node_count" { type = number default = 3 }
variable "machine_type" { type = string default = "e2-medium" }
variable "tags" { type = map(string) default = {} }
