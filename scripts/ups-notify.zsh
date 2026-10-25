#!/usr/bin/env zsh
# upsmon NOTIFYCMD: start/stop the battery watcher on ONBATT/ONLINE.
# upsmon runs this as the unprivileged `nut` user, so a bare `systemctl start` is refused
# ("Interactive authentication required", seen 2026-10-13). sudo -n uses the narrow rule
# installed by ups-shutdown-install.zsh in /etc/sudoers.d/ups-notify.
case "$NOTIFYTYPE" in
  ONBATT) sudo -n /usr/bin/systemctl start --no-block ups-battery-watch.service ;;
  ONLINE) sudo -n /usr/bin/systemctl stop --no-block ups-battery-watch.service ;;
esac
