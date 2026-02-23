#!/bin/bash
set -e

echo "=== Configurando servidor Carbon Helpdesk ==="

# Atualizar sistema
echo ">>> Atualizando sistema..."
apt-get update -y
apt-get upgrade -y

# Instalar Docker
echo ">>> Instalando Docker..."
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Verificar Docker
echo ">>> Verificando Docker..."
docker --version
docker compose version

# Instalar Nginx
echo ">>> Instalando Nginx..."
apt-get install -y nginx certbot python3-certbot-nginx

# Configurar firewall
echo ">>> Configurando firewall..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Configurar Nginx
echo ">>> Configurando Nginx..."
cat > /etc/nginx/sites-available/carbon-helpdesk << 'NGINX'
server {
    listen 80;
    server_name helpdesk.carbonsmartwatch.com.br _;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
NGINX

rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/carbon-helpdesk /etc/nginx/sites-enabled/carbon-helpdesk
nginx -t && systemctl restart nginx

# Iniciar containers
echo ">>> Iniciando containers..."
cd /opt/carbon-helpdesk
docker compose up -d --build

echo ""
echo "=== Servidor configurado com sucesso! ==="
echo "Acesse: http://$(curl -s ifconfig.me)"
