#!/usr/bin/env bash
# One-time bootstrap for any Debian/Ubuntu VM — GCP e2-micro, Oracle Ampere A1 or AMD.
# The image is built on your laptop (deploy/build-push.sh); this VM only pulls and runs it.
#
#     scp -r cc-mimic/deploy <user>@<VM_IP>:~/deploy
#     ssh <user>@<VM_IP> 'sudo bash ~/deploy/vm-setup.sh'
set -euo pipefail

SECRET_DIR=/etc/cc-mimic
APP_DIR=/opt/cc-mimic
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

die() { echo "error: $*" >&2; exit 1; }
[[ $EUID -eq 0 ]] || die "run with sudo"

echo "==> installing docker"
if ! command -v docker >/dev/null; then
    apt-get update
    apt-get install -y ca-certificates curl
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
        > /etc/apt/sources.list.d/docker.list
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
fi
systemctl enable --now docker

echo "==> opening ports 80/443 on the VM"
# Oracle's Ubuntu images ship a REJECT-all INPUT chain, so ACCEPT rules must be inserted
# above it. GCP images leave INPUT open, where this is simply a no-op.
if iptables -S INPUT | grep -qE '^-A INPUT .*(REJECT|DROP)'; then
    for port in 80 443; do
        iptables -C INPUT -p tcp --dport "$port" -j ACCEPT 2>/dev/null \
            || iptables -I INPUT 6 -p tcp --dport "$port" -j ACCEPT
    done
    netfilter-persistent save 2>/dev/null \
        || { apt-get install -y iptables-persistent && netfilter-persistent save; }
else
    echo "    host firewall already open; nothing to do (normal on GCP)"
fi

# 1 GB shapes (GCP e2-micro, Oracle E2.1.Micro) need swap or the agent gets OOM-killed.
if [[ ! -f /swapfile ]] && [[ $(free -m | awk '/^Mem:/{print $2}') -lt 2048 ]]; then
    echo "==> adding 2G swap (low-memory VM)"
    fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
    grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "==> secret store at $SECRET_DIR"
install -d -m 0700 -o root -g root "$SECRET_DIR"
if [[ ! -f "$SECRET_DIR/env" ]]; then
    cat > "$SECRET_DIR/env" <<'ENV'
# Runtime secrets. Nothing here is baked into the image.
API_KEY=
BASE_URL=https://openrouter.ai/api/v1

# Exact origin of the deployed portfolio. No trailing slash, no path.
ALLOWED_ORIGINS=https://your-site.vercel.app

# Production Convex deployment that mints the JWTs this API verifies (the .site URL).
CONVEX_SITE_URL=https://your-prod.convex.site
ENV
    chmod 0600 "$SECRET_DIR/env"
    echo "    created $SECRET_DIR/env — fill it in, then re-run"
fi
if [[ ! -f "$SECRET_DIR/deploy.env" ]]; then
    cat > "$SECRET_DIR/deploy.env" <<'ENV'
DOMAIN=agent.example.com
IMAGE=ghcr.io/your-github-user/cc-mimic:latest
ENV
    chmod 0600 "$SECRET_DIR/deploy.env"
    echo "    created $SECRET_DIR/deploy.env — set DOMAIN and IMAGE, then re-run"
fi
if [[ ! -f "$SECRET_DIR/duckdns.env" ]]; then
    cat > "$SECRET_DIR/duckdns.env" <<'ENV'
# Optional but strongly recommended on GCP: keeps the DNS record correct after a
# stop/start, which otherwise hands the VM a new external IP. Delete this file to skip.
DUCKDNS_DOMAIN=
DUCKDNS_TOKEN=
ENV
    chmod 0600 "$SECRET_DIR/duckdns.env"
    echo "    created $SECRET_DIR/duckdns.env — fill in to survive a VM restart"
fi

grep -q '^API_KEY=.\+'   "$SECRET_DIR/env"        || die "set API_KEY in $SECRET_DIR/env"
grep -q '^DOMAIN=.\+'    "$SECRET_DIR/deploy.env" || die "set DOMAIN in $SECRET_DIR/deploy.env"
grep -q '^IMAGE=.\+'     "$SECRET_DIR/deploy.env" || die "set IMAGE in $SECRET_DIR/deploy.env"
grep -q '^DOMAIN=agent.example.com$' "$SECRET_DIR/deploy.env" && die "DOMAIN is still the placeholder"
grep -q 'your-github-user' "$SECRET_DIR/deploy.env" && die "IMAGE is still the placeholder"

# GCP releases an ephemeral external IP when the VM is STOPPED, so the box comes back on a
# different address and the DNS record goes stale. This re-reports the current IP to DuckDNS
# at boot and every 5 minutes, so a stop/start self-heals without a paid static IP.
if [[ -f "$SECRET_DIR/duckdns.env" ]]; then
    echo "==> installing DuckDNS updater"
    cat > /usr/local/bin/duckdns-update <<'UPD'
#!/usr/bin/env bash
set -euo pipefail
. /etc/cc-mimic/duckdns.env      # DUCKDNS_DOMAIN=<name-without-suffix>  DUCKDNS_TOKEN=<token>
# no ip= parameter: DuckDNS uses the source address of this request
curl -fsS "https://www.duckdns.org/update?domains=${DUCKDNS_DOMAIN}&token=${DUCKDNS_TOKEN}&ip="
UPD
    chmod 0755 /usr/local/bin/duckdns-update

    cat > /etc/systemd/system/duckdns.service <<'UNIT'
[Unit]
Description=Report this VM's current public IP to DuckDNS
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/duckdns-update
UNIT

    cat > /etc/systemd/system/duckdns.timer <<'UNIT'
[Unit]
Description=Keep the DuckDNS record pointed at this VM

[Timer]
OnBootSec=30s
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
UNIT
    systemctl daemon-reload
    systemctl enable --now duckdns.timer
    /usr/local/bin/duckdns-update && echo "    DuckDNS record updated"
else
    echo "    no $SECRET_DIR/duckdns.env — skipping DuckDNS updater"
    echo "    (without it, stopping the VM changes its IP and breaks the domain)"
fi

echo "==> installing compose files to $APP_DIR"
install -d -m 0755 "$APP_DIR"
install -m 0644 "$SRC_DIR/docker-compose.yml" "$SRC_DIR/Caddyfile" "$APP_DIR/"

# Pull-based auto-deploy: the VM polls the registry instead of CI pushing to the VM.
# No SSH key in GitHub, no inbound access, and it keeps working when the IP changes.
echo "==> installing auto-update timer"
cat > /usr/local/bin/cc-mimic-update <<'UPD'
#!/usr/bin/env bash
set -euo pipefail
cd /opt/cc-mimic
set -a; . /etc/cc-mimic/deploy.env; set +a
before=$(docker image inspect --format '{{.Id}}' "$IMAGE" 2>/dev/null || echo none)
docker compose pull --quiet
after=$(docker image inspect --format '{{.Id}}' "$IMAGE" 2>/dev/null || echo none)
if [[ "$before" != "$after" ]]; then
    echo "new image $after — restarting"
    docker compose up -d
    docker image prune -f
else
    echo "no change"
fi
UPD
chmod 0755 /usr/local/bin/cc-mimic-update

cat > /etc/systemd/system/cc-mimic-update.service <<'UNIT'
[Unit]
Description=Pull the latest cc-mimic image and restart if it changed
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/cc-mimic-update
UNIT

cat > /etc/systemd/system/cc-mimic-update.timer <<'UNIT'
[Unit]
Description=Check for a new cc-mimic image every 5 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload
systemctl enable --now cc-mimic-update.timer

echo "==> pulling and starting"
cd "$APP_DIR"
set -a; . "$SECRET_DIR/deploy.env"; set +a
docker compose pull
docker compose up -d

echo
echo "done. https://$(grep '^DOMAIN=' "$SECRET_DIR/deploy.env" | cut -d= -f2)"
echo
echo "Two things this script cannot do for you:"
echo "  1. Open TCP 80 and 443 in your cloud provider firewall:"
echo "     GCP    - gcloud compute firewall-rules create allow-http-https \\"
echo "                --allow=tcp:80,tcp:443 --target-tags=cc-mimic"
echo "     Oracle - console -> Networking -> VCN -> Security List -> ingress rules"
echo "  2. DNS: point an A record for your domain at this VM's public IP"
echo "     (Caddy needs it resolving before it can get a certificate)"
echo
echo "Auto-deploy is on: pushes to main rebuild the image in CI and this VM"
echo "picks it up within 5 minutes (systemctl list-timers cc-mimic-update.timer)."
