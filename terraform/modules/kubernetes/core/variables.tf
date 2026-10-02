variable "namespaces" { type = list(string) default = ["apex-os-core", "apex-os-data", "apex-os-monitoring", "apex-os-security"] }
variable "enable_istio" { type = bool default = false }
variable "enable_cert_manager" { type = bool default = true }
variable "environment" { type = string default = "dev" }
