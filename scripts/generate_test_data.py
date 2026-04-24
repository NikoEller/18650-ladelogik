"""Generate deterministic simulated charge supervision data.

The model is intentionally simple but plausible:
- TP4056-like current: high current below the upper range, taper near 4 V
- relay hysteresis: ON below 3.85 V, OFF above 4.00 V
- thermal inertia: temperature rises while charging and relaxes when idle
"""

from __future__ import annotations

import csv
import math
import random
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_FILE = ROOT / "data" / "simulated_charge_log.csv"

LOW_V = 3.85
HIGH_V = 4.00
TEMP_CUTOFF_C = 45.0
CAPACITY_AH = 2.6
DT_S = 60
TOTAL_HOURS = 12


def ocv_from_soc(soc_percent: float) -> float:
    points = [
        (0, 2.90),
        (5, 3.20),
        (10, 3.45),
        (20, 3.62),
        (40, 3.74),
        (60, 3.85),
        (75, 3.94),
        (90, 4.05),
        (100, 4.17),
    ]
    if soc_percent <= points[0][0]:
        return points[0][1]
    for (s0, v0), (s1, v1) in zip(points, points[1:]):
        if soc_percent <= s1:
            ratio = (soc_percent - s0) / (s1 - s0)
            return v0 + ratio * (v1 - v0)
    return points[-1][1]


def simulate() -> list[dict[str, object]]:
    rng = random.Random(18650)
    start = datetime(2026, 4, 24, 9, 0, 0)
    soc = 47.0
    relay = False
    temperature_c = 23.4
    ambient_c = 22.8
    rows: list[dict[str, object]] = []
    measured_voltage = ocv_from_soc(soc)

    for index in range(int(TOTAL_HOURS * 3600 / DT_S) + 1):
        timestamp = start + timedelta(seconds=index * DT_S)

        if relay and measured_voltage >= HIGH_V:
            relay = False
        elif not relay and measured_voltage <= LOW_V:
            relay = True

        ocv = ocv_from_soc(soc)
        if relay:
            taper = min(1.0, max(0.12, (4.07 - measured_voltage) / 0.28))
            charge_current_ma = 930.0 * taper + rng.gauss(0, 16)
            charge_current_ma = max(120.0, min(980.0, charge_current_ma))
            current_a = charge_current_ma / 1000.0
            soc += current_a * DT_S / 3600.0 / CAPACITY_AH * 100.0 * 0.94
            terminal_lift = 0.035 + 0.055 * taper
            thermal_target = ambient_c + 7.4 * taper
            mode = "charging"
        else:
            load_ma = 55.0 + 8.0 * math.sin(index / 40.0)
            charge_current_ma = max(0.0, rng.gauss(2.0, 2.5))
            soc -= load_ma / 1000.0 * DT_S / 3600.0 / CAPACITY_AH * 100.0
            terminal_lift = -0.006
            thermal_target = ambient_c + 0.6
            mode = "idle"

        soc = max(0.0, min(100.0, soc))
        temperature_c += (thermal_target - temperature_c) * 0.045 + rng.gauss(0, 0.045)
        ambient_c = 22.8 + 0.7 * math.sin(index / 130.0)
        measured_voltage = ocv_from_soc(soc) + terminal_lift + rng.gauss(0, 0.004)
        measured_voltage = max(2.75, min(4.18, measured_voltage))

        rows.append(
            {
                "timestamp": timestamp.isoformat(timespec="seconds"),
                "elapsed_min": round(index * DT_S / 60.0, 1),
                "cell_voltage_v": round(measured_voltage, 4),
                "charge_current_mA": round(charge_current_ma, 1),
                "temperature_c": round(temperature_c, 2),
                "relay_state": 1 if relay else 0,
                "soc_percent": round(soc, 1),
                "setpoint_low_v": LOW_V,
                "setpoint_high_v": HIGH_V,
                "temperature_cutoff_c": TEMP_CUTOFF_C,
                "mode": mode,
                "fault_reason": "",
            }
        )

    return rows


def main() -> None:
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    rows = simulate()
    with OUT_FILE.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUT_FILE}")


if __name__ == "__main__":
    main()

