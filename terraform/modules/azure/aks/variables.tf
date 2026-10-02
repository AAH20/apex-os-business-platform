variable "cluster_name" { type = string }
variable "location" { type = string default = "East US" }
variable "resource_group_name" { type = string }
variable "kubernetes_version" { type = string default = "1.28" }
variable "vnet_id" { type = string }
variable "subnet_id" { type = string }
variable "node_count" { type = number default = 3 }
variable "vm_size" { type = string default = "Standard_D2s_v3" }
variable "tags" { type = map(string) default = {} }
