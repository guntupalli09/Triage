# Data Retention — Infrastructure Setup

`CONTRACT_RETENTION_DAYS` (see `.env.example`) configures *what* gets
deleted and *when* it's eligible, but does not, by itself, cause anything
to run. Actually deleting expired contracts on a schedule requires wiring
up one of the two mechanisms below — pick the one matching your deployment.

## Docker / self-hosted (cron, systemd timer, or Kubernetes CronJob)

Run `run_retention_cleanup.py` on a schedule. It connects to the same
database as the web process, deletes contracts past
`CONTRACT_RETENTION_DAYS`, and audit-logs each deletion
(`contract_auto_deleted`).

**crontab** (daily at 3am, adjust the path to match your deployment):

```
0 3 * * * cd /app && python run_retention_cleanup.py >> /var/log/triage-retention.log 2>&1
```

**systemd timer** — `/etc/systemd/system/triage-retention.service`:

```ini
[Unit]
Description=Triage Counsel contract retention cleanup

[Service]
Type=oneshot
WorkingDirectory=/app
EnvironmentFile=/app/.env
ExecStart=/usr/bin/python3 run_retention_cleanup.py
```

`/etc/systemd/system/triage-retention.timer`:

```ini
[Unit]
Description=Run Triage Counsel retention cleanup daily

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

**Kubernetes CronJob:**

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: triage-retention-cleanup
spec:
  schedule: "0 3 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: retention-cleanup
              image: <your-triage-image>
              command: ["python", "run_retention_cleanup.py"]
              envFrom:
                - secretRef:
                    name: triage-env
          restartPolicy: OnFailure
```

Test with `python run_retention_cleanup.py --dry-run` first — it reports
what would be deleted without deleting anything.

## Vercel / serverless (HTTP-triggered cron)

No persistent process to run a CLI script against. Instead, set
`CRON_SECRET` (a random secret — `openssl rand -hex 32`) and configure a
[Vercel Cron Job](https://vercel.com/docs/cron-jobs) to `POST
/internal/retention/cleanup` with `Authorization: Bearer <CRON_SECRET>`.
Without `CRON_SECRET` configured, that route always returns 404 — it does
not exist as an accessible, unauthenticated endpoint by default.

Add to `vercel.json`:

```json
{
  "crons": [
    { "path": "/internal/retention/cleanup", "schedule": "0 3 * * *" }
  ]
}
```

Vercel Cron Jobs send their own bearer token automatically when triggered
by the platform (see Vercel's cron docs for the current mechanism); set
`CRON_SECRET` to match what your Vercel project is configured to send, or
front the route with your own external scheduler (e.g. a GitHub Actions
workflow on a schedule, or any HTTP-capable cron service) that sends
`Authorization: Bearer <CRON_SECRET>` explicitly.

## Verifying it's working

Both paths write an audit log entry per run:
`retention_cleanup_run` (HTTP path) records `{"retention_days", "found",
"deleted", "errors"}` in `metadata_json`; the CLI path logs the same
summary to stdout/its log file. A `contract_auto_deleted` entry exists per
contract actually removed, distinguishable from the user-initiated
`contract_deleted` (P4) by `actor_user_id` being null (system action, not
something the owning user did) and `detail="retention_policy_expired"`.
