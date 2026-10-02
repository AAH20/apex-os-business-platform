variable "name_prefix" { type = string }
variable "location" { type = string default = "East US" }
variable "resource_group_name" { type = string }
variable "tags" { type = map(string) default = {} }
