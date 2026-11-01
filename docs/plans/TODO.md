# TODO

## DGX Spark UPS graceful shutdown

Plan: [dgx-spark-ups-graceful-shutdown.md](dgx-spark-ups-graceful-shutdown.md)

- [ ] Phase 0: verify premises (cable UPS, VID:PID, port/cable, power draw)
- [x] Phase 1: NUT install and driver
- [x] Phase 2: monitoring config
- [ ] Phase 3: battery-based shutdown policy
- [ ] Phase 4: test
- [ ] Phase 5: docs and alerting (process doc done; optional alerts open)
- [ ] Phase 6: job-aware shutdown (`ups-wait-for-mains`, stop CLP jobs before Docker); see the CLP plan `2026-09-25-ups-graceful-job-shutdown.md`

## Next steps

### DGX Spark UPS graceful shutdown

1. Phase 4: staged pull-the-plug test (preflight, short run at `THRESHOLD=95`, recovery, full-depth run at 40%); not near the 06:00 pipeline; expect manual power-on after mains returns (see the plan).
