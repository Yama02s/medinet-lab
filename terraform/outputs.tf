output "alb_dns_name" {
  description = "Nombre DNS del ALB (de aqui se obtiene la IP para el FQDN)"
  value       = aws_lb.main.dns_name
}

output "app_url" {
  value = "https://${var.domain_name}/docs"
}

output "rds_endpoint" {
  value = aws_db_instance.main.address
}

output "efs_id" {
  value = aws_efs_file_system.uploads.id
}

output "instance_ids" {
  value = aws_instance.backend[*].id
}

output "target_group_arn" {
  value = aws_lb_target_group.backend.arn
}
