#!/bin/bash
# user_data de cada EC2 del backend (Terraform reemplaza las variables de la plantilla).
# El log queda en /var/log/user-data.log y en la salida de consola de la instancia.
exec > >(tee /var/log/user-data.log | logger -t user-data -s 2>/dev/console) 2>&1
set -eu   # sin "-x" para no imprimir secretos en el log

REGION="${region}"
echo "== [1/5] Instalando Docker y cliente EFS =="
dnf install -y docker amazon-efs-utils
systemctl enable --now docker

echo "== [2/5] Montando EFS (archivos compartidos entre nodos) =="
mkdir -p /mnt/efs
for i in $(seq 1 30); do
  mount -t efs -o tls ${efs_id}:/ /mnt/efs && break
  sleep 10
done
mountpoint -q /mnt/efs
echo "${efs_id}:/ /mnt/efs efs _netdev,tls 0 0" >> /etc/fstab
mkdir -p /mnt/efs/uploads
chown 10001:10001 /mnt/efs/uploads   # uid/gid del usuario "nonroot" del contenedor
chmod 700 /mnt/efs/uploads

echo "== [3/5] Leyendo secretos desde SSM Parameter Store =="
get_param() {
  aws ssm get-parameter --name "$1" --with-decryption \
    --query Parameter.Value --output text --region "$REGION"
}
until DB_PASS=$(get_param "${ssm_db_password}"); do sleep 10; done
until JWT_SECRET=$(get_param "${ssm_jwt_secret}"); do sleep 10; done

echo "== [4/5] Generando archivo de entorno (solo legible por root) =="
install -d -m 700 /opt/medinet
umask 077
cat > /opt/medinet/.env <<ENVFILE
DATABASE_URL=postgresql+asyncpg://${db_user}:$DB_PASS@${db_host}:5432/${db_name}?ssl=require
JWT_SECRET_KEY=$JWT_SECRET
JWT_ALGORITHM=HS256
ENVIRONMENT=production
BACKEND_CORS_ORIGINS=["https://${fqdn}"]
UPLOAD_STORAGE_PATH=/app/storage/secure_uploads
ENVFILE

echo "== [5/5] Esperando ${startup_delay}s y levantando el contenedor =="
sleep ${startup_delay}
docker rm -f backend 2>/dev/null || true
docker run -d --name backend --restart unless-stopped \
  --security-opt no-new-privileges:true \
  --env-file /opt/medinet/.env \
  -p 8000:8000 \
  -v /mnt/efs/uploads:/app/storage/secure_uploads \
  ${image}:${image_tag}

echo "== user-data terminado =="
