# Upload Hardening — Infrastructure Setup

`upload_security.py` (P5) implements everything that can run safely inside
the same process handling the upload: filename sanitization, magic-byte/
content validation, zip-bomb and PDF-bomb size/ratio guards, and a
pluggable malware-scanning interface. Two things are deliberately left to
infrastructure rather than attempted in-process:

## Malware scanning (ClamAV)

By default, `NoopMalwareScanner` runs — uploads pass through without being
scanned, with a warning logged once per process. To scan uploads for real:

1. Run a ClamAV daemon (`clamd`) reachable from the app. In Docker Compose,
   add a service:

   ```yaml
   clamav:
     image: clamav/clamav:stable
     restart: unless-stopped
     volumes:
       - clamav-data:/var/lib/clamav
     healthcheck:
       test: ["CMD", "clamdscan", "--version"]
       interval: 30s
       timeout: 10s
       retries: 5
       start_period: 90s  # first-run virus definition download is slow
   ```

   Add `clamav-data` to the top-level `volumes:` block, and add `clamav`
   to `web`'s `depends_on` if you want the app to wait for it.

2. Install the optional Python dependency:

   ```
   pip install clamd
   ```

   (or uncomment `clamd>=1.0.2` in `requirements-docker.txt`)

3. Set in `.env`:

   ```
   MALWARE_SCANNER=clamd
   CLAMD_HOST=clamav       # the Docker Compose service name above
   CLAMD_PORT=3310
   ```

If `clamd` is configured but unreachable at the time a scan is attempted,
`upload_security.get_malware_scanner()` logs an error and falls back to
the no-op scanner for that process rather than breaking uploads entirely —
monitor for that log line (`Failed to initialize clamd malware scanner`)
as a signal that scanning silently isn't happening.

Vercel/serverless: there is no persistent daemon to run ClamAV against in
that deployment path. Either scan uploads via an external API-based
scanning service (implement a new `MalwareScanner` subclass calling it)
or accept that the serverless deployment runs without malware scanning —
the other upload-hardening checks (magic bytes, zip/PDF bombs, filename
sanitization) still apply either way.

## Process-level sandboxing / CPU-timeout isolation

`upload_security.py`'s PDF/zip checks (page count, decompression ratio,
extracted-text size) catch the overwhelming majority of pathological
files, but they're still checks running inside the same process and
request that's doing the parsing — a sufficiently adversarial file that
passes those checks could still consume excessive CPU or memory during
`PdfReader`/`python-docx` parsing itself, and nothing in-process can
enforce a hard timeout on that (Python's `signal.alarm` only works on the
main thread; FastAPI's sync route handlers run in a worker thread pool).

Recommended mitigation: run document parsing in an isolated
worker/container with OS-level resource limits, so a runaway parse is
killed by the platform rather than hanging or OOMing the whole web
worker process:

- **Docker**: set `--memory` and `--cpus` limits on the container (or the
  equivalent `deploy.resources.limits` in `docker-compose.yml`) so a
  pathological parse degrades that one container, not the host.
- **Dedicated parsing worker**: move `extract_text_from_file()` calls to a
  separate worker process/container (e.g. behind a small internal queue)
  with its own tighter resource limits and a hard wall-clock timeout,
  rather than running parsing inline in the web request path. This is a
  larger architectural change than anything else in this hardening pass
  and is intentionally out of scope here — see
  `docs/architecture/ENTERPRISE_UPGRADE_PLAN.md` for where this would fit
  if pursued.
