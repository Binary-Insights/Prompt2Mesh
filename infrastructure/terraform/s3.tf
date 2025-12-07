# S3 Bucket for User Files
resource "aws_s3_bucket" "user_files" {
  bucket = "${var.s3_bucket_name}-${var.aws_account_id}"

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-user-files"
    }
  )
}

# S3 Bucket Versioning
resource "aws_s3_bucket_versioning" "user_files" {
  bucket = aws_s3_bucket.user_files.id

  versioning_configuration {
    status = var.enable_s3_versioning ? "Enabled" : "Disabled"
  }
}

# S3 Bucket Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "user_files" {
  bucket = aws_s3_bucket.user_files.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 Bucket Public Access Block
resource "aws_s3_bucket_public_access_block" "user_files" {
  bucket = aws_s3_bucket.user_files.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Bucket Lifecycle Policy (optional - clean up old files)
resource "aws_s3_bucket_lifecycle_configuration" "user_files" {
  bucket = aws_s3_bucket.user_files.id

  rule {
    id     = "delete-old-versions"
    status = "Enabled"

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }

  rule {
    id     = "abort-incomplete-uploads"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# S3 Bucket CORS Configuration (for web uploads)
resource "aws_s3_bucket_cors_configuration" "user_files" {
  bucket = aws_s3_bucket.user_files.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST", "DELETE", "HEAD"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}
