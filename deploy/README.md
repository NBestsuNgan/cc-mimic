# Deploying cc-mimic to a free VM

Scope: this deploys **cc-mimic only**. The Next.js portfolio deploys to Vercel separately.

**For first-time setup, follow `portfolio/DEPLOY.md`** — it's a single ordered runbook
covering Convex, OAuth, Vercel and this VM (this part is steps 10–14). This page is the
reference for how it works and how to operate it, not the order to do it in.

## Architecture

Two independent paths: how a request reaches the agent, and how new code reaches the VM.
Nothing crosses between them, which is why neither GitHub nor Vercel holds a credential
for the VM.

### Request path, and where DNS fits

```mermaid
flowchart LR
    U["Visitor's browser"]
    V["Vercel<br>portfolio, Next.js"]
    D["DuckDNS<br>agent.example.duckdns.org"]

    subgraph VM["GCP e2-micro VM — ephemeral public IP"]
        direction TB
        C["caddy :80 / :443<br>Let's Encrypt TLS"]
        A["api :8000<br>uvicorn, 1 worker"]
        W[("workspace volume")]
        T["duckdns.timer<br>every 5 min"]
        C -->|"compose network only"| A
        A --- W
    end

    U -->|"1 · page load"| V
    V -->|"2 · HTML carrying NEXT_PUBLIC_API_URL"| U
    U -->|"3 · resolve that hostname"| D
    D -->|"4 · current VM IP"| U
    U -->|"5 · HTTPS + SSE stream"| C
    T -->|"re-reports the IP<br>after every stop/start"| D
```

Why DNS is load-bearing here: GCP hands the VM an **ephemeral** external IP and takes it
back whenever the instance is STOPPED. The A record would then point at an address that
is no longer yours. `duckdns.timer` re-reports the real IP every five minutes, so a
stop/start heals itself in about thirty seconds. That is also why the timer stayed at
five minutes when the image poll dropped to daily — it is fixing a different problem.

A hostname is not optional. Vercel serves the portfolio over HTTPS, and a browser refuses
to call `http://` from an `https://` page. Caddy needs a real name to get a certificate;
a bare IP cannot have one.

### Deploy path

```mermaid
flowchart LR
    L["laptop<br>git push main"]
    G["GitHub Actions · deploy.yml<br>pytest → build linux/amd64"]
    R[("ghcr.io/nbestsungan/cc-mimic<br>:latest and :sha")]

    subgraph VM["GCP VM"]
        direction TB
        T2["cc-mimic-update.timer<br>at boot, then once a day"]
        A2["api container"]
        T2 -->|"digest changed → compose up -d"| A2
    end

    L --> G
    G -->|"push, built-in GITHUB_TOKEN"| R
    R -.->|"outbound pull — no inbound port,<br>no SSH key, no GCP service account"| T2
```

The VM pulls; CI never pushes to the VM. That is the whole reason no service-account JSON
or SSH key exists anywhere in this repo, and why a changing IP breaks nothing about
deploys.

## What you need to do

```bash
# update command 
gcloud compute ssh cc-mimic --zone=us-central1-a --command 'sudo bash ~/deploy/update.sh'
```