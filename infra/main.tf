# Tu dong lay thong tin Account ID va Region cua tai khoan AWS dang chay lenh
data "aws_caller_identity" "current" {}

locals {
  account_id         = data.aws_caller_identity.current.account_id
  bronze_bucket_name = "${var.project_name}-${local.account_id}-bronze"
  silver_bucket_name = "${var.project_name}-${local.account_id}-silver"
  gold_bucket_name   = "${var.project_name}-${local.account_id}-gold"
}

# ==============================================================================
# 1. S3 MEDALLION LAKEHOUSE BUCKETS
# ==============================================================================

# 1.1 Bronze Bucket (Raw Data Landing Zone)
resource "aws_s3_bucket" "bronze" {
  bucket        = local.bronze_bucket_name
  force_destroy = true # Cho phep teardown sach se khi huy lab

  tags = {
    Layer = "Bronze"
    Type  = "RawLanding"
  }
}

resource "aws_s3_bucket_public_access_block" "bronze" {
  bucket = aws_s3_bucket.bronze.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "bronze" {
  bucket = aws_s3_bucket.bronze.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# 1.2 Silver Bucket (Cleaned & Imputed Parquet Transactions)
resource "aws_s3_bucket" "silver" {
  bucket        = local.silver_bucket_name
  force_destroy = true

  tags = {
    Layer = "Silver"
    Type  = "CleanedParquet"
  }
}

resource "aws_s3_bucket_public_access_block" "silver" {
  bucket = aws_s3_bucket.silver.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "silver" {
  bucket = aws_s3_bucket.silver.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# 1.3 Gold Bucket (RFM Customer Features & ML Clustering Outputs)
resource "aws_s3_bucket" "gold" {
  bucket        = local.gold_bucket_name
  force_destroy = true

  tags = {
    Layer = "Gold"
    Type  = "AnalyticalFeatures"
  }
}

resource "aws_s3_bucket_public_access_block" "gold" {
  bucket = aws_s3_bucket.gold.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "gold" {
  bucket = aws_s3_bucket.gold.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# ==============================================================================
# 2. FINOPS: CLOUDWATCH BILLING SPEND ALARM (1.00 USD)
# ==============================================================================

resource "aws_cloudwatch_metric_alarm" "billing_alert" {
  alarm_name          = "CustomerSegmentation-Spend-Alert-${var.billing_threshold_usd}USD"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = 21600 # 6 tieng
  statistic           = "Maximum"
  threshold           = var.billing_threshold_usd
  alarm_description   = "Canh bao khan khi chi phi thuc hanh AWS vuot ${var.billing_threshold_usd} USD"

  dimensions = {
    Currency = "USD"
  }
}

# ==============================================================================
# 3. AWS GLUE METASTORE CATALOG (SERVERLESS LAKEHOUSE QUERY)
# ==============================================================================

resource "aws_glue_catalog_database" "retail_lakehouse" {
  name        = "retail_customer_analytics"
  description = "Glue Catalog Database phuc vu truy van Athena Lakehouse"
}
