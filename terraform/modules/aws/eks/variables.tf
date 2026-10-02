variable "cluster_name" { type = string }
variable "cluster_version" { type = string default = "1.28" }
variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "node_instance_types" { type = list(string) default = ["t3.large"] }
variable "node_desired_size" { type = number default = 3 }
variable "node_min_size" { type = number default = 2 }
variable "node_max_size" { type = number default = 6 }
variable "tags" { type = map(string) default = {} }
