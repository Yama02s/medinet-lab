variable "aws_region" {
  description = "Región de AWS Academy"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Prefijo para los recursos"
  type        = string
  default     = "medinet-lab"
}

variable "github_repo_url" {
  description = "URL pública de tu repositorio en GitHub"
  type        = string
  default     = "https://github.com/Yama02s/medinet-lab.git"
}

variable "domain_name" {
  description = "FQDN gratuito registrado (ej. medinet-lab.duckdns.org)"
  type        = string
}

variable "db_username" {
  description = "Usuario maestro de Amazon RDS PostgreSQL"
  type        = string
  default     = "medinet_admin"
}

variable "db_password" {
  description = "Contraseña de RDS (se pasa por variable de entorno TF_VAR_db_password)"
  type        = string
  sensitive   = true
}

variable "jwt_secret_key" {
  description = "Clave secreta para validar tokens JWT (TF_VAR_jwt_secret_key)"
  type        = string
  sensitive   = true
}

variable "ssl_cert_path" {
  description = "Ruta local al archivo cert.pem de Let's Encrypt"
  type        = string
  default     = "./certs/cert.pem"
}

variable "ssl_private_key_path" {
  description = "Ruta local al archivo privkey.pem de Let's Encrypt"
  type        = string
  default     = "./certs/privkey.pem"
}

variable "ssl_chain_path" {
  description = "Ruta local al archivo chain.pem de Let's Encrypt"
  type        = string
  default     = "./certs/chain.pem"
}