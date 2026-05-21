"""Generate deterministic simulated data for 18650 Ladelogik.

The model is intentionally simple but plausible:
- TP4056-like current: high current below the upper range, taper near 4 V
- relay hysteresis: ON below 3.85 V, OFF above 4.00 V
- thermal inertia: temperature rises while charging and relaxes when idle
- PID reference controller: calculated for analysis, not used as charger output
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
PID_SETPOINT_V = (LOW_V + HIGH_V) / 2.0
PID_BIAS_PERCENT = 50.0
PID_KP = 850.0  # percent per volt
PID_KI = 2.4  # percent per volt-minute
PID_KD = 55.0  # percent-minute per volt
PID_INTEGRAL_LIMIT = 8.0  # volt-minutes
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
    pid_integral = 0.0
    previous_error = PID_SETPOINT_V - measured_voltage

    def clamp(value: float, low: float, high: float) -> float:
        return max(low, min(high, value))

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
        error_v = PID_SETPOINT_V - measured_voltage
        dt_min = DT_S / 60.0
        pid_integral = clamp(
            pid_integral + error_v * dt_min,
            -PID_INTEGRAL_LIMIT,
            PID_INTEGRAL_LIMIT,
        )
        derivative_v_per_min = (error_v - previous_error) / dt_min
        pid_p = PID_KP * error_v
        pid_i = PID_KI * pid_integral
        pid_d = PID_KD * derivative_v_per_min
        pid_raw = PID_BIAS_PERCENT + pid_p + pid_i + pid_d
        pid_output = clamp(pid_raw, 0.0, 100.0)
        pid_relay_request = 1 if pid_output >= 50.0 and temperature_c < TEMP_CUTOFF_C else 0
        previous_error = error_v

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
                "pid_setpoint_v": round(PID_SETPOINT_V, 4),
                "voltage_error_v": round(error_v, 4),
                "pid_integral_v_min": round(pid_integral, 4),
                "pid_bias_percent": round(PID_BIAS_PERCENT, 1),
                "pid_p_percent": round(pid_p, 2),
                "pid_i_percent": round(pid_i, 2),
                "pid_d_percent": round(pid_d, 2),
                "pid_raw_percent": round(pid_raw, 1),
                "pid_output_percent": round(pid_output, 1),
                "pid_relay_request": pid_relay_request,
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
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUT_FILE}")


if __name__ == "__main__":
    main()
