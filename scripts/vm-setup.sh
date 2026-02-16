#!/bin/bash
# ============================================================
# Zavis LinkedIn Tool — One-Time VM Setup Script
# Run this ONCE on a fresh GCP Compute Engine Ubuntu 22.04 VM
# ============================================================

set -e

echo "========================================="
echo "  Zavis LinkedIn Tool — VM Setup"
echo "========================================="

# 1. Update system
echo "[1/5] Updating system packages..."
sudo apt-get update -y && sudo apt-get upgrade -y

# 2. Install Docker
echo "[2/5] Installing Docker..."
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Let current user run docker without sudo
sudo usermod -aG docker $USER

# 3. Install git
echo "[3/5] Installing Git..."
sudo apt-get install -y git

# 4. Clone the repo
echo "[4/5] Cloning repository..."
cd ~
if [ -d "zavislinkedInmarketingtool" ]; then
    echo "Repo already exists, pulling latest..."
    cd zavislinkedInmarketingtool && git pull origin main
else
    git clone https://github.com/k0sanuj/zavislinkedInmarketingtool.git
    cd zavislinkedInmarketingtool
fi

# 5. Create .env file from template
echo "[5/5] Setting up environment file..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "========================================="
    echo "  IMPORTANT: Edit your .env file!"
    echo "========================================="
    echo ""
    echo "Run this command to edit your secrets:"
    echo "  nano .env"
    echo ""
    echo "You MUST fill in these values:"
    echo "  - DB_PASSWORD (any strong password)"
    echo "  - LINKEDIN_LI_AT_COOKIE"
    echo "  - LINKEDIN_JSESSIONID_COOKIE"
    echo "  - ANTHROPIC_API_KEY or OPENAI_API_KEY"
    echo "  - SECRET_KEY (any random string)"
    echo ""
else
    echo ".env file already exists, skipping..."
fi

echo ""
echo "========================================="
echo "  Setup complete!"
echo "========================================="
echo ""
echo "NEXT STEPS:"
echo "  1. Log out and back in (so Docker group takes effect):"
echo "     exit"
echo "     (then reconnect via SSH)"
echo ""
echo "  2. Edit your .env file:"
echo "     cd ~/zavislinkedInmarketingtool && nano .env"
echo ""
echo "  3. Deploy the app:"
echo "     cd ~/zavislinkedInmarketingtool && bash scripts/deploy.sh"
echo ""
