# Production Docker Cleanup

Automated weekly cleanup of unused Docker resources. Safe for production — never touches running containers, their images, or any named volumes.

## Setup on Hetzner VPS

```bash
# 1. Copy the script
sudo cp ops/scripts/docker-cleanup.sh /opt/scripts/docker-cleanup.sh
sudo chmod +x /opt/scripts/docker-cleanup.sh

# 2. Install logrotate config
sudo cp ops/logrotate/docker-cleanup /etc/logrotate.d/docker-cleanup

# 3. Install cron job (runs every Sunday at 3:00 AM)
(crontab -l 2>/dev/null | grep -v docker-cleanup; echo "0 3 * * 0 /opt/scripts/docker-cleanup.sh") | crontab -

# 4. Create log file
sudo touch /var/log/docker-cleanup.log
```

## Verification

```bash
# Confirm cron is installed
crontab -l | grep docker-cleanup

# Confirm script is executable
ls -la /opt/scripts/docker-cleanup.sh

# Dry-run the script
sudo /opt/scripts/docker-cleanup.sh

# Check logs
tail -50 /var/log/docker-cleanup.log

# Confirm running containers are still up
docker ps

# Confirm volumes are intact
docker volume ls
```

## What gets cleaned

- Stopped containers
- Dangling and unused images (not used by running containers)
- Dangling and unused build cache
- Unused networks

## What is NEVER touched

- Running containers
- Images used by running containers
- Named volumes (PostgreSQL, Redis, etc.)
- Production traffic
