resource "random_id" "bucket_suffix" {
  byte_length = 4
}

locals {
  s3_bucket_name = "${var.project_name}-resultados-${random_id.bucket_suffix.hex}"
}

# Bucket S3 Privado, Versionado y Cifrado (Compatible con Windows PowerShell y SCP de AWS Academy)
resource "terraform_data" "lab_results_bucket" {
  input = local.s3_bucket_name

  provisioner "local-exec" {
    interpreter = ["PowerShell", "-Command"]
    environment = {
      BUCKET_NAME        = local.s3_bucket_name
      AWS_DEFAULT_REGION = var.aws_region
    }
    command = <<-EOT
      @'
      import os, boto3

      s3 = boto3.client("s3", region_name=os.environ["AWS_DEFAULT_REGION"])
      b = os.environ["BUCKET_NAME"]

      if b not in [x["Name"] for x in s3.list_buckets()["Buckets"]]:
          s3.create_bucket(Bucket=b)

      s3.put_public_access_block(
          Bucket=b,
          PublicAccessBlockConfiguration={
              "BlockPublicAcls": True,
              "IgnorePublicAcls": True,
              "BlockPublicPolicy": True,
              "RestrictPublicBuckets": True,
          },
      )

      s3.put_bucket_encryption(
          Bucket=b,
          ServerSideEncryptionConfiguration={
              "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
          },
      )

      s3.put_bucket_versioning(
          Bucket=b,
          VersioningConfiguration={"Status": "Enabled"},
      )

      print("S3 configurado:", b)
      '@ | python
    EOT
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
  engine_version         = "16"
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
  multi_az               = false
  skip_final_snapshot    = true
  deletion_protection    = false

  tags = { Name = "${var.project_name}-rds" }
}