# ----------------------------------------------------------------------------
# Secretos generados por Terraform y guardados en SSM Parameter Store.
# Nunca se escriben en el repositorio; las EC2 los leen al arrancar usando
# LabInstanceProfile.
# ----------------------------------------------------------------------------
resource "random_password" "db" {
  length  = 24
  special = false
}

resource "random_password" "jwt" {
  length  = 48
  special = false
}

resource "aws_ssm_parameter" "db_password" {
  #checkov:skip=CKV_AWS_337:SecureString cifrado con la clave administrada por AWS (aws/ssm); una CMK propia queda fuera del alcance del laboratorio
  name  = "/${var.project}/db_password"
  type  = "SecureString"
  value = random_password.db.result
}

resource "aws_ssm_parameter" "jwt_secret" {
  #checkov:skip=CKV_AWS_337:SecureString cifrado con la clave administrada por AWS (aws/ssm); una CMK propia queda fuera del alcance del laboratorio
  name  = "/${var.project}/jwt_secret"
  type  = "SecureString"
  value = var.jwt_secret_key != "" ? var.jwt_secret_key : random_password.jwt.result
}
