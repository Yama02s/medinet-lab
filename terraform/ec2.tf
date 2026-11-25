data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }
}

resource "aws_instance" "app_nodes" {
  count                  = 2
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = "t3.small"
  subnet_id              = aws_subnet.private[count.index].id
  vpc_security_group_ids = [aws_security_group.ec2_sg.id]
  iam_instance_profile   = "LabInstanceProfile"

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required" # Exige IMDSv2 (Checkov)
    http_put_response_hop_limit = 2
  }

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
    encrypted   = true
  }

  user_data = <<-EOF
              #!/bin/bash
              set -e
              apt-get update -y
              apt-get install -y docker.io git
              systemctl enable --now docker

              mkdir -p /opt/medinet
              cd /opt/medinet
              git clone ${var.github_repo_url} repo
              
              # Detectar si el proyecto está en la raíz o en backend-medinet-lab
              if [ -d "/opt/medinet/repo/backend-medinet-lab" ]; then
                APP_DIR="/opt/medinet/repo/backend-medinet-lab"
              else
                APP_DIR="/opt/medinet/repo"
              fi

              cd "$APP_DIR"

              cat <<EOT > .env
              PROJECT_NAME="MediNet LAB Service"
              ENVIRONMENT="production"
              DEBUG=False
              API_V1_STR="/api/lab"
              DATABASE_URL="postgresql+asyncpg://${var.db_username}:${var.db_password}@${aws_db_instance.postgres.endpoint}/medinet_lab_db"
              JWT_SECRET_KEY="${var.jwt_secret_key}"
              STORAGE_BACKEND="s3"
              AWS_S3_BUCKET_NAME="${aws_s3_bucket.lab_results.id}"
              AWS_REGION="${var.aws_region}"
              BACKEND_CORS_ORIGINS=["https://${var.domain_name}"]
              EOT

              docker build -t medinet-lab:latest .
              docker run --rm --env-file .env medinet-lab:latest alembic upgrade head
              docker run -d --name medinet-lab-app --restart always -p 8000:8000 --env-file .env medinet-lab:latest
              EOF

  depends_on = [
    aws_db_instance.postgres,
    aws_s3_bucket.lab_results,
    aws_nat_gateway.nat
  ]

  tags = {
    Name = "${var.project_name}-node-az${count.index + 1}"
  }
}

resource "aws_lb_target_group_attachment" "app_nodes" {
  count            = 2
  target_group_arn = aws_lb_target_group.app_tg.arn
  target_id        = aws_instance.app_nodes[count.index].id
  port             = 8000
}