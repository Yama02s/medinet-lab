output "alb_dns_name" {
  description = "DNS del Application Load Balancer (Apuntar tu dominio DuckDNS aquí)"
  value       = aws_lb.alb.dns_name
}

output "s3_bucket_name" {
  description = "Nombre del bucket privado S3 creado"
  value       = terraform_data.lab_results_bucket.output
}

output "rds_endpoint" {
  description = "Endpoint privado de Amazon RDS PostgreSQL"
  value       = aws_db_instance.postgres.endpoint
}

output "ec2_instance_ids" {
  description = "IDs de los 2 nodos EC2 en distintas AZs (Para la prueba de Failover)"
  value       = aws_instance.app_nodes[*].id
}