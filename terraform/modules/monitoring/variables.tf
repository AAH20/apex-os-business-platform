variable "name_prefix" { type = string }
variable "environment" { type = string default = "dev" }
variable "retention_days" { type = number default = 30 }
variable "alert_email" { type = string default = "alerts@apex-os.io" }
variable "grafana_admin_password" { type = string default = "admin" sensitive = true }
variable "enable_prometheus" { type = bool default = true }
variable "enable_grafana" { type = bool default = true }
variable "enable_alertmanager" { type = bool default = true }
variable "enable_loki" { type = bool default = true }
variable "enable_tempo" { type = bool default = true }
variable "tags" { type = map(string) default = {} }
