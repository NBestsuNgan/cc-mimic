# Deploying cc-mimic to a free VM

Scope: this deploys **cc-mimic only**. The Next.js portfolio deploys to Vercel separately.

**For the step-by-step deploy, follow `portfolio/DEPLOY.md`** — it's a single ordered
runbook covering Convex, OAuth, Vercel and this VM (this part is steps 10–14). The pages
below are the reference for how it works, not the order to do it in.

## What you need first

1. A Debian/Ubuntu VM with a public IP. A GCP Always Free `e2-micro` or an Oracle
   Always Free instance both work; `vm-setup.sh` handles either.
2. **A domain name pointing at the VM.** This is not optional. Vercel serves the portfolio
   over HTTPS, and a browser refuses to call `http://` from an `https://` page (mixed
   content). Caddy needs a real hostname to get a Let's Encrypt certificate; an IP alone
   cannot get one. A free subdomain from DuckDNS or similar is fine.

## Steps

### 1. Open the ports in the Oracle console

Oracle blocks everything by default in **two** places, and the script can only fix one.

- Console → Networking → Virtual Cloud Networks → your VCN → Security Lists → default
- Add **Ingress Rules**: source `0.0.0.0/0`, IP protocol TCP, destination port `80`, then
  another for `443`.

The script handles the second place (the VM's own iptables REJECT rule).

### 2. Point DNS at the VM

Create an `A` record for e.g. `agent.yourdomain.com` → the VM's public IP. Confirm with
`dig +short agent.yourdomain.com` before continuing; Caddy's certificate request fails if
the name doesn't resolve yet.

### 3. Build the image locally, then bootstrap the VM

The VM never compiles anything — it pulls a prebuilt image.

```bash
cd cc-mimic
PLATFORM=linux/amd64 IMAGE=ghcr.io/<you>/cc-mimic:latest bash deploy/build-push.sh
scp -r deploy <user>@<VM_IP>:~/deploy                            # compose + Caddyfile only
ssh <user>@<VM_IP> 'sudo bash ~/deploy/vm-setup.sh'
```

`<you>` must be lowercase even if your GitHub username is not — ghcr rejects
any uppercase in an image path.

The first run creates two root-owned `0600` files and stops, so you can fill them in:

- `/etc/cc-mimic/env` — `API_KEY`, `BASE_URL`, `ALLOWED_ORIGINS`, `CONVEX_SITE_URL`
- `/etc/cc-mimic/deploy.env` — `DOMAIN`, `IMAGE`

Edit both with `sudo nano`, then run the script again. It builds and starts the container.

### 4. Point the portfolio at it

In the Vercel project settings, set:

```
NEXT_PUBLIC_API_URL = https://agent.yourdomain.com
```

and put that same Vercel URL in `ALLOWED_ORIGINS` on the VM (exact origin, no trailing
slash), then `sudo bash deploy/update.sh`.

## How secrets are handled

- `.env` is in `.dockerignore` — the API key is **never** baked into the image, which is
  what makes it safe to push the image to a public registry.
- The key lives only in `/etc/cc-mimic/env`, owned by root, mode `0600`, injected at
  container start via compose `env_file`.
- Only `deploy/` is copied to the server — no application source and no `.env`, so your
  laptop's development secrets never reach it.
- The agent can run shell commands. `src/tools/builtin/shell.py` strips `*KEY*`,
  `*SECRET*`, `*PASSWORD*` and `*TOKEN*` from the environment it passes to subprocesses,
  so a tool call running `env` does not see `API_KEY`.
- The container runs as uid 10001, `/srv` is not writable, and `no-new-privileges` is set.
  Only the workspace volume can be written to.
- Port 8000 is `expose`d, not `ports:`-published — it is reachable only from Caddy inside
  the compose network, never directly from the internet.

## Operating the VM

### Stopping / restarting the VM

Almost nothing is lost. The boot disk is a **persistent disk**, so everything on it comes
back: Docker images, the `workspace` volume (all users' files and their
`.ai-agent/config.toml`), Caddy's `caddy_data` volume with the TLS certificate, and
`/etc/cc-mimic/*`. `restart: unless-stopped` brings both containers up on boot.

Two things do not survive:

| Lost on stop | Why | Impact |
|---|---|---|
| **The external IP** | GCP releases an *ephemeral* IP when the VM is STOPPED (a reboot keeps it). You get a different one on start. | DNS points at the old address → the site is unreachable and Caddy can't renew its certificate. **This is the one that bites.** |
| **Live conversations** | Sessions are held in the API process's memory | Users start a new conversation. Their files and transcripts are on disk and still listed. |

Note the distinction: **reboot** keeps the IP, **stop → start** does not.

Two ways to handle the IP:

**A. DuckDNS auto-updater (free, already installed).** `vm-setup.sh` installs a systemd
timer that re-reports the VM's current IP to DuckDNS at boot and every 5 minutes, so a
stop/start heals itself within ~30 seconds. Enable it by filling in:

```bash
sudo nano /etc/cc-mimic/duckdns.env
```

```ini
DUCKDNS_DOMAIN=<duckdns-name>      # the name only, no .duckdns.org
DUCKDNS_TOKEN=<token from duckdns.org>
```

then `sudo bash ~/deploy/vm-setup.sh`. Check it with:

```bash
systemctl status duckdns.timer
sudo /usr/local/bin/duckdns-update    # prints OK
```

**B. Reserve a static IP.** GCP charges for **both** static and ephemeral external IPs, so
this adds little or nothing over what you already pay:

```bash
gcloud compute addresses create cc-mimic-ip --region=us-central1
gcloud compute instances delete-access-config cc-mimic --zone=<GCP_ZONE> \
  --access-config-name="External NAT"
gcloud compute instances add-access-config cc-mimic --zone=<GCP_ZONE> \
  --access-config-name="External NAT" --address=<the reserved IP>
```

A reserved IP that is **not** attached to a running instance is billed at a higher rate —
so if you ever delete the VM, release the address too.

### If you delete the VM (not just stop it)

Then yes, everything goes: disk, volumes, workspaces, certificates, `/etc/cc-mimic`.
Rebuilding is steps 9, 10, 13, 14 — about ten minutes, because the image lives in the
registry and nothing but configuration lives on the box. Users lose their workspace files.

### Routine checks

```bash
gcloud compute ssh cc-mimic --zone=<GCP_ZONE>
cd /opt/cc-mimic
sudo docker compose ps                 # both containers Up
sudo docker compose logs -f api        # tail the API
df -h /                                # disk (30 GB; workspaces are never pruned)
free -m                                # 1 GB + 2 GB swap
```

Workspaces accumulate forever. To clear old ones:

```bash
sudo docker run --rm -v cc-mimic_workspace:/w alpine \
  sh -c 'find /w -maxdepth 2 -mindepth 2 -type d -mtime +30 -exec rm -rf {} +'
```


## Auto-deploy

`.github/workflows/deploy.yml` runs `test_app.py`, builds `linux/amd64` and pushes to
ghcr on every push to `main`. No secrets — the built-in `GITHUB_TOKEN` can push to the
repo's own package.

The VM pulls rather than CI pushing: `cc-mimic-update.timer` runs at boot and once a
day, does `docker compose pull`, and restarts only if the image digest changed. No SSH
key in GitHub, no inbound access, and it survives the VM's IP changing.

A daily poll costs almost nothing but means a push can sit unshipped for up to a day, so
treat the timer as the safety net and deploy on purpose when you want the change live:

```bash
gcloud compute ssh <VM_NAME> --zone=<GCP_ZONE> --command 'sudo /usr/local/bin/cc-mimic-update'
```

`systemctl list-timers cc-mimic-update.timer` and `journalctl -u cc-mimic-update -n 20`
show its state.

> A restart drops every live conversation — sessions are in memory. Files and transcripts
> are on disk and survive. Avoid pushing while someone is mid-demo.

## Known limits

- **One worker only.** Sessions live in the API process's memory, so `--workers 1` is
  mandatory and a restart drops every live conversation.
- **Sessions are never evicted** — memory grows with each new chat. Restart periodically.
- **Workspaces persist** in the `workspace` volume and are never pruned automatically.
- **Command approval is a denylist.** `ApprovalPolicy.NEVER` auto-approves anything in
  `SAFE_PATTERNS` that isn't caught by `DANGEROUS_PATTERNS`. The escape vectors found so
  far (`find -exec`, `awk system()`, `sed -i`, `sort --compress-program`, inline
  interpreters) are blocked and covered by `test_app.py`, but pattern-matching shell
  commands is not a security boundary — the container is. It runs as uid 10001 with a
  read-only `/srv` and `no-new-privileges`.
