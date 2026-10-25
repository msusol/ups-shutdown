# ups-shutdown

Graceful shutdown of an NVIDIA DGX Spark when a USB-attached UPS runs low on battery.
The UPS talks to the Spark over USB (HID), [Network UPS Tools](https://networkupstools.org/) (NUT)
reads it, and a small watcher stops all Docker containers and powers the machine off at a
battery-charge threshold (default 40%). Brand-agnostic by design (any `usbhid-ups`-supported
UPS works via the `VENDORID`/`PRODUCTID` overrides in `scripts/ups-nut-setup.zsh`); tested
against the hardware below.

## Hardware and software

- Goldenmate 1000VA/800W lithium UPS (LiFePO4, 230Wh, USB communication port) — the
  hardware this was built and tested against; other `usbhid-ups`-compatible UPS models
  should work with the vendor/product ID overrides
- NVIDIA DGX Spark, Ubuntu 24.04 (DGX OS), aarch64
- NUT 2.8.1 with the `usbhid-ups` driver (USB ID `06da:ffff` for the Goldenmate; override
  `VENDORID`/`PRODUCTID` for other hardware)

## How it works

1. `upsmon` (NUT) runs `ups-notify` when the UPS goes on battery or returns to mains.
2. On battery, `ups-battery-watch.service` polls `battery.charge` every 10 seconds.
3. At or below the threshold it runs `upsmon -c fsd`, and `upsmon` runs `ups-graceful-shutdown`.
4. `ups-graceful-shutdown` stops all Docker containers (30 s timeout), syncs, and runs `shutdown -h now`.

The UPS does not expose load or writable low-battery thresholds, so the policy uses
`battery.charge` rather than the drifting `battery.runtime` estimate.

## Quick start

Requires `sudo` on the Spark, with the UPS cabled to an open USB-C port (not the power-input port).

```zsh
sudo apt install nut nut-client nut-server
sudo zsh scripts/ups-nut-setup.zsh
sudo zsh scripts/ups-shutdown-install.zsh
upsc ups
```

Change the threshold in `/etc/nut/ups-shutdown.env` (`THRESHOLD=40`). Set `DRY_RUN=1` to run
`ups-graceful-shutdown` without acting.

## Layout

| Path | Purpose |
|---|---|
| `scripts/ups-nut-setup.zsh` | Configure NUT (standalone, `usbhid-ups`, localhost only, local monitor user) |
| `scripts/ups-shutdown-install.zsh` | Install the shutdown hooks and systemd watcher unit |
| `scripts/ups-battery-watch.zsh` | Poll charge on battery, force shutdown at the threshold |
| `scripts/ups-graceful-shutdown.zsh` | Stop Docker containers, sync, power off |
| `scripts/ups-notify.zsh` | `upsmon` NOTIFYCMD hook |
| `scripts/spark-power-log.zsh` | User service that logs GPU watts, CPU, and UPS state every 10 s (see `docs/process/spark-power-sampler.md`) |
| `scripts/spark-power-dashboard.py` | Builds a static HTML dashboard from the power-log CSVs and the NUT journal |
| `scripts/spark-power-dashboard-install.zsh` | Install the user units that rebuild the page every 10 min and serve it on the tailnet |
| `docs/process/dgx-spark-ups-setup.md` | Setup guide, baseline readings, troubleshooting |
| `docs/plans/dgx-spark-ups-graceful-shutdown.md` | Implementation plan and status |

See [docs/index.md](docs/index.md) for the full documentation set.

## Power dashboard

`python3 scripts/spark-power-dashboard.py --days 7 --open` charts GPU watts, CPU busy % and UPS
charge from the sampler's CSVs, shades any time the UPS was off mains, and lists on-battery
events from the NUT journal. It writes one self-contained page to
`~/.local/state/spark-power/dashboard.html`; see
[spark-power-sampler.md](docs/process/spark-power-sampler.md).

A live copy is served on the tailnet by `scripts/spark-power-dashboard-install.zsh`.

![Spark power dashboard: seven days of GPU watts, CPU busy % and UPS charge, with the 2026-10-13 on-battery blip listed](docs/images/spark-power-dashboard.jpg)

## Status

Setup, hooks, and a mains smoke test are done. The pull-the-plug test and the check that the
Spark powers back on after an outage are still open; see the
[plan](docs/plans/dgx-spark-ups-graceful-shutdown.md).

The scripts stop every running Docker container and power off the host. Review them before
installing, and test at a quiet moment.
