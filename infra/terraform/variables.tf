variable "aws_region" {
  description = "Region the API calls Bedrock in; the guardrail lives here."
  type        = string
  default     = "us-east-1"
}

variable "guardrail_profile_id" {
  description = "System-defined cross-Region guardrail profile; Standard tier requires one."
  type        = string
  default     = "us.guardrail.v1:0"
}
