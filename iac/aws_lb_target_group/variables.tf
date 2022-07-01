variable "src" {
  type = object({
    backend    = string
    config_key = string
    name       = string
  })
}

variable "tags" {
  type = object({
    Description = string
  })
}
