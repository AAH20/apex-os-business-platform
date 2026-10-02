variable "name_prefix" { type = string }
variable "project_id" { type = string }
variable "region" { type = string default = "us-central1" }
variable "tags" { type = map(string) default = {} }
