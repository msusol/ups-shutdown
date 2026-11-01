#!/usr/bin/env zsh
# Log UPS state every INTERVAL seconds to a CSV, syncing each line so the log
# survives a power-off. Usage: zsh scripts/ups-log-discharge.zsh [outfile]
UPS=${UPS:-goldenmate@localhost}
INTERVAL=${INTERVAL:-5}
OUT=${1:-$HOME/ups-pull-test-$(date +%Y%m%d-%H%M%S).csv}
echo "timestamp,ups_status,battery_charge,battery_runtime,battery_voltage" >> $OUT
echo "logging to $OUT" >&2
while true; do
  v=(${(f)"$(upsc $UPS 2> /dev/null)"})
  st=${${(M)v:#ups.status:*}#*: }
  ch=${${(M)v:#battery.charge:*}#*: }
  rt=${${(M)v:#battery.runtime:*}#*: }
  vo=${${(M)v:#battery.voltage:*}#*: }
  echo "$(date +%FT%T),${st},${ch},${rt},${vo}" >> $OUT
  sync -d $OUT 2> /dev/null || sync
  sleep $INTERVAL
done
