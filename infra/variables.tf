variable "aws_region" {
  type        = string
  description = "AWS Region deploy Lakehouse"
  default     = "us-east-1"
}


variable "project_name" {
  type        = string
  description = "Ten dinh danh du an"
  default     = "retail-customer-lakehouse"
}

variable "environment" {
  type        = string
  description = "Moi truong trien khai (dev/staging/prod)"
  default     = "dev"
}

variable "billing_threshold_usd" {
  type        = number
  description = "Nguong canh bao chi phi CloudWatch (USD)"
  default     = 1.0
}
