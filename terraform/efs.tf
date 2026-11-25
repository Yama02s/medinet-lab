# ----------------------------------------------------------------------------
# EFS: almacenamiento compartido para los PDF de resultados.
# Sin esto, un archivo subido por el nodo A no existiria para el nodo B.
# ----------------------------------------------------------------------------
resource "aws_efs_file_system" "uploads" {
  #checkov:skip=CKV_AWS_184:Cifrado en reposo activo con la clave administrada por AWS (aws/elasticfilesystem); una CMK propia agrega costo y gestion de claves fuera del alcance del laboratorio
  creation_token = "${var.project}-uploads"
  encrypted      = true

  tags = { Name = "${var.project}-uploads" }
}

resource "aws_efs_mount_target" "uploads" {
  count           = 2
  file_system_id  = aws_efs_file_system.uploads.id
  subnet_id       = aws_subnet.private[count.index].id
  security_groups = [aws_security_group.efs.id]
}
