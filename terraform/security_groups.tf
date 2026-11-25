# Capa 1: Security Group del Application Load Balancer (Único expuesto a Internet)
resource "aws_security_group" "alb_sg" {
  name        = "${var.project_name}-alb-sg"
  description = "Permite trafico HTTP (80) y HTTPS (443) desde Internet hacia el ALB"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP para redireccion a HTTPS"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS seguro"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project_name}-alb-sg" }
}

# Regla independiente de salida del ALB hacia las EC2 (Rompe la dependencia circular)
resource "aws_security_group_rule" "alb_to_ec2" {
  type                     = "egress"
  description              = "Salida unicamente hacia las instancias EC2 en puerto 8000"
  from_port                = 8000
  to_port                  = 8000
  protocol                 = "tcp"
  security_group_id        = aws_security_group.alb_sg.id
  source_security_group_id = aws_security_group.ec2_sg.id
}

# Capa 2: Security Group de los nodos EC2 (Solo acepta tráfico del ALB)
resource "aws_security_group" "ec2_sg" {
  name        = "${var.project_name}-ec2-sg"
  description = "Acepta trafico en puerto 8000 exclusivamente desde el ALB"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Trafico de aplicacion desde ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id]
  }

  egress {
    description = "Salida a RDS, S3 y repositorios de paquetes via NAT"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project_name}-ec2-sg" }
}

# Capa 3: Security Group de Amazon RDS (Solo acepta tráfico desde los nodos EC2)
resource "aws_security_group" "rds_sg" {
  name        = "${var.project_name}-rds-sg"
  description = "Acepta conexiones PostgreSQL (5432) exclusivamente desde EC2"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "PostgreSQL desde nodos Backend"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2_sg.id]
  }

  tags = { Name = "${var.project_name}-rds-sg" }
}