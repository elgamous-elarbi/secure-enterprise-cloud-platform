output "trail_arn" {
  description = "ARN du trail CloudTrail"
  value       = aws_cloudtrail.this.arn
}

output "bucket_name" {
  description = "Nom du bucket S3 contenant les logs CloudTrail"
  value       = aws_s3_bucket.cloudtrail.id
}