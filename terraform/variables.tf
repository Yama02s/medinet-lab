variable "region" {
  description = "Region de AWS (Learner Lab usa us-east-1)"
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Prefijo para nombrar los recursos"
  type        = string
  default     = "medinet-lab"
}

variable "azs" {
  description = "Dos zonas de disponibilidad"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "Subredes publicas (ALB y NAT), una por AZ"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "Subredes privadas (EC2, RDS y EFS), una por AZ"
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24"]
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}

variable "db_instance_class" {
  type    = string
  default = "db.t3.micro"
}

variable "db_name" {
  type    = string
  default = "lab_db"
}

variable "db_username" {
  type    = string
  default = "lab_admin"
}

variable "container_image" {
  description = "Imagen del backend en GHCR (sin tag, en minusculas)"
  type        = string
  default     = "ghcr.io/yama02s/medinet-lab/medinet-lab"
}

variable "image_tag" {
  description = "Tag de la imagen a desplegar (idealmente el SHA del commit)"
  type        = string
}

variable "domain_name" {
  description = "FQDN gratuito que apunta al ALB (ej. medinet-lab.duckdns.org)"
  type        = string
}

variable "cert_dir" {
  description = "Carpeta (dentro de terraform/) con cert.pem, chain.pem y privkey.pem. NO se sube al repo"
  type        = string
  default     = "certs"
}

variable "health_check_path" {
  type    = string
  default = "/health"
}

variable "jwt_secret_key" {
  description = "Clave JWT compartida con el modulo IAM. Si se deja vacia se genera una aleatoria"
  type        = string
  default     = ""
  sensitive   = true
}
