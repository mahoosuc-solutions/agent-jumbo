#!/bin/bash

echo "Running initialization script..."

# branch from parameter
if [ -z "$1" ]; then
    echo "Error: Branch parameter is empty. Please provide a valid branch name."
    exit 1
fi
BRANCH="$1"

if [ -f /aj/.env ]; then
    ENV_RUN_MODE=$(grep -E '^[[:space:]]*AGENT_MAHOO_RUN_MODE=' /aj/.env | tail -n 1 | cut -d= -f2- | tr -d '"' | tr -d "'")
    ENV_LAPTOP_MODE=$(grep -E '^[[:space:]]*AGENT_MAHOO_LAPTOP_MODE=' /aj/.env | tail -n 1 | cut -d= -f2- | tr -d '"' | tr -d "'")
    if [ -n "$ENV_RUN_MODE" ]; then
        export AGENT_MAHOO_RUN_MODE="$ENV_RUN_MODE"
    elif [ "${ENV_LAPTOP_MODE,,}" = "true" ] || [ "${ENV_LAPTOP_MODE}" = "1" ] || [ "${ENV_LAPTOP_MODE,,}" = "yes" ] || [ "${ENV_LAPTOP_MODE,,}" = "on" ]; then
        export AGENT_MAHOO_RUN_MODE="local-lite"
    fi
fi

# Copy all contents from persistent /per to root directory (/) without overwriting
cp -r --no-preserve=ownership,mode /per/* /

# allow execution of /root/.bashrc and /root/.profile
chmod 444 /root/.bashrc
chmod 444 /root/.profile

# update package list to save time later
apt-get update > /dev/null 2>&1 &

case "${AGENT_MAHOO_RUN_MODE:-full}" in
    local-lite)
        export RUN_UI_AUTOSTART=true
        export RUN_SEARXNG_AUTOSTART=false
        export RUN_CRON_AUTOSTART=false
        export RUN_SSHD_AUTOSTART=false
        export RUN_TUNNEL_API_AUTOSTART=false
        ;;
    research)
        export RUN_UI_AUTOSTART=true
        export RUN_SEARXNG_AUTOSTART=true
        export RUN_CRON_AUTOSTART=false
        export RUN_SSHD_AUTOSTART=false
        export RUN_TUNNEL_API_AUTOSTART=false
        ;;
    *)
        export RUN_UI_AUTOSTART=true
        export RUN_SEARXNG_AUTOSTART=true
        export RUN_CRON_AUTOSTART=true
        export RUN_SSHD_AUTOSTART=true
        export RUN_TUNNEL_API_AUTOSTART=true
        ;;
esac

# let supervisord handle the services
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
