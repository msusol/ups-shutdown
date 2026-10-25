# Spark Power Sampler

## Prerequisites

- DGX Spark with the NUT setup from [dgx-spark-ups-setup.md](dgx-spark-ups-setup.md) (the sampler reads `upsc ups`).
- `nvidia-smi` available. `sudo` is not needed; the sampler is a systemd user service and linger is enabled.

## Why

The UPS shows load in watts on its front display but does not send it over USB, and the Spark
exposes no whole-system power sensor. The sampler logs what software can see (GPU watts, CPU
busy %, load average, UPS status and charge) every 10 seconds so a busy window such as the
06:00 pipeline can be compared against a quiet one. Pair it with manual readings from the UPS display.

## Steps

1. Install and start:

   ```zsh
   zsh scripts/spark-power-log-install.zsh
   ```

2. Read a day's log:

   ```zsh
   column -s, -t ~/.local/state/spark-power/spark-power-$(date +%F).csv | less -S
   ```

3. View it as charts (GPU watts, CPU %, UPS charge, red bands where the UPS left mains, plus the on-battery events from the NUT journal):

   ```zsh
   python3 scripts/spark-power-dashboard.py --days 7 --open
   ```

   It writes `~/.local/state/spark-power/dashboard.html`, a static page with no network use; regenerate it to refresh.

4. Manual readings: note the UPS display watts at about 05:55, 06:15, 06:40, and when the pipeline finishes, then compare with the CSV rows at those times.

## Expected output

One CSV per day in `~/.local/state/spark-power/` (about 0.5 MB/day, files older than 30 days are deleted) with columns
`timestamp,gpu_watts,gpu_util_pct,cpu_busy_pct,load1,ups_status,ups_charge`.
Idle baseline on 2026-09-25: GPU about 12 W, CPU about 2% busy, UPS display 63 W.

## Troubleshooting

- **Service not running:** `systemctl --user status spark-power-log.service` and `journalctl --user -u spark-power-log.service`.
- **Empty `gpu_watts`:** `nvidia-smi` failed; run it by hand.
- **Empty `ups_status`:** NUT is down; see the setup guide.
- Settings via environment: `INTERVAL` (seconds), `POWER_LOG_DIR`, `KEEP_DAYS`.

## Related docs

- [DGX Spark UPS setup](dgx-spark-ups-setup.md)
- [DGX Spark UPS graceful shutdown plan](../plans/dgx-spark-ups-graceful-shutdown.md)
