#!/bin/bash
# Script de diagnóstico - rodar no servidor via SSH
# ssh root@143.198.20.6 'bash /opt/carbon-helpdesk/deploy/debug-502.sh'

echo "=== 1. STATUS DOS CONTAINERS ==="
cd /opt/carbon-helpdesk
docker compose ps

echo ""
echo "=== 2. PORTAS ABERTAS ==="
ss -tlnp | grep -E '3000|8000|5173|80|443'

echo ""
echo "=== 3. TESTE CONEXÃO FRONTEND (porta 3000) ==="
curl -s -o /dev/null -w "HTTP %{http_code}" http://127.0.0.1:3000/ 2>&1 || echo "FALHOU"

echo ""
echo "=== 4. TESTE CONEXÃO BACKEND (porta 8000) ==="
curl -s -o /dev/null -w "HTTP %{http_code}" http://127.0.0.1:8000/api/health 2>&1 || echo "FALHOU"

echo ""
echo "=== 5. LOGS FRONTEND (últimas 30 linhas) ==="
docker compose logs --tail=30 frontend 2>&1

echo ""
echo "=== 6. LOGS BACKEND (últimas 30 linhas) ==="
docker compose logs --tail=30 backend 2>&1

echo ""
echo "=== 7. DOCKER COMPOSE PORTS ==="
docker compose port frontend 5173 2>&1 || echo "porta 5173 não mapeada"
docker compose port frontend 3000 2>&1 || echo "porta 3000 não mapeada"
docker compose port backend 8000 2>&1 || echo "porta 8000 não mapeada"

echo ""
echo "=== 8. NGINX STATUS ==="
systemctl status nginx --no-pager -l 2>&1 | head -15

echo ""
echo "=== 9. NGINX ERROR LOG ==="
tail -20 /var/log/nginx/error.log 2>&1
