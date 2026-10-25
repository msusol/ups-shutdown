#!/usr/bin/env zsh
# Install the dashboard as systemd user units (no sudo needed; linger is already enabled):
#   spark-power-dashboard.timer     rebuilds the page every 10 minutes
#   spark-power-dashboard-web.service  serves it on the tailnet at http://<tailscale-ip>:8765/
set -eu
SRC=${0:A:h}
mkdir -p ~/.config/systemd/user
cp $SRC/spark-power-dashboard.service $SRC/spark-power-dashboard.timer $SRC/spark-power-dashboard-web.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user start spark-power-dashboard.service
systemctl --user enable --now spark-power-dashboard.timer spark-power-dashboard-web.service
sleep 3
systemctl --user --no-pager --lines=0 status spark-power-dashboard-web.service || true
systemctl --user list-timers --no-pager spark-power-dashboard.timer
bind=$(systemctl --user show spark-power-dashboard-web.service -p Environment --value | tr ' ' '\n' | sed -n 's/^DASH_BIND=//p')
port=$(systemctl --user show spark-power-dashboard-web.service -p Environment --value | tr ' ' '\n' | sed -n 's/^DASH_PORT=//p')
curl -s -o /dev/null -w "page: http://${bind}:${port}/  ->  HTTP %{http_code}\n" --max-time 5 http://${bind}:${port}/
