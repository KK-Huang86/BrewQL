output "guardrail_id" {
  description = "Set as BEDROCK_GUARDRAIL_ID in .env."
  value       = aws_bedrock_guardrail.input.guardrail_id
}

output "guardrail_version" {
  description = "Set as BEDROCK_GUARDRAIL_VERSION in .env."
  value       = aws_bedrock_guardrail_version.current.version
}

output "apply_guardrail_policy_json" {
  description = "Inline policy to attach to the API's IAM user."
  value       = data.aws_iam_policy_document.apply_guardrail.json
}
