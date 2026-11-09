# Read-only role Grafana Cloud assumes to query CloudWatch (observe-with-grafana D5): the
# dashboard shows AWS/Bedrock token counts next to the app's own, to reconcile the two.
# Grafana Assume Role: Grafana's AWS account assumes this role with the stack's external ID,
# so no access key exists anywhere. Values come from Grafana's CloudWatch data source page.

variable "grafana_aws_account_id" {
  description = "Grafana Cloud's AWS account allowed to assume the role (CloudWatch data source page, Grafana Assume Role)."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.grafana_aws_account_id))
    error_message = "grafana_aws_account_id must be a 12-digit AWS account ID."
  }
}

variable "grafana_external_id" {
  description = "The stack's external ID shown on the same page; without it any Grafana stack could assume the role."
  type        = string

  validation {
    condition     = length(var.grafana_external_id) > 0
    error_message = "grafana_external_id must not be empty."
  }
}

data "aws_iam_policy_document" "grafana_trust" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${var.grafana_aws_account_id}:root"]
    }

    condition {
      test     = "StringEquals"
      variable = "sts:ExternalId"
      values   = [var.grafana_external_id]
    }
  }
}

# Read metrics only: no Bedrock calls, no logs, no writes. CloudWatch metric reads have no
# resource-level permissions, so the resource is "*".
data "aws_iam_policy_document" "cloudwatch_read" {
  statement {
    actions = [
      "cloudwatch:GetMetricData",
      "cloudwatch:GetMetricStatistics",
      "cloudwatch:ListMetrics",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role" "grafana_cloudwatch" {
  name               = "brewql-grafana-cloudwatch-read"
  description        = "Grafana Cloud reads CloudWatch metrics for BrewQL cost reconciliation."
  assume_role_policy = data.aws_iam_policy_document.grafana_trust.json
}

resource "aws_iam_role_policy" "grafana_cloudwatch_read" {
  name   = "cloudwatch-read"
  role   = aws_iam_role.grafana_cloudwatch.id
  policy = data.aws_iam_policy_document.cloudwatch_read.json
}

output "grafana_cloudwatch_role_arn" {
  description = "Paste into the CloudWatch data source's Assume Role ARN field."
  value       = aws_iam_role.grafana_cloudwatch.arn
}
