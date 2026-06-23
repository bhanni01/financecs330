# Variables let us name values once and reuse them, instead of repeating strings.
variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
  default     = "finance"
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}
