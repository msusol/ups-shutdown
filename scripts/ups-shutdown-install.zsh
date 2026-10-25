#!/usr/bin/env zsh
# Install the graceful-shutdown scripts, systemd unit and upsmon hooks.
# Run with: sudo zsh scripts/ups-shutdown-install.zsh
# Threshold lives in /etc/nut/ups-shutdown.env (THRESHOLD=40).
set -eu
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1 }

SRC=${0:A:h}
CONF=/etc/nut/upsmon.conf

install -m 0755 $SRC/ups-graceful-shutdown.zsh /usr/local/sbin/ups-graceful-shutdown
install -m 0755 $SRC/ups-battery-watch.zsh /usr/local/sbin/ups-battery-watch
install -m 0755 $SRC/ups-notify.zsh /usr/local/sbin/ups-notify

if [[ ! -e /etc/nut/ups-shutdown.env ]]; then
  cat > /etc/nut/ups-shutdown.env << ENV_EOF
UPS=${UPS_NAME:-ups}@localhost
THRESHOLD=40
POLL=10
ENV_EOF
  chown root:nut /etc/nut/ups-shutdown.env
  chmod 640 /etc/nut/ups-shutdown.env
fi

cat > /etc/systemd/system/ups-battery-watch.service << 'UNIT_EOF'
[Unit]
Description=Watch UPS battery charge and force shutdown at threshold
After=nut-server.service

[Service]
Type=simple
ExecStart=/usr/local/sbin/ups-battery-watch
UNIT_EOF

# upsmon runs ups-notify as user `nut`; allow exactly these two commands, nothing else
SUDOERS=/etc/sudoers.d/ups-notify
cat > $SUDOERS.tmp << 'SUDO_EOF'
nut ALL=(root) NOPASSWD: /usr/bin/systemctl start --no-block ups-battery-watch.service, /usr/bin/systemctl stop --no-block ups-battery-watch.service
SUDO_EOF
chmod 0440 $SUDOERS.tmp
visudo -cf $SUDOERS.tmp > /dev/null || { rm -f $SUDOERS.tmp; echo "sudoers check failed" >&2; exit 1 }
mv $SUDOERS.tmp $SUDOERS

[[ -e $CONF.pre-shutdown ]] || cp -a $CONF $CONF.pre-shutdown
sed -i '/^SHUTDOWNCMD/d' $CONF
if ! grep -q '^# ups-graceful-shutdown' $CONF; then
  cat >> $CONF << CONF_EOF

# ups-graceful-shutdown
SHUTDOWNCMD "/usr/local/sbin/ups-graceful-shutdown"
NOTIFYCMD /usr/local/sbin/ups-notify
NOTIFYFLAG ONBATT SYSLOG+EXEC
NOTIFYFLAG ONLINE SYSLOG+EXEC
CONF_EOF
fi

systemctl daemon-reload
systemctl restart nut-monitor.service
sleep 2
systemctl --no-pager --lines=0 status nut-monitor ups-battery-watch || true
echo "installed; threshold: $(grep '^THRESHOLD' /etc/nut/ups-shutdown.env)"
