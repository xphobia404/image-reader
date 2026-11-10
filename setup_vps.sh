#!/bin/bash
set -e

echo "=================================================="
echo "    Setup Toll Receipt Reader App on Linux VPS    "
echo "=================================================="

# 1. Update package list & install system dependencies for OpenCV
echo "[1/4] Menginstall dependensi sistem..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv libgl1 libglib2.0-0 git curl

# 2. Setup Python virtual environment
echo "[2/4] Menyiapkan Python Virtual Environment..."
python3 -m venv venv
source venv/bin/activate

# 3. Upgrade pip and install requirements
echo "[3/4] Menginstall paket Python..."
pip install --upgrade pip
pip install -r requirements.txt

# 4. Buat service systemd agar aplikasi berjalan terus di background
echo "[4/4] Mengatur Systemd Service..."
APP_DIR=$(pwd)
CURRENT_USER=$(whoami)

sudo bash -c "cat <<EOF > /etc/systemd/system/toll-reader.service
[Unit]
Description=Toll Receipt Reader Streamlit App
After=network.target

[Service]
User=$CURRENT_USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
Restart=always
RestartSec=5
Environment=PATH=$APP_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
EnvironmentFile=-$APP_DIR/.env

[Install]
WantedBy=multi-user.target
EOF"

sudo systemctl daemon-reload
sudo systemctl enable toll-reader
sudo systemctl restart toll-reader

echo "=================================================="
echo "✅ Aplikasi BERHASIL dideploy dan berjalan!"
echo "Status service: sudo systemctl status toll-reader"
echo "Akses aplikasi di: http://<IP_VPS_ANDA>:8501"
echo "=================================================="
