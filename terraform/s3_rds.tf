resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# Bucket S3 Privado y Cifrado para Exámenes Clínicos (Compartido entre ambas EC2)
resource "aws_s3_bucket" "lab_results" {
  bucket        = "${var.project_name}-resultados-${random_id.bucket_suffix.hex}"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "lab_results" {
  bucket                  = aws_s3_bucket.lab_results.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "lab_results" {
  bucket = aws_s3_bucket.lab_results.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "lab_results" {
  bucket = aws_s3_bucket.lab_results.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Grupo de Subredes Privadas Multi-AZ para Amazon RDS
resource "aws_db_subnet_group" "rds_subnets" {
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = { Name = "${var.project_name}-db-subnet-group" }
}

# Instancia Amazon RDS PostgreSQL (Privada y con cifrado en reposo)
resource "aws_db_instance" "postgres" {
  identifier             = "${var.project_name}-postgres"
  engine                 = "postgres"
  engine_version         = "16.3"
  instance_class         = "db.t3.micro"
  allocated_storage      = 20
  storage_type           = "gp3"
  storage_encrypted      = true
  db_name                = "medinet_lab_db"
  username               = var.db_username
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.rds_subnets.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  publicly_accessible    = false
  multi_az               = false # Mantiene estabilidad en AWS Academy; el DB Subnet Group ya abarca 2 AZs
  skip_final_snapshot    = true
  deletion_protection    = false

  tags = { Name = "${var.project_name}-rds" }
}