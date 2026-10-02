variable "name_prefix" { type = string }
variable "vpc_cidr" { type = string default = "10.0.0.0/16" }
variable "private_subnet_cidrs" { type = list(string) }
variable "public_subnet_cidrs" { type = list(string) }
variable "availability_zones" { type = list(string) }
variable "enable_flow_logs" { type = bool default = true }
variable "enable_encryption_at_rest" { type = bool default = true }
variable "tags" { type = map(string) default = {} }
