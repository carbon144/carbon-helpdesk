#!/bin/bash
# Deploy Carbon Expert Hub to server
set -e

SERVER="143.198.20.6"
USER="root"
PASS='OdysseY144.-a'
REMOTE_DIR="/opt/carbon-helpdesk"

echo "=== Syncing files to server ==="
sshpass -p "$PASS" rsync -avz --exclude 'node_modules' --exclude '.git' --exclude '__pycache__' --exclude '.env' --exclude 'venv' --exclude '.venv' --exclude 'dist' \
  ~/Desktop/carbon-helpdesk/ ${USER}@${SERVER}:${REMOTE_DIR}/

echo "=== Rebuilding and restarting containers ==="
sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o PubkeyAuthentication=no ${USER}@${SERVER} "cd ${REMOTE_DIR} && docker compose up -d --build"

echo "=== Done! ==="
echo "Access: http://${SERVER}"
