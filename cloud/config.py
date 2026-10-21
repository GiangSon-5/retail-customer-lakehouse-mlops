"""
================================================================================
Module: cloud/config.py
Dự án: Retail Customer Segmentation & AWS Medallion Lakehouse
Mục tiêu:
    - Quản lý tập trung toàn bộ cấu hình hạ tầng AWS Cloud.
    - Đồng bộ tự động với các output từ Terraform.
================================================================================
"""

# AWS Region
AWS_REGION = "us-east-1"

# S3 Medallion Lakehouse Buckets
S3_BRONZE_BUCKET = "retail-customer-lakehouse-876760932342-bronze"
S3_SILVER_BUCKET = "retail-customer-lakehouse-876760932342-silver"
S3_GOLD_BUCKET = "retail-customer-lakehouse-876760932342-gold"

# AWS IAM Execution Role cho SageMaker
SAGEMAKER_ROLE_ARN = "arn:aws:iam::876760932342:role/retail-customer-lakehouse-sagemaker-execution-role"

# AWS Managed Scikit-learn Container Image
SKLEARN_IMAGE_URI = "683313688378.dkr.ecr.us-east-1.amazonaws.com/sagemaker-scikit-learn:1.2-1-cpu-py3"

# SageMaker Processing Resource Defaults
DEFAULT_INSTANCE_TYPE = "ml.t3.medium"
DEFAULT_INSTANCE_COUNT = 1
DEFAULT_VOLUME_SIZE_GB = 20
DEFAULT_MAX_RUNTIME_SECONDS = 1800
