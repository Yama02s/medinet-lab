# ----------------------------------------------------------------------------
# Certificado TLS (emitido por Let's Encrypt, importado a ACM).
# Los archivos estan en terraform/certs/ y NO se suben al repositorio.
# ----------------------------------------------------------------------------
resource "aws_acm_certificate" "imported" {
  private_key       = file("${path.module}/${var.cert_dir}/privkey.pem")
  certificate_body  = file("${path.module}/${var.cert_dir}/cert.pem")
  certificate_chain = file("${path.module}/${var.cert_dir}/chain.pem")

  lifecycle {
    create_before_destroy = true
  }
}

# ----------------------------------------------------------------------------
# Application Load Balancer en las 2 subredes publicas (2 AZ)
# ----------------------------------------------------------------------------
resource "aws_lb" "main" {
  #checkov:skip=CKV_AWS_150:El laboratorio requiere poder destruir el ambiente con terraform destroy al terminar cada sesion
  #checkov:skip=CKV_AWS_91:Los access logs requieren un bucket S3 con politica dedicada; se registra como mejora futura. La auditoria funcional se envia al modulo AUD
  #checkov:skip=CKV2_AWS_28:AWS WAF queda fuera del alcance y presupuesto del laboratorio; mitigado con validacion estricta en la aplicacion y escaneo DAST
  name               = "${var.project}-alb"
  load_balancer_type = "application"
  internal           = false
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  drop_invalid_header_fields = true
  enable_deletion_protection = false

  tags = { Name = "${var.project}-alb" }
}

resource "aws_lb_target_group" "backend" {
  name                 = "${var.project}-tg"
  port                 = 8000
  protocol             = "HTTP"
  vpc_id               = aws_vpc.main.id
  deregistration_delay = 30

  # Health checks activos: un nodo caido se detecta en ~20 s (2 fallos x 10 s)
  health_check {
    path                = var.health_check_path
    matcher             = "200"
    interval            = 10
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }

  tags = { Name = "${var.project}-tg" }
}

resource "aws_lb_target_group_attachment" "backend" {
  count            = 2
  target_group_arn = aws_lb_target_group.backend.arn
  target_id        = aws_instance.backend[count.index].id
  port             = 8000
}

# HTTPS (443) con TLS 1.2/1.3
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate.imported.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }
}

# HTTP (80) -> redireccion permanente a HTTPS
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}
