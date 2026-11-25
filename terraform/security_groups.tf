# ----------------------------------------------------------------------------
# Security Groups ENCADENADOS:
#   Internet -> SG-ALB -> SG-EC2 -> SG-RDS (y SG-EFS)
# Las reglas se declaran por separado para evitar dependencias circulares.
# ----------------------------------------------------------------------------
resource "aws_security_group" "alb" {
  name        = "${var.project}-alb-sg"
  description = "ALB: HTTP y HTTPS desde internet"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${var.project}-alb-sg" }
}

resource "aws_security_group" "ec2" {
  name        = "${var.project}-ec2-sg"
  description = "Backend: solo trafico desde el ALB"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${var.project}-ec2-sg" }
}

resource "aws_security_group" "rds" {
  name        = "${var.project}-rds-sg"
  description = "RDS: solo PostgreSQL desde el backend"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${var.project}-rds-sg" }
}

resource "aws_security_group" "efs" {
  name        = "${var.project}-efs-sg"
  description = "EFS: solo NFS desde el backend"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${var.project}-efs-sg" }
}

# --- ALB ---------------------------------------------------------------
resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  #checkov:skip=CKV_AWS_260:El puerto 80 solo existe para redirigir con 301 a HTTPS (exigido por la pauta); el listener no reenvia trafico a la aplicacion
  security_group_id = aws_security_group.alb.id
  description       = "HTTP desde internet (solo redirige a HTTPS)"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
}

resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  security_group_id = aws_security_group.alb.id
  description       = "HTTPS desde internet"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

resource "aws_vpc_security_group_egress_rule" "alb_to_ec2" {
  security_group_id            = aws_security_group.alb.id
  description                  = "ALB hacia el backend (puerto de la app)"
  referenced_security_group_id = aws_security_group.ec2.id
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8000
}

# --- EC2 (backend) -----------------------------------------------------
resource "aws_vpc_security_group_ingress_rule" "ec2_from_alb" {
  security_group_id            = aws_security_group.ec2.id
  description                  = "App solo desde el SG del ALB"
  referenced_security_group_id = aws_security_group.alb.id
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8000
}

resource "aws_vpc_security_group_egress_rule" "ec2_https" {
  security_group_id = aws_security_group.ec2.id
  description       = "HTTPS saliente (GHCR, SSM, repositorios) via NAT"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

resource "aws_vpc_security_group_egress_rule" "ec2_http" {
  security_group_id = aws_security_group.ec2.id
  description       = "HTTP saliente (repositorios del sistema) via NAT"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
}

resource "aws_vpc_security_group_egress_rule" "ec2_to_rds" {
  security_group_id            = aws_security_group.ec2.id
  description                  = "Backend hacia PostgreSQL"
  referenced_security_group_id = aws_security_group.rds.id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
}

resource "aws_vpc_security_group_egress_rule" "ec2_to_efs" {
  security_group_id            = aws_security_group.ec2.id
  description                  = "Backend hacia EFS (NFS)"
  referenced_security_group_id = aws_security_group.efs.id
  ip_protocol                  = "tcp"
  from_port                    = 2049
  to_port                      = 2049
}

# --- RDS ---------------------------------------------------------------
resource "aws_vpc_security_group_ingress_rule" "rds_from_ec2" {
  security_group_id            = aws_security_group.rds.id
  description                  = "PostgreSQL solo desde el SG del backend"
  referenced_security_group_id = aws_security_group.ec2.id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
}

# --- EFS ---------------------------------------------------------------
resource "aws_vpc_security_group_ingress_rule" "efs_from_ec2" {
  security_group_id            = aws_security_group.efs.id
  description                  = "NFS solo desde el SG del backend"
  referenced_security_group_id = aws_security_group.ec2.id
  ip_protocol                  = "tcp"
  from_port                    = 2049
  to_port                      = 2049
}
