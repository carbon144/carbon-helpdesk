#!/bin/bash
# Deploy Carbon Expert Hub to server
set -e

SERVER="143.198.20.6"
USER="root"
PASS='OdysseY144.-a'
REMOTE_DIR="/opt/carbon-helpdesk"

echo "=== Carbon Helpdesk Deploy ==="
echo "[$(date)] Starting deployment..."

# Step 1: Backup database before deploy
echo ""
echo "=== Step 1: Backing up database ==="
sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o PubkeyAuthentication=no ${USER}@${SERVER} \
  "cd ${REMOTE_DIR} && bash deploy/backup.sh" 2>/dev/null || {
    echo "WARNING: Backup failed or no existing database. Continuing deploy..."
}

# Step 2: Sync files to server
echo ""
echo "=== Step 2: Syncing files to server ==="
sshpass -p "$PASS" rsync -avz \
  --exclude 'node_modules' \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude '.env' \
  --exclude 'venv' \
  --exclude '.venv' \
  --exclude 'dist' \
  --exclude 'backups' \
  ~/Desktop/carbon-helpdesk/ ${USER}@${SERVER}:${REMOTE_DIR}/

# Step 3: Build and restart containers
echo ""
echo "=== Step 3: Rebuilding and restarting containers ==="
sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o PubkeyAuthentication=no ${USER}@${SERVER} \
  "cd ${REMOTE_DIR} && docker compose -f docker-compose.prod.yml up -d --build"

# Step 4: Verify deployment
echo ""
echo "=== Step 4: Verifying deployment ==="
sleep 10
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://${SERVER}/api/health 2>/dev/null || echo "000")
if [ "$HTTP_STATUS" = "200" ]; then
    echo "Health check passed (HTTP $HTTP_STATUS)"
else
    echo "WARNING: Health check returned HTTP $HTTP_STATUS (server may still be starting)"
fi

echo ""
echo "=== Deploy complete! ==="
echo "Access: http://${SERVER}"
echo "[$(date)] Deployment finished."
