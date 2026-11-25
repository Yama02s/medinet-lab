# Importa el certificado SSL/TLS válido generado con Let's Encrypt para tu dominio DuckDNS
resource "aws_acm_certificate" "cert" {
  private_key       = file(var.ssl_private_key_path)
  certificate_body  = file(var.ssl_cert_path)
  certificate_chain = file(var.ssl_chain_path)

  lifecycle {
    create_before_destroy = true
  }
}

# Application Load Balancer en las 2 subredes públicas
resource "aws_lb" "alb" {
  name                       = "${var.project_name}-alb"
  internal                   = false
  load_balancer_type         = "application"
  security_groups            = [aws_security_group.alb_sg.id]
  subnets                    = aws_subnet.public[*].id
  drop_invalid_header_fields = true

  tags = { Name = "${var.project_name}-alb" }
}

# Target Group con Health Check activo hacia el servicio
resource "aws_lb_target_group" "app_tg" {
  name     = "${var.project_name}-tg"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id

  health_check {
    enabled             = true
    path                = "/"
    port                = "traffic-port"
    protocol            = "HTTP"
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 15
    matcher             = "200"
  }
}

# Listener HTTPS (Puerto 443) con política TLS 1.2/1.3 moderna
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.alb.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate.cert.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app_tg.arn
  }
}

# Listener HTTP (Puerto 80) con redirección automática a HTTPS (443)
resource "aws_lb_listener" "http_redirect" {
  load_balancer_arn = aws_lb.alb.arn
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