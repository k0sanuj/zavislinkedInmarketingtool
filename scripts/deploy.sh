#!/bin/bash
# ============================================================
# Zavis LinkedIn Tool — Deploy / Update Script
# Run this anytime to deploy or update the application
# ============================================================

set -e

cd ~/zavislinkedInmarketingtool

echo "========================================="
echo "  Zavis LinkedIn Tool — Deploy"
echo "========================================="

# 1. Pull latest code
echo "[1/4] Pulling latest code..."
git pull origin main

# 2. Check .env exists
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Run: cp .env.example .env && nano .env"
    exit 1
fi

# Check required vars
if ! grep -q "DB_PASSWORD=" .env || grep -q "DB_PASSWORD=$" .env; then
    echo "ERROR: DB_PASSWORD not set in .env"
    exit 1
fi

# 3. Build and start containers
echo "[2/4] Building containers (this takes a few minutes first time)..."
docker compose -f docker-compose.prod.yml build

echo "[3/4] Starting services..."
docker compose -f docker-compose.prod.yml up -d

# 4. Wait and check health
echo "[4/4] Waiting for services to start..."
sleep 10

echo ""
echo "========================================="
echo "  Service Status"
echo "========================================="
docker compose -f docker-compose.prod.yml ps

echo ""
echo "========================================="
echo "  Deployment complete!"
echo "========================================="
echo ""
echo "Your app is running at: http://$(curl -s ifconfig.me)"
echo "API docs available at:  http://$(curl -s ifconfig.me)/docs"
echo ""
echo "Useful commands:"
echo "  View logs:      docker compose -f docker-compose.prod.yml logs -f"
echo "  Stop app:       docker compose -f docker-compose.prod.yml down"
echo "  Restart app:    docker compose -f docker-compose.prod.yml restart"
echo "  Update & deploy: bash scripts/deploy.sh"
echo ""
