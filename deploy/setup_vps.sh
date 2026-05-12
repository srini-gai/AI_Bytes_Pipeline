#!/usr/bin/env bash
# AI Bytes Pipeline — VPS setup script
# Run once on a fresh Ubuntu 22.04 VPS as root (or with sudo)
# Usage: bash setup_vps.sh

set -euo pipefail

APP_DIR="/opt/aibytes"
LOG_DIR="/var/log/aibytes"
SERVICE_USER="ubuntu"

echo "=== AI Bytes VPS Setup ==="

# ── System packages ────────────────────────────────────────────────
apt-get update -qq
apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3.11-dev \
    ffmpeg \
    nodejs npm \
    git curl wget \
    ca-certificates

# ── Node.js 20 (Remotion needs 18+) ───────────────────────────────
if ! node --version 2>/dev/null | grep -qE '^v(1[89]|[2-9][0-9])'; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
fi

echo "Node: $(node --version)  npm: $(npm --version)"

# ── App directory ──────────────────────────────────────────────────
mkdir -p "$APP_DIR" "$LOG_DIR"
chown "$SERVICE_USER:$SERVICE_USER" "$APP_DIR" "$LOG_DIR"

# ── Python venv ────────────────────────────────────────────────────
sudo -u "$SERVICE_USER" bash -c "
    cd '$APP_DIR'
    python3.11 -m venv venv
    venv/bin/pip install --upgrade pip wheel
    venv/bin/pip install -r requirements.txt
"

# ── Node dependencies for Remotion ────────────────────────────────
sudo -u "$SERVICE_USER" bash -c "
    cd '$APP_DIR/remotion'
    npm install
    # Pre-download Chrome Headless Shell
    npx remotion browser ensure
"

# ── Systemd service + timer ────────────────────────────────────────
cp deploy/aibytes.service /etc/systemd/system/aibytes.service
cp deploy/aibytes.timer   /etc/systemd/system/aibytes.timer

systemctl daemon-reload
systemctl enable aibytes.timer
systemctl start  aibytes.timer

echo ""
echo "=== Setup complete ==="
echo "Timer status:"
systemctl status aibytes.timer --no-pager
echo ""
echo "Next steps:"
echo "  1. Copy your .env to $APP_DIR/.env"
echo "  2. Copy credentials/ folder to $APP_DIR/credentials/"
echo "  3. Edit topics.txt for Week 1"
echo "  4. Test: sudo -u $SERVICE_USER $APP_DIR/venv/bin/python orchestrator.py --dry-run"
echo "  5. Manual run: systemctl start aibytes.service"
echo "  6. Watch logs: tail -f $LOG_DIR/pipeline.log"
