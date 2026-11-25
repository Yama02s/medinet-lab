# ----------------------------------------------------------------------------
# Amazon RDS PostgreSQL: subredes privadas, sin acceso publico, cifrado en reposo
# Una UNICA instancia consumida por ambos nodos del backend.
# ----------------------------------------------------------------------------
resource "aws_db_subnet_group" "main" {
  name       = "${var.project}-db-subnets"
  subnet_ids = aws_subnet.private[*].id

  tags = { Name = "${var.project}-db-subnets" }
}

# ----------------------------------------------------------------------------
# Grupo de parametros: registro de consultas (CKV2_AWS_30) y TLS obligatorio.
# log_statement = "ddl" registra cambios de estructura (CREATE/ALTER/DROP) pero
# NO las consultas con datos, para no dejar informacion clinica en los logs
# (minimizacion de datos, Ley 19.628/21.719 e ISO 27799).
# ----------------------------------------------------------------------------
resource "aws_db_parameter_group" "main" {
  name   = "${var.project}-pg16"
  family = "postgres16"

  parameter {
    name  = "log_statement"
    value = "ddl"
  }

  # Registra solo la duracion de consultas lentas (> 1 s), sin sus valores
  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }

  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }

  tags = { Name = "${var.project}-pg16" }
}

resource "aws_db_instance" "main" {
  #checkov:skip=CKV_AWS_157:La pauta exige UNA unica instancia RDS consumida por ambos nodos; el DB Subnet Group si abarca 2 AZ
  #checkov:skip=CKV_AWS_293:El laboratorio (AWS Academy) requiere poder destruir el ambiente con terraform destroy al terminar cada sesion
  #checkov:skip=CKV_AWS_118:Enhanced Monitoring requiere crear un rol IAM propio, prohibido en AWS Academy (solo LabRole)
  #checkov:skip=CKV_AWS_353:Performance Insights no aporta a la evaluacion y no esta disponible en todas las clases micro; se usa CloudWatch y logs exportados
  #checkov:skip=CKV_AWS_354:Depende de Performance Insights (deshabilitado, ver CKV_AWS_353)
  identifier = "${var.project}-db"

  engine         = "postgres"
  engine_version = "16"
  instance_class = var.db_instance_class

  allocated_storage = 20
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = var.db_name
  username = var.db_username
  password = random_password.db.result

  db_subnet_group_name   = aws_db_subnet_group.main.name
  parameter_group_name   = aws_db_parameter_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false

  # CKV_AWS_161 corregido: autenticacion IAM habilitada (ademas de la contrasena en SSM)
  iam_database_authentication_enabled = true

  # CKV_AWS_129 corregido: logs del motor exportados a CloudWatch Logs
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  multi_az               = false

  backup_retention_period    = 1
  auto_minor_version_upgrade = true
  copy_tags_to_snapshot      = true

  # Necesario para poder hacer "terraform destroy" en el laboratorio
  deletion_protection = false
  skip_final_snapshot = true
}
