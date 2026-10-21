output "bronze_bucket_id" {
  description = "Ten S3 Bronze Bucket"
  value       = aws_s3_bucket.bronze.id
}

output "silver_bucket_id" {
  description = "Ten S3 Silver Bucket"
  value       = aws_s3_bucket.silver.id
}

output "gold_bucket_id" {
  description = "Ten S3 Gold Bucket"
  value       = aws_s3_bucket.gold.id
}

output "cloudwatch_alarm_name" {
  description = "Ten CloudWatch Billing Alarm"
  value       = aws_cloudwatch_metric_alarm.billing_alert.alarm_name
}

output "glue_database_name" {
  description = "Ten AWS Glue Catalog Database"
  value       = aws_glue_catalog_database.retail_lakehouse.name
}

# ==============================================================================
# SAGEMAKER NOTEBOOK INSTANCE OUTPUTS
# ==============================================================================

output "sagemaker_notebook_name" {
  description = "Ten SageMaker Notebook Instance"
  value       = aws_sagemaker_notebook_instance.eda_notebook.name
}

output "sagemaker_notebook_url" {
  description = "Duong dan truc tiep mo JupyterLab tren AWS Console"
  value       = "https://${aws_sagemaker_notebook_instance.eda_notebook.name}.notebook.${var.aws_region}.sagemaker.aws"
}

output "sagemaker_execution_role_arn" {
  description = "ARN cua IAM Role gan cho SageMaker"
  value       = aws_iam_role.sagemaker_execution.arn
}
