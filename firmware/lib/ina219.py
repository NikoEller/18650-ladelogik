"""Small INA219 driver for MicroPython.

The calibration defaults are suitable for common INA219 modules with a
0.1 ohm shunt and currents around the TP4056 range.
"""

from micropython import const


_REG_CONFIG = const(0x00)
_REG_SHUNT_VOLTAGE = const(0x01)
_REG_BUS_VOLTAGE = const(0x02)
_REG_POWER = const(0x03)
_REG_CURRENT = const(0x04)
_REG_CALIBRATION = const(0x05)


class INA219:
    """INA219 high-side current and bus voltage sensor."""

    def __init__(self, i2c, address=0x40, shunt_ohms=0.1, max_expected_amps=1.2):
        self.i2c = i2c
        self.address = address
        self.shunt_ohms = shunt_ohms
        self.current_lsb = max_expected_amps / 32768.0
        self.power_lsb = self.current_lsb * 20.0
        self.calibration = int(0.04096 / (self.current_lsb * shunt_ohms))
        self.configure()

    def configure(self):
        # 32 V bus range, +/-320 mV shunt range, 12-bit averaged conversion,
        # continuous shunt and bus measurement.
        config = 0x399F
        self._write_register(_REG_CONFIG, config)
        self._write_register(_REG_CALIBRATION, self.calibration)

    def bus_voltage_v(self):
        raw = self._read_register(_REG_BUS_VOLTAGE)
        return ((raw >> 3) & 0x1FFF) * 0.004

    def shunt_voltage_v(self):
        raw = self._read_register(_REG_SHUNT_VOLTAGE, signed=True)
        return raw * 0.00001

    def supply_voltage_v(self):
        return self.bus_voltage_v() + self.shunt_voltage_v()

    def current_a(self):
        self._write_register(_REG_CALIBRATION, self.calibration)
        raw = self._read_register(_REG_CURRENT, signed=True)
        return raw * self.current_lsb

    def current_mA(self):
        return self.current_a() * 1000.0

    def power_w(self):
        self._write_register(_REG_CALIBRATION, self.calibration)
        raw = self._read_register(_REG_POWER)
        return raw * self.power_lsb

    def _write_register(self, register, value):
        data = bytes(((value >> 8) & 0xFF, value & 0xFF))
        self.i2c.writeto_mem(self.address, register, data)

    def _read_register(self, register, signed=False):
        data = self.i2c.readfrom_mem(self.address, register, 2)
        value = (data[0] << 8) | data[1]
        if signed and value & 0x8000:
            value -= 1 << 16
        return value

