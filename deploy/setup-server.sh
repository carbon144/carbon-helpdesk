#!/bin/bash
# ============================================
# Carbon Expert Hub - Server Setup Script
# Run this on the DigitalOcean droplet as root
# ============================================

set -e

echo "=== Carbon Expert Hub - Configurando servidor ==="

# Update system
apt-get update && apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh

# Install Docker Compose
apt-get install -y docker-compose-plugin

# Install Nginx (reverse proxy)
apt-get install -y nginx certbot python3-certbot-nginx

# Create app directory
mkdir -p /opt/carbon-helpdesk

# Enable and start Docker
systemctl enable docker
systemctl start docker

# Configure firewall
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

echo "=== Setup completo! ==="
echo "Agora faça upload dos arquivos do projeto para /opt/carbon-helpdesk/"
