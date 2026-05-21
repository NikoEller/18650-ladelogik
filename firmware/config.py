"""Configuration for 18650 Ladelogik.

The Pico supervises a finished TP4056 charger module. It does not implement
CC/CV charging itself.
"""

# I2C bus for INA219.
I2C_ID = 0
I2C_SDA_PIN = 4
I2C_SCL_PIN = 5
I2C_FREQ_HZ = 400_000
INA219_ADDRESS = 0x40
INA219_SHUNT_OHMS = 0.1
INA219_MAX_EXPECTED_A = 1.2
INVERT_CURRENT_SIGN = False

# Relay module input. The relay switches only the 5 V input of the TP4056.
RELAY_PIN = 15
RELAY_ACTIVE_HIGH = True

# Temperature sensor. Default is DS18B20 on a OneWire bus.
TEMP_SENSOR_TYPE = "DS18B20"  # "DS18B20" or "NTC"
DS18B20_PIN = 16
REQUIRE_TEMP_SENSOR = True

# Optional NTC divider input, used only when TEMP_SENSOR_TYPE == "NTC".
NTC_ADC_PIN = 26
NTC_PULLUP_OHMS = 10_000
NTC_NOMINAL_OHMS = 10_000
NTC_NOMINAL_TEMP_C = 25.0
NTC_BETA = 3950.0

# Optional SSD1306 OLED. Keep False for the minimal supervised logger.
USE_OLED = False
OLED_WIDTH = 128
OLED_HEIGHT = 64
OLED_ADDRESS = 0x3C

# Two-point controller with hysteresis.
CHARGE_ON_V = 3.85
CHARGE_OFF_V = 4.00

# Safety limits. The upper cutoff stays below the Li-Ion absolute maximum.
OVERVOLTAGE_CUTOFF_V = 4.18
ABSOLUTE_MIN_CELL_V = 2.50
LOW_VOLTAGE_WARN_V = 2.90
TEMP_WARN_C = 40.0
TEMP_CUTOFF_C = 45.0
TEMP_RESUME_C = 38.0

# Runtime behavior.
SAMPLE_INTERVAL_S = 5
LOG_FILE = "charge_log.csv"
STATUS_PRINT = True
