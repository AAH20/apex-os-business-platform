variable "name_prefix" { type = string }
variable "project_id" { type = string }
variable "region" { type = string default = "us-central1" }
variable "vpc_cidr" { type = string default = "10.2.0.0/16" }
variable "tags" { type = map(string) default = {} }
