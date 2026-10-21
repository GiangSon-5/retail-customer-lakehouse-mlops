# ==============================================================================
# AMAZON SAGEMAKER NOTEBOOK INSTANCE & IAM SECURITY INFRASTRUCTURE
# ==============================================================================

# 1. IAM Execution Role cho SageMaker
resource "aws_iam_role" "sagemaker_execution" {
  name        = "${var.project_name}-sagemaker-execution-role"
  description = "IAM Execution Role cap quyen cho SageMaker Notebook truy cap S3 Medallion Lakehouse"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "sagemaker.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# 2. Gan quyen co ban cua SageMaker (AmazonSageMakerFullAccess)
resource "aws_iam_role_policy_attachment" "sagemaker_base_execution" {
  role       = aws_iam_role.sagemaker_execution.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
}

# 3. Policy cap quyen rieng biet doc/ghi tren 3 S3 Buckets Medallion (Least Privilege)
resource "aws_iam_policy" "sagemaker_s3_medallion" {
  name        = "${var.project_name}-sagemaker-s3-medallion-policy"
  description = "Quyen truy cap truc tiep vao 3 bucket Bronze, Silver, Gold cua Lakehouse"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = [
          aws_s3_bucket.bronze.arn,
          aws_s3_bucket.silver.arn,
          aws_s3_bucket.gold.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "${aws_s3_bucket.bronze.arn}/*",
          "${aws_s3_bucket.silver.arn}/*",
          "${aws_s3_bucket.gold.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "sagemaker_s3_attachment" {
  role       = aws_iam_role.sagemaker_execution.name
  policy_arn = aws_iam_policy.sagemaker_s3_medallion.arn
}

# 4. SageMaker Notebook Instance (ml.t3.medium - Free Tier 250h/thang)
resource "aws_sagemaker_notebook_instance" "eda_notebook" {
  name          = "${var.project_name}-eda-notebook"
  role_arn      = aws_iam_role.sagemaker_execution.arn
  instance_type = "ml.t3.medium"
  volume_size   = 5 # 5 GB EBS disk

  direct_internet_access = "Enabled"

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
