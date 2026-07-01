#!/bin/bash
# ==============================================================================
# Production Deployment Script for Symptom Triage Assistant on AWS EC2 (Ubuntu 24.04)
# ==============================================================================

set -e

echo "======================================================================"
echo " Starting Deployment of Symptom Triage Assistant"
echo "======================================================================"

# ----------------------------------------------------------------------
# 1. Update System
# ----------------------------------------------------------------------
echo "--> Updating system package repositories..."
sudo apt update -y
sudo apt upgrade -y

# ----------------------------------------------------------------------
# 2. Install Python & Required Packages
# ----------------------------------------------------------------------
echo "--> Installing Python, pip, virtualenv, sqlite3 and build tools..."

sudo apt install -y \
python3 \
python3-pip \
python3-venv \
python3-dev \
sqlite3 \
git \
curl \
build-essential

echo "--> Verifying Python installation..."
python3 --version
pip3 --version

# ----------------------------------------------------------------------
# 3. Install Node.js 20 LTS
# ----------------------------------------------------------------------
echo "--> Installing Node.js 20 LTS..."

curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

echo "--> Verifying Node installation..."
node --version
npm --version

# ----------------------------------------------------------------------
# 4. Install Ollama
# ----------------------------------------------------------------------
if ! command -v ollama &> /dev/null
then
    echo "--> Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "--> Ollama already installed."
fi

echo "--> Starting Ollama..."

sudo systemctl enable ollama
sudo systemctl start ollama

sleep 5

echo "--> Pulling llama3.2:3b model..."
ollama pull llama3.2:3b

# ----------------------------------------------------------------------
# 5. Backend Setup
# ----------------------------------------------------------------------
echo "--> Setting up backend..."

cd backend

python3 -m venv .venv

source .venv/bin/activate

python -m pip install --upgrade pip

pip install -r requirements.txt

deactivate

cd ..

# ----------------------------------------------------------------------
# 6. Frontend Setup
# ----------------------------------------------------------------------
echo "--> Setting up frontend..."

cd frontend

npm install

npm run build

cd ..

# ----------------------------------------------------------------------
# 7. Create Systemd Service
# ----------------------------------------------------------------------

echo "--> Creating systemd service..."

CURRENT_DIR=$(pwd)

sudo tee /etc/systemd/system/symptom-triage.service > /dev/null <<EOF
[Unit]
Description=Symptom Triage Assistant
After=network.target ollama.service

[Service]
User=ubuntu
WorkingDirectory=$CURRENT_DIR/backend
ExecStart=$CURRENT_DIR/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

Environment=DATABASE_PATH=$CURRENT_DIR/backend/symptom_triage.db
Environment=OLLAMA_BASE_URL=http://127.0.0.1:11434

[Install]
WantedBy=multi-user.target
EOF

# ----------------------------------------------------------------------
# 8. Enable Service
# ----------------------------------------------------------------------

echo "--> Starting application..."

sudo systemctl daemon-reload
sudo systemctl enable symptom-triage
sudo systemctl restart symptom-triage

echo
echo "======================================================================"
echo " Deployment Completed Successfully!"
echo "======================================================================"
echo
echo "Backend URL:"
echo "http://<EC2-PUBLIC-IP>:8000"
echo
echo "Check service status:"
echo "sudo systemctl status symptom-triage"
echo
echo "View logs:"
echo "journalctl -u symptom-triage -f"
echo
echo "======================================================================"
