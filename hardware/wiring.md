# Logisches Verdrahtungsschema fuer 18650 Ladelogik

Das Projekt trennt klar zwischen sicherem Laden und uebergeordneter
Ueberwachung:

- Der TP4056 fuehrt das CC/CV-Laden der einzelnen 18650-Zelle aus.
- Der Raspberry Pi Pico misst, entscheidet und loggt.
- Das Relais schaltet ausschliesslich die 5-V-Versorgung des TP4056.
- Die Zelle wird nicht direkt durch das Relais geschaltet.

![Verdrahtung](wiring_diagram.svg)

## Pinbelegung

| Pico-Pin | Signal | Verbindung |
|---|---|---|
| GP4 | I2C SDA | INA219 SDA, optional OLED SDA |
| GP5 | I2C SCL | INA219 SCL, optional OLED SCL |
| GP15 | Relay IN | Eingang des 3.3-V-kompatiblen Relaismoduls |
| GP16 | OneWire | DS18B20 DATA mit 4.7-kOhm-Pull-up nach 3V3 |
| 3V3 | Versorgung | INA219 VCC, DS18B20 VDD, ggf. Relay-Logik |
| GND | Masse | Gemeinsame Masse Pico, Sensoren, TP4056 IN- |

## Strompfad

1. USB-5-V-Versorgung geht auf den Relaiskontakt.
2. Vom Relaiskontakt geht 5 V auf `IN+` des TP4056.
3. `IN-` des TP4056 liegt auf gemeinsamer Masse.
4. Die 18650-Zelle liegt am Batterieanschluss des TP4056.
5. Der INA219 misst im positiven Batteriezweig mit passender Stromrichtung.

Bei TP4056-Modulen mit Schutzschaltung koennen die Klemmen je nach Modul als
`B+/B-` und `OUT+/OUT-` beschriftet sein. Fuer echte Versuche ist das
Datenblatt beziehungsweise das Layout des konkreten Moduls massgeblich.

## Sicherheitsnotizen

- Keine selbstgebaute CC/CV-Regelung mit PWM, DAC oder GPIO.
- Kein direktes Schalten der Zelle durch das Relais.
- Temperaturfuehler mechanisch und thermisch an der Zelle befestigen.
- Erste Inbetriebnahme nur mit Strombegrenzung, Aufsicht und brandsicherer
  Unterlage.
- Bei Auffaelligkeiten wie Erwaermung, Geruch, Aufblaehen oder Spannung ausser
  Spezifikation sofort abschalten.
