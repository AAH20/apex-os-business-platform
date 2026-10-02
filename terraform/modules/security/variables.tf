variable "name_prefix" { type = string }
variable "environment" { type = string default = "dev" }
variable "aws_vpc_id" { type = string default = "" }
variable "allowed_cidr_blocks" { type = list(string) default = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"] }
variable "enable_waf" { type = bool default = true }
variable "enable_shield" { type = bool default = false }
variable "enable_guardduty" { type = bool default = true }
variable "enable_securityhub" { type = bool default = true }
variable "enable_flow_logs" { type = bool default = true }
variable "enable_encryption_at_rest" { type = bool default = true }
variable "enable_encryption_in_transit" { type = bool default = true }
variable "tags" { type = map(string) default = {} }
