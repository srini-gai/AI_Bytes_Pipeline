#!/usr/bin/env bash
# AI Bytes Pipeline — incremental deploy (sync code to VPS without re-running setup)
# Usage: bash deploy/deploy.sh [VPS_IP]
# Example: bash deploy/deploy.sh 187.127.151.27

set -euo pipefail

VPS_IP="${1:-187.127.151.27}"
VPS_USER="ubuntu"
APP_DIR="/opt/aibytes"
KEY="${HOME}/.ssh/id_rsa"

echo "Deploying to ${VPS_USER}@${VPS_IP}:${APP_DIR}"

# Sync code (exclude credentials, venv, output, node_modules)
rsync -avz --progress \
    --exclude ".git" \
    --exclude "venv/" \
    --exclude "node_modules/" \
    --exclude "output/" \
    --exclude "credentials/" \
    --exclude ".env" \
    --exclude "__pycache__/" \
    --exclude "*.pyc" \
    --exclude "remotion/.cache/" \
    -e "ssh -i ${KEY}" \
    ./ "${VPS_USER}@${VPS_IP}:${APP_DIR}/"

# Re-install Python deps if requirements changed
ssh -i "${KEY}" "${VPS_USER}@${VPS_IP}" "
    cd ${APP_DIR}
    venv/bin/pip install -q -r requirements.txt
    cd remotion && npm install --silent
"

# Reload systemd if service files changed
ssh -i "${KEY}" "${VPS_USER}@${VPS_IP}" "
    sudo cp ${APP_DIR}/deploy/aibytes.service /etc/systemd/system/aibytes.service
    sudo cp ${APP_DIR}/deploy/aibytes.timer   /etc/systemd/system/aibytes.timer
    sudo systemctl daemon-reload
    sudo systemctl restart aibytes.timer
"

echo "Deploy complete. Timer status:"
ssh -i "${KEY}" "${VPS_USER}@${VPS_IP}" "systemctl status aibytes.timer --no-pager"
