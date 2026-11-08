# Input guardrail: checks each question before the SQL model sees it.
# Standard tier because Classic only understands English, French and Spanish.

data "aws_caller_identity" "current" {}

locals {
  account_id            = data.aws_caller_identity.current.account_id
  guardrail_profile_arn = "arn:aws:bedrock:${var.aws_region}:${local.account_id}:guardrail-profile/${var.guardrail_profile_id}"
}

resource "aws_bedrock_guardrail" "input" {
  name        = "brewql-input"
  description = "Blocks prompt attacks and questions unrelated to Find Coffee operations data."

  # Shown to users as the refusal reason.
  blocked_input_messaging   = "這個問題無法處理：BrewQL 只回答 Find Coffee 咖啡店營運數據的問題。"
  blocked_outputs_messaging = "這個回覆無法顯示。"

  cross_region_config {
    guardrail_profile_identifier = local.guardrail_profile_arn
  }

  content_policy_config {
    filters_config {
      type            = "PROMPT_ATTACK"
      input_strength  = "HIGH"
      output_strength = "NONE" # prompt attacks only apply to input
    }

    tier_config {
      tier_name = "STANDARD"
    }
  }

  topic_policy_config {
    topics_config {
      name = "off-topic"
      type = "DENY"
      # Describe what to block, not what to allow: the topic classifier misreads "requests that are not X"
      # (it blocked search-trend questions). Other off-topic questions are refused by the model.
      definition = "Creative writing, general chat or small talk, coding help, personal advice, weather, news or entertainment, or asking the assistant to change its role or ignore its instructions."
      examples = [
        "幫我寫一首詩",
        "今天天氣如何？",
        "推薦我一部電影",
        "幫我寫一個 Python 程式",
      ]
    }

    tier_config {
      tier_name = "STANDARD"
    }
  }
}

# The API pins a published version, never DRAFT, so edits go live only on purpose.
# The description hashes the policy, so a policy change publishes a new version.
# skip_destroy keeps the old version when a policy change publishes a new one, so the
# running API (still pinned to the old number) keeps working until .env is updated.
resource "aws_bedrock_guardrail_version" "current" {
  guardrail_arn = aws_bedrock_guardrail.input.guardrail_arn
  skip_destroy  = true
  description = "policy ${substr(sha1(jsonencode([
    aws_bedrock_guardrail.input.content_policy_config,
    aws_bedrock_guardrail.input.topic_policy_config,
    aws_bedrock_guardrail.input.blocked_input_messaging,
  ])), 0, 12)}"
}

# Least privilege for the API's IAM user; attach it by hand (IAM users stay out of
# Terraform so their keys never land in state).
data "aws_iam_policy_document" "apply_guardrail" {
  statement {
    actions = ["bedrock:ApplyGuardrail"]
    resources = [
      aws_bedrock_guardrail.input.guardrail_arn,
      # Standard tier may evaluate in any Region of the US profile.
      "arn:aws:bedrock:*:${local.account_id}:guardrail-profile/${var.guardrail_profile_id}",
    ]
  }
}
