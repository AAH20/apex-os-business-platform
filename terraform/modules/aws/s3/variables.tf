variable "bucket_names" { type = list(string) default = [] }
variable "name_prefix" { type = string }
variable "enable_encryption_at_rest" { type = bool default = true }
variable "tags" { type = map(string) default = {} }
