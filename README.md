# Discord WatchBot

Discord WatchBot is a Discord bot for homelab operations. It provides:

- system health/status checks (CPU, RAM, disks)
- power control (wake up + remote power off)
- Docker service auto-healing with crash-loop protection
- webhook-based security/system alerts pushed to Discord

## Features

- `status` slash command for live host metrics
- `wake_up` slash command using Wake-on-LAN
- `power_off` slash command over SSH
- `tracking` slash command for interactive Docker service monitoring
- automatic restart attempts for monitored containers
- crash-loop detection and cooldown locks
- hourly threshold alerts for CPU, RAM, and disk usage
- built-in HTTP alert receiver at `POST /alert` on port `5000`

## Project Structure

- `main.py` - bot startup, cog loading, Discord command sync
- `cogs/monitor_bot.py` - status command + periodic system threshold checks
- `cogs/power_manager.py` - wake and shutdown controls + host online checks
- `cogs/watch_bot.py` - Docker tracking dashboard + auto-heal loop
- `cogs/alert.py` - webhook endpoint that forwards alerts to Discord channels
- `config.json` - monitored system disks + CPU/RAM thresholds
- `monitored_services.json` - persisted list of Docker services under auto-heal

## Requirements

- Python 3.11+ (project Dockerfile uses Python 3.12)
- A Discord bot token
- Bot invited with needed permissions/intents
- Network access to your homelab host
- SSH access for remote shutdown command
- Docker Engine access (local socket and/or remote Docker over SSH)

## Environment Variables

Create a `.env` file in the project root:

```env
DISCORD_TOKEN=your_discord_bot_token
MY_GUILD_ID=your_test_or_main_guild_id
ADMIN_ID=your_discord_user_id

NOTIFICATION_CHANNEL_ID=channel_id_for_general_alerts
FAIL2BAN_CHANNEL_ID=channel_id_for_fail2ban_alerts
REVERSE_SHELL_MONITOR_CHANNEL_ID=channel_id_for_reverse_shell_alerts

LAB_IP=homelab_host_ip
SSH_USER=ssh_username
BROADCAST_IP=wol_broadcast_ip
LAB_MAC=homelab_mac_address
```

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

## Docker Setup

The provided setup mounts:

- project directory to `/app`
- host SSH keys to `/mnt/.ssh` (copied in `entrypoint.sh`)
- Docker socket to `/var/run/docker.sock`

Start with:

```bash
docker compose up -d --build
```

## Slash Commands

- `/status` - shows host OS, CPU, RAM, and disk usage bars
- `/wake_up` - sends Wake-on-LAN packet (admin only)
- `/power_off` - runs remote `sudo poweroff` over SSH (admin only)
- `/tracking` - opens interactive service monitoring/auto-heal dashboard (admin only)

## Alert Webhook

`cogs/alert.py` runs an HTTP server on port `5000` and accepts:

- `POST /alert`
- JSON body:

```json
{
  "type": "Fail2Ban Alert",
  "message": "Blocked IP 1.2.3.4",
  "status": "warning",
  "to_channel": "fail2ban"
}
```

Supported `to_channel` values:

- `fail2ban`
- `reverse_shell_monitor`

Supported `status` values:

- `error`
- `warning`
- `success`
- any other value defaults to informational embed

## Configuration

Edit `config.json` to tune thresholds:

- `system.cpu_threshold`
- `system.ram_threshold`
- `disks[].threshold`

Example:

```json
{
  "disks": [
    { "name": "Root (/)", "path": "/", "threshold": 90 }
  ],
  "system": {
    "cpu_threshold": 90,
    "ram_threshold": 85
  }
}
```

## Notes

- `monitored_services.json` is auto-created if missing.
- Discord command sync is performed for `MY_GUILD_ID` during startup.
- Ensure your bot has message/content and application command permissions.