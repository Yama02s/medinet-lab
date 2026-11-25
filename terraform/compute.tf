# ----------------------------------------------------------------------------
# 2 instancias EC2 del backend, una por AZ, en subredes PRIVADAS (sin IP publica
# y sin llave SSH). Usan el LabInstanceProfile de AWS Academy.
# ----------------------------------------------------------------------------
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "backend" {
  count = 2

  # CKV_AWS_126 corregido: monitoreo detallado de CloudWatch (metricas cada 1 minuto)
  monitoring = true

  ami                         = data.aws_ami.al2023.id
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.private[count.index].id
  vpc_security_group_ids      = [aws_security_group.ec2.id]
  iam_instance_profile        = "LabInstanceProfile"
  associate_public_ip_address = false
  ebs_optimized               = true

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required" # IMDSv2 obligatorio
  }

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
    encrypted   = true
  }

  # replace(): elimina los saltos de linea de Windows (CRLF) que romperian el script en Linux
  user_data = replace(templatefile("${path.module}/user_data.sh.tpl", {
    region          = var.region
    efs_id          = aws_efs_file_system.uploads.id
    ssm_db_password = aws_ssm_parameter.db_password.name
    ssm_jwt_secret  = aws_ssm_parameter.jwt_secret.name
    db_user         = var.db_username
    db_host         = aws_db_instance.main.address
    db_name         = var.db_name
    fqdn            = var.domain_name
    image           = var.container_image
    image_tag       = var.image_tag
    # El nodo 2 espera 90 s para no migrar la BD al mismo tiempo que el nodo 1
    startup_delay = count.index * 90
  }), "\r\n", "\n")
  user_data_replace_on_change = true

  # La salida a internet (NAT) y el EFS deben existir antes de arrancar
  depends_on = [
    aws_route_table_association.private,
    aws_nat_gateway.main,
    aws_efs_mount_target.uploads,
  ]

  tags = { Name = "${var.project}-backend-${count.index + 1}" }
}
