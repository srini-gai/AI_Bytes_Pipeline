# Deployment Skill — AI Bytes VPS

> Hostinger KVM2 VPS (187.127.151.27), Ubuntu 22.04, systemd + cron.

---

## VPS Setup (one-time)

```bash
# Connect
ssh root@187.127.151.27

# Update system
apt-get update && apt-get upgrade -y

# Install Python 3.11
apt-get install -y python3.11 python3.11-venv python3-pip

# Install Node.js 20 (for Remotion)
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# Install FFmpeg (includes ffprobe)
apt-get install -y ffmpeg

# Install Whisper system deps
apt-get install -y python3-dev

# Create app user
useradd -m -s /bin/bash aibytes
su - aibytes
```

---

## Deploy Pipeline

```bash
# On local machine — rsync to VPS
rsync -avz --exclude='.env' --exclude='output/' --exclude='venv/' --exclude='node_modules/' \
  "C:/Additional case AI/AI_Bytes_Pipeline/" \
  root@187.127.151.27:/home/aibytes/pipeline/

# On VPS — set up venv and install deps
cd /home/aibytes/pipeline
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install Remotion deps
cd remotion && npm install && cd ..

# Copy .env (do this manually — never rsync secrets)
nano /home/aibytes/pipeline/.env
```

---

## systemd Service

Save as `/etc/systemd/system/aibytes.service`:

```ini
[Unit]
Description=AI Bytes Pipeline
After=network.target

[Service]
Type=oneshot
User=aibytes
WorkingDirectory=/home/aibytes/pipeline
ExecStart=/home/aibytes/pipeline/venv/bin/python orchestrator.py
StandardOutput=append:/home/aibytes/pipeline/orchestrator.log
StandardError=append:/home/aibytes/pipeline/orchestrator.log
Environment=PATH=/home/aibytes/pipeline/venv/bin:/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and test
systemctl daemon-reload
systemctl start aibytes
systemctl status aibytes
```

---

## Cron Schedule (Sunday 6:00 AM IST = 00:30 UTC)

```bash
# Edit crontab as aibytes user
crontab -e

# Add this line:
30 0 * * 0 /home/aibytes/pipeline/venv/bin/python /home/aibytes/pipeline/orchestrator.py >> /home/aibytes/pipeline/orchestrator.log 2>&1
```

---

## Verify Deployment

```bash
# Manual test run — dry run first
cd /home/aibytes/pipeline
source venv/bin/activate
python orchestrator.py --dry-run

# Check log
tail -50 orchestrator.log

# Full run test (episode 1 only)
python orchestrator.py --episode 1
```

---

## Monitoring

```bash
# Watch log in real time
tail -f orchestrator.log

# Check last run
grep "Pipeline complete" orchestrator.log | tail -1

# Check cron ran
grep "CRON" /var/log/syslog | grep aibytes
```
