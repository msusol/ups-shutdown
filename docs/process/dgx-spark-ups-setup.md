# DGX Spark UPS Setup and Graceful Shutdown

## Prerequisites

- Goldenmate 1000VA Lithium UPS with USB communication cable to an open Spark USB-C port (not the marked power-input port).
- DGX Spark on Ubuntu 24.04 with `sudo` access; the Spark plugged into a battery-backed UPS outlet.
- `lsusb` shows `06da:ffff Phoenixtec Power Co., Ltd Smart-Battery`.

## Steps

1. Install NUT:

   ```zsh
   sudo apt install nut nut-client nut-server
   ```

2. Configure NUT (standalone, `usbhid-ups` driver, localhost-only, local monitor user):

   ```zsh
   sudo zsh scripts/ups-nut-setup.zsh
   ```

3. Install the shutdown hooks (default threshold 40% battery charge):

   ```zsh
   sudo zsh scripts/ups-shutdown-install.zsh
   ```

4. Verify readings and the watcher:

   ```zsh
   upsc ups
   sudo systemctl start ups-battery-watch.service
   journalctl -t ups-watch -n 5 --no-pager
   ```

5. Change the threshold by editing `THRESHOLD` in `/etc/nut/ups-shutdown.env`; no restart needed (read on each watcher start).

## How it works

- `upsmon` runs `/usr/local/sbin/ups-notify` on ONBATT/ONLINE, which starts/stops `ups-battery-watch.service`.
- The watcher polls `battery.charge` every `POLL` seconds; at or below `THRESHOLD` it runs `upsmon -c fsd`.
- `upsmon` then runs `SHUTDOWNCMD` (`/usr/local/sbin/ups-graceful-shutdown`): stop all Docker containers (30 s timeout), `sync`, `shutdown -h now`. The UPS's own low-battery flag takes the same path.
- Set `DRY_RUN=1` to run the shutdown script without acting.

## Expected output

`upsc ups` reports `battery.charge`, `battery.runtime`, `ups.status: OL` on mains.

### Baseline (measured 2026-09-25, on mains)

Conditions: Spark idle-ish (GPU 2% util, 12 W GPU draw, load average about 0.6, 9 Docker containers running), UPS at full charge.

`lsusb`:

```text
Bus 001 Device 002: ID 06da:ffff Phoenixtec Power Co., Ltd Smart-Battery
```

`upsc ups` (key values):

| Variable | Value | Note |
|---|---|---|
| `ups.status` | `OL` | on line (mains). Expect `OB` on battery, `LB` when low |
| `battery.charge` | `100` | percent; the value the shutdown policy uses |
| `battery.runtime` | `9720`, `11400`, `11280` s | three readings over about 5 minutes, all idle on mains; firmware estimate that drifts, do not rely on it |
| `battery.voltage` | `13.20` | V |
| `battery.type` | `Lion` | reported string; the product is sold as LiFePO4 |
| `device.mfr` / `device.model` | `-BMS-` / `Smart-Battery` | generic BMS strings, not a brand name |
| `driver.name` | `usbhid-ups` | data table Phoenixtec/Liebert HID 0.41 |
| `ups.delay.shutdown` / `ups.delay.start` | `20` / `30` s | the only writable variables |

Not reported by this UPS: `ups.load`, `battery.charge.low`, `battery.runtime.low`, input voltage. Available instant commands: `load.off`, `load.on`, `load.off.delay`, `load.on.delay`, `driver.killpower` (locked by `driver.flag.allow_killpower=0`).

**Real whole-load wattage (read from the UPS's own front display, not
NUT — since `ups.load` isn't exposed over USB, this is the only whole-
circuit figure available): ~60 W idling**, with everything on the same
desk circuit plugged in — router, LED lights, an HV switch, and laptop
chargers, in addition to the DGX Spark itself. `spark-power-log`'s
GPU-only sampling (see
[spark-power-sampler.md](spark-power-sampler.md)) shows ~11-12 W GPU
draw over the same idle period, confirming the GPU is a small fraction
of the ~60 W total — most of that idle load is the rest of the desk's
devices, not the Spark's GPU.

Expected services after setup: `nut-driver@ups`, `nut-server`, `nut-monitor` active; `ups-battery-watch.service` inactive while on mains.

Not yet measured: charge-vs-time on battery, time from 40% to the Spark powering off, and whether the Spark powers back on after mains returns. Record those here after the pull-the-plug test (plan Phase 4).

## Troubleshooting

- **Watcher never starts on battery ("Interactive authentication required" in `journalctl -u nut-monitor`):** `upsmon` runs `ups-notify` as user `nut`, which cannot `systemctl start` without a rule. `ups-shutdown-install.zsh` installs `/etc/sudoers.d/ups-notify` (exactly the start/stop of `ups-battery-watch.service`); re-run it if that file is missing. Test: `sudo -u nut sudo -n /usr/bin/systemctl start --no-block ups-battery-watch.service`, then `journalctl -t ups-watch` shows "on battery; watching" and, on mains, "back on mains" (the unit exits at once, so `is-active` reads inactive).
- **Watcher fails immediately:** check `journalctl -u ups-battery-watch.service`. zsh reserves names such as `status`; do not use them as variables.
- **`nut-scanner -U` reports `Cannot load USB library (libusb-1.0.so)`:** install `libusb-1.0-0-dev` (provides the unversioned symlink), then run the scan with `sudo`; without root it reports "Access denied". The scanner is optional: the udev rules already list `06da:ffff` for `usbhid-ups`.
- **`battery.runtime` looks wrong:** it is a firmware estimate that drifts; the policy uses `battery.charge`.
- **Spark stays off after an outage:** check firmware/BIOS power-restore behavior (see the plan's Phase 4).

## Related docs

- [DGX Spark UPS graceful shutdown plan](../plans/dgx-spark-ups-graceful-shutdown.md)
