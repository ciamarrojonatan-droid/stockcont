# Remote Tunnel & Mobile Monitoring Setup (`localhost:8501`)

This guide secures the local StockCont Dashboard Web SPA when accessed remotely from mobile devices or external workstations.

## 1. Enable Mutable Route Authentication

Generate a strong random token and add it to `.env`:

```env
DASHBOARD_ACCESS_TOKEN="replace-with-strong-32-char-random-secret"
ALERT_WEBHOOK_URL="https://discord.com/api/webhooks/..."
HEARTBEAT_PING_URL="https://hc-ping.com/<your-uuid>"
```

When `DASHBOARD_ACCESS_TOKEN` is set, every `POST`, `PUT`, `PATCH`, and `DELETE` call under `/api/*` requires either:

- `Authorization: Bearer <token>`
- `X-Dashboard-Token: <token>`

When `DASHBOARD_ACCESS_TOKEN` is left empty in local development, existing localhost workflows remain zero-friction.

## 2. Option A: Tailscale Serve / Funnel (Zero Port Forwarding)

1. Start the dashboard locally:
   ```powershell
   venv\Scripts\python.exe main.py --dashboard
   ```
2. Expose over your private encrypted Tailnet:
   ```powershell
   tailscale serve --bg http://127.0.0.1:8501
   ```

## 3. Option B: Cloudflare Zero Trust Tunnel (`cloudflared`)

1. Authenticate and create a named tunnel via Cloudflare Zero Trust.
2. Route your private hostname to `http://127.0.0.1:8501`:
   ```powershell
   cloudflared tunnel --url http://127.0.0.1:8501
   ```
3. Enforce Cloudflare Access policy (email OTP / GitHub SSO) in front of the tunnel in addition to `DASHBOARD_ACCESS_TOKEN`.
