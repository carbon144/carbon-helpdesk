#!/bin/bash
# ============================================
# Carbon Expert Hub - Deploy Script
# Run this from your Mac inside the carbon-helpdesk folder
# ============================================

SERVER_IP="143.198.20.6"
SERVER_USER="root"
REMOTE_DIR="/opt/carbon-helpdesk"

echo "=== Carbon Expert Hub - Deploy ==="
echo "Servidor: $SERVER_IP"
echo ""

# Step 1: Setup server (only first time)
echo ">>> Step 1: Configurando servidor..."
ssh $SERVER_USER@$SERVER_IP 'bash -s' < deploy/setup-server.sh

# Step 2: Sync project files to server
echo ">>> Step 2: Enviando arquivos..."
rsync -avz --progress \
    --exclude 'node_modules' \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '.env.local' \
    --exclude 'deploy' \
    ./ $SERVER_USER@$SERVER_IP:$REMOTE_DIR/

# Step 3: Copy nginx config
echo ">>> Step 3: Configurando Nginx..."
scp deploy/nginx.conf $SERVER_USER@$SERVER_IP:/etc/nginx/sites-available/carbon-helpdesk
ssh $SERVER_USER@$SERVER_IP "ln -sf /etc/nginx/sites-available/carbon-helpdesk /etc/nginx/sites-enabled/ && rm -f /etc/nginx/sites-enabled/default && nginx -t && systemctl reload nginx"

# Step 4: Start Docker containers on server
echo ">>> Step 4: Iniciando containers..."
ssh $SERVER_USER@$SERVER_IP "cd $REMOTE_DIR && docker compose down 2>/dev/null; docker compose up -d --build"

echo ""
echo "=== Deploy concluído! ==="
echo "Acesse: http://$SERVER_IP"
echo ""
echo "Para SSL (HTTPS), configure o domínio helpdesk.carbonsmartwatch.com.br"
echo "apontando para $SERVER_IP e depois rode:"
echo "  ssh root@$SERVER_IP 'certbot --nginx -d helpdesk.carbonsmartwatch.com.br'"
