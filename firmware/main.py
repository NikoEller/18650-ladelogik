"""18650 Ladelogik for Raspberry Pi Pico.

The firmware supervises a finished TP4056 Li-Ion charger module:
- measure cell voltage/current with an INA219
- measure cell temperature with DS18B20 or NTC
- switch the TP4056 5 V input through a relay
- log measurements to CSV

It never generates a CC/CV charge profile. That job belongs to the TP4056.
"""

import math
import os
import time
from machine import ADC, I2C, Pin

import config as cfg
from ina219 import INA219


CSV_HEADER = (
    "timestamp,elapsed_s,cell_voltage_v,charge_current_mA,"
    "temperature_c,relay_state,soc_percent,mode,fault_reason\n"
)


class Relay:
    def __init__(self, pin_id, active_high=True):
        self.pin = Pin(pin_id, Pin.OUT)
        self.active_high = active_high
        self.set(False)

    def set(self, enabled):
        value = 1 if enabled else 0
        if not self.active_high:
            value = 1 - value
        self.pin.value(value)


class TemperatureReader:
    def __init__(self):
        self.sensor_type = cfg.TEMP_SENSOR_TYPE.upper()
        self.ds = None
        self.rom = None
        self.adc = None
        if self.sensor_type == "DS18B20":
            try:
                import ds18x20
                import onewire

                bus = onewire.OneWire(Pin(cfg.DS18B20_PIN))
                self.ds = ds18x20.DS18X20(bus)
                roms = self.ds.scan()
                if roms:
                    self.rom = roms[0]
            except Exception as exc:
                print("DS18B20 init failed:", exc)
        elif self.sensor_type == "NTC":
            self.adc = ADC(cfg.NTC_ADC_PIN)

    def read_c(self):
        if self.sensor_type == "DS18B20":
            if self.ds is None or self.rom is None:
                return None
            self.ds.convert_temp()
            time.sleep_ms(750)
            return float(self.ds.read_temp(self.rom))

        if self.sensor_type == "NTC":
            raw = self.adc.read_u16()
            if raw <= 0 or raw >= 65535:
                return None
            voltage_ratio = raw / 65535.0
            resistance = cfg.NTC_PULLUP_OHMS * voltage_ratio / (1.0 - voltage_ratio)
            inv_t = (
                1.0 / (cfg.NTC_NOMINAL_TEMP_C + 273.15)
                + math.log(resistance / cfg.NTC_NOMINAL_OHMS) / cfg.NTC_BETA
            )
            return (1.0 / inv_t) - 273.15

        return None


class OptionalDisplay:
    def __init__(self, i2c):
        self.display = None
        if not cfg.USE_OLED:
            return
        try:
            import ssd1306

            self.display = ssd1306.SSD1306_I2C(
                cfg.OLED_WIDTH, cfg.OLED_HEIGHT, i2c, addr=cfg.OLED_ADDRESS
            )
        except Exception as exc:
            print("OLED init failed:", exc)

    def show(self, voltage_v, current_ma, temp_c, relay_on, mode):
        if self.display is None:
            return
        self.display.fill(0)
        self.display.text("18650 Ladelogik", 0, 0)
        self.display.text("U:{:.3f} V".format(voltage_v), 0, 14)
        self.display.text("I:{:.0f} mA".format(current_ma), 0, 26)
        temp_text = "--" if temp_c is None else "{:.1f} C".format(temp_c)
        self.display.text("T:" + temp_text, 0, 38)
        self.display.text(("ON " if relay_on else "OFF ") + mode[:7], 0, 50)
        self.display.show()


def iso_timestamp():
    now = time.localtime()
    return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}".format(*now[:6])


def ensure_log_file(path):
    try:
        os.stat(path)
    except OSError:
        with open(path, "w") as handle:
            handle.write(CSV_HEADER)


def estimate_soc_percent(voltage_v):
    # Coarse open-circuit voltage lookup for a single Li-Ion cell. This is not
    # a fuel gauge, but it is good enough for a readable project log.
    table = (
        (2.90, 0),
        (3.20, 5),
        (3.45, 10),
        (3.62, 20),
        (3.74, 40),
        (3.85, 60),
        (3.94, 75),
        (4.05, 90),
        (4.17, 100),
    )
    if voltage_v <= table[0][0]:
        return table[0][1]
    for index in range(1, len(table)):
        v0, s0 = table[index - 1]
        v1, s1 = table[index]
        if voltage_v <= v1:
            fraction = (voltage_v - v0) / (v1 - v0)
            return s0 + fraction * (s1 - s0)
    return 100.0


def decide_relay(voltage_v, temp_c, relay_on, fault_latched, previous_fault):
    if cfg.REQUIRE_TEMP_SENSOR and temp_c is None:
        return False, True, "TEMP_SENSOR_MISSING"
    if temp_c is not None and temp_c >= cfg.TEMP_CUTOFF_C:
        return False, True, "TEMP_CUTOFF"
    if voltage_v >= cfg.OVERVOLTAGE_CUTOFF_V:
        return False, True, "OVERVOLTAGE"
    if voltage_v <= cfg.ABSOLUTE_MIN_CELL_V:
        return False, True, "CELL_UNDERVOLTAGE_INSPECTION_REQUIRED"
    if fault_latched:
        return False, True, previous_fault or "FAULT_LATCHED"

    if relay_on and voltage_v >= cfg.CHARGE_OFF_V:
        return False, False, ""
    if not relay_on and voltage_v <= cfg.CHARGE_ON_V:
        if temp_c is None or temp_c <= cfg.TEMP_RESUME_C:
            return True, False, ""
    return relay_on, False, ""


def log_row(path, elapsed_s, voltage_v, current_ma, temp_c, relay_on, soc, mode, fault):
    temp_text = "" if temp_c is None else "{:.2f}".format(temp_c)
    row = (
        "{},{},{:.4f},{:.1f},{},{},{:.1f},{},{}\n".format(
            iso_timestamp(),
            elapsed_s,
            voltage_v,
            current_ma,
            temp_text,
            1 if relay_on else 0,
            soc,
            mode,
            fault,
        )
    )
    with open(path, "a") as handle:
        handle.write(row)


def main():
    i2c = I2C(
        cfg.I2C_ID,
        sda=Pin(cfg.I2C_SDA_PIN),
        scl=Pin(cfg.I2C_SCL_PIN),
        freq=cfg.I2C_FREQ_HZ,
    )
    power = INA219(
        i2c,
        address=cfg.INA219_ADDRESS,
        shunt_ohms=cfg.INA219_SHUNT_OHMS,
        max_expected_amps=cfg.INA219_MAX_EXPECTED_A,
    )
    temp_reader = TemperatureReader()
    relay = Relay(cfg.RELAY_PIN, cfg.RELAY_ACTIVE_HIGH)
    display = OptionalDisplay(i2c)

    ensure_log_file(cfg.LOG_FILE)
    start_ms = time.ticks_ms()
    relay_on = False
    fault_latched = False
    fault_reason = ""

    while True:
        voltage_v = power.bus_voltage_v()
        current_ma = power.current_mA()
        if cfg.INVERT_CURRENT_SIGN:
            current_ma = -current_ma
        temp_c = temp_reader.read_c()

        relay_on, fault_latched, fault_reason = decide_relay(
            voltage_v, temp_c, relay_on, fault_latched, fault_reason
        )
        relay.set(relay_on)

        mode = "fault" if fault_latched else ("charging" if relay_on else "idle")
        soc = estimate_soc_percent(voltage_v)
        elapsed_s = time.ticks_diff(time.ticks_ms(), start_ms) // 1000
        log_row(
            cfg.LOG_FILE,
            elapsed_s,
            voltage_v,
            current_ma,
            temp_c,
            relay_on,
            soc,
            mode,
            fault_reason,
        )

        if cfg.STATUS_PRINT:
            temp_text = "--" if temp_c is None else "{:.1f}".format(temp_c)
            print(
                "t={}s U={:.3f}V I={:.0f}mA T={}C relay={} mode={} fault={}".format(
                    elapsed_s,
                    voltage_v,
                    current_ma,
                    temp_text,
                    1 if relay_on else 0,
                    mode,
                    fault_reason or "-",
                )
            )
        display.show(voltage_v, current_ma, temp_c, relay_on, mode)
        time.sleep(cfg.SAMPLE_INTERVAL_S)


if __name__ == "__main__":
    main()
