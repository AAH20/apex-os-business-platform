variable "identifier" { type = string }
variable "engine" { type = string default = "postgres" }
variable "engine_version" { type = string default = "15.4" }
variable "instance_class" { type = string default = "db.t3.medium" }
variable "allocated_storage" { type = number default = 100 }
variable "multi_az" { type = bool default = true }
variable "vpc_id" { type = string }
variable "subnet_ids" { type = list(string) }
variable "allowed_cidr_blocks" { type = list(string) default = [] }
variable "tags" { type = map(string) default = {} }
