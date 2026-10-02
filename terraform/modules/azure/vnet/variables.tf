variable "name_prefix" { type = string }
variable "location" { type = string default = "East US" }
variable "resource_group_name" { type = string }
variable "vnet_cidr" { type = string default = "10.1.0.0/16" }
variable "tags" { type = map(string) default = {} }
