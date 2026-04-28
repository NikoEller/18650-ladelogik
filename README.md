# 18650 Battery Charge Supervisor mit Raspberry Pi Pico und MicroPython

Ein regelungstechnisches Bewerbungsprojekt zur uebergeordneten Ueberwachung
des Ladevorgangs einer einzelnen geschuetzten 18650-Li-Ion-Zelle. Das sichere
CC/CV-Laden uebernimmt ein fertiges TP4056-Lademodul mit Schutzschaltung. Der
Raspberry Pi Pico misst, schaltet die 5-V-Versorgung des Lademoduls per Relais,
ueberwacht Grenzwerte und loggt Messdaten.

![Logisches Verdrahtungsschema](hardware/wiring_diagram.svg)

## Projektziel

Das Projekt zeigt, wie ein einfacher Zweipunktregler mit Hysterese in ein
praxisnahes Embedded-System eingebettet wird. Im Mittelpunkt steht nicht das
Ersetzen eines Ladegeraets, sondern die sichere Trennung der Aufgaben:

- TP4056: eigentliche Li-Ion-Ladekurve mit Konstantstrom/Konstantspannung
- Raspberry Pi Pico: Messung, Freigabe, Abschaltung, Logging und Auswertung
- Relais: trennt nur die 5-V-Versorgung zum TP4056, nie die Zelle direkt

## Sicherheitshinweise

Dieses Projekt ist ein Lern- und Demonstrationsaufbau. Es ist kein zertifiziertes
Ladegeraet, kein Batteriemanagementsystem und keine Produktempfehlung fuer den
unbeaufsichtigten Betrieb.

Wichtige Regeln:

- Kein selbstgebautes CC/CV-Laden ueber GPIO, PWM, DAC oder Software-Regelung.
- Nur geschuetzte 18650-Zellen oder Zellen mit geeigneter Schutzschaltung verwenden.
- Das Relais schaltet ausschliesslich den 5-V-Eingang des TP4056-Moduls.
- Der Temperaturfuehler muss thermisch an der Zelle befestigt werden.
- Grenzwerte: Laden ein unter 3,85 V, Laden aus ueber 4,00 V, Notabschaltung
  bei 45 Grad C, Ueberspannungsabschaltung bei 4,18 V.
- Zellen unter 2,50 V werden nicht automatisch geladen, sondern muessen
  kontrolliert und bewertet werden.
- Echte Tests nur unter Aufsicht, mit brandsicherer Unterlage, geeigneter
  Schutzschaltung und im Zweifel mit zusaetzlicher Strombegrenzung durchfuehren.

## Bauteilliste

| Bauteil | Funktion |
|---|---|
| Raspberry Pi Pico | Uebergeordnete Steuerung, Logging und I2C |
| TP4056-Modul mit Schutzschaltung | Sicheres CC/CV-Laden der Einzelzelle |
| Geschuetzte 18650-Zelle | Energiespeicher im Testaufbau |
| INA219 Strom-/Spannungssensor | Messung von Zellspannung und Ladestrom per I2C |
| DS18B20 oder NTC | Temperaturmessung an der Zelle |
| Relaismodul | Schaltet die 5-V-Versorgung des TP4056 |
| 4,7-kOhm-Widerstand | Pull-up fuer DS18B20 OneWire |
| Kabel/Breadboard | Aufbau und Verbindung |
| Optional SSD1306 OLED | Lokale Statusanzeige |

Die vollstaendige BOM liegt unter [`hardware/bom.csv`](hardware/bom.csv).

## Regelungskonzept

Der Supervisor verwendet einen Zweipunktregler mit Hysterese:

- Wenn die gemessene Zellspannung kleiner oder gleich 3,85 V ist, darf das
  Relais einschalten.
- Wenn die Zellspannung groesser oder gleich 4,00 V ist, schaltet das Relais
  wieder ab.
- Bei Ueberspannung, Unterspannung ausserhalb des sicheren Bereichs oder zu
  hoher Temperatur wird ein Fehler gelatcht und das Relais bleibt aus.

Ein PID-Regler ist hier nicht sinnvoll. Die Stellgroesse ist binaer: Das
Lademodul bekommt 5 V oder nicht. Der TP4056 regelt den eigentlichen Ladestrom
und die Ladeschlussspannung intern. Der Pico darf daher keine kontinuierliche
Ladekurve regeln, sondern nur eine Freigabeentscheidung mit klaren Grenzwerten
treffen.

## Aufbau

Die Verdrahtung ist in [`hardware/wiring.md`](hardware/wiring.md) beschrieben.
Der wichtige Punkt: Die Relaiskontakte liegen im 5-V-Eingang des TP4056. Die
Zelle bleibt am Lademodul beziehungsweise an ihrer Schutzschaltung angeschlossen.

Empfohlene Pico-Pins:

- GP4: I2C SDA fuer INA219 und optional OLED
- GP5: I2C SCL fuer INA219 und optional OLED
- GP15: Relais-Eingang
- GP16: DS18B20 OneWire

## MicroPython-Code

Die Firmware liegt im Ordner [`firmware/`](firmware/):

- [`firmware/main.py`](firmware/main.py): Hauptprogramm mit Messschleife,
  Hysterese-Regler, Fehlerlatch, CSV-Logging und optionaler OLED-Ausgabe
- [`firmware/config.py`](firmware/config.py): Pins, Grenzwerte und Sensoroptionen
- [`firmware/lib/ina219.py`](firmware/lib/ina219.py): kleiner INA219-Treiber

Logfelder:

`timestamp`, `elapsed_s`, `cell_voltage_v`, `charge_current_mA`,
`temperature_c`, `relay_state`, `soc_percent`, `mode`, `fault_reason`

## Messdaten und Plots

Da keine realen Messwerte beiliegen, erzeugt das Projekt realistisch wirkende
Simulationsdaten. Das Modell bildet eine TP4056-aehnliche Stromkurve, thermische
Traegheit und den Hysterese-Schaltverlauf ab.

```bash
python3 scripts/generate_test_data.py
python3 scripts/plot_results.py
```

Erzeugte Artefakte:

- [`data/simulated_charge_log.csv`](data/simulated_charge_log.csv)
- [`plots/voltage_over_time.svg`](plots/voltage_over_time.svg)
- [`plots/current_over_time.svg`](plots/current_over_time.svg)
- [`plots/temperature_over_time.svg`](plots/temperature_over_time.svg)
- [`plots/relay_state_over_time.svg`](plots/relay_state_over_time.svg)
- [`plots/setpoint_vs_actual.svg`](plots/setpoint_vs_actual.svg)

![Vergleich Sollbereich und Istwert](plots/setpoint_vs_actual.svg)

## Ergebnisse

Die Simulation zeigt das erwartete Verhalten:

- Unterhalb von 3,85 V wird der TP4056 freigegeben.
- Der Ladestrom liegt zunaechst im typischen TP4056-Bereich und faellt nahe der
  oberen Spannung ab.
- Bei 4,00 V trennt das Relais die 5-V-Versorgung des Lademoduls.
- Die Temperatur steigt waehrend der Ladephase moderat an und bleibt unterhalb
  der dokumentierten Notabschaltung.
- Der Relaiszustand zeigt klar die Hysterese und verhindert schnelles Takten.

## GitHub Pages

Die Projektseite liegt im Ordner [`docs/`](docs/) und ist fuer GitHub Pages
vorbereitet. Sie enthaelt Motivation, Regelungstechnik, Hardware, Schaltplan,
Code-Erklaerung, Messdaten, Sicherheitskapitel und Fazit.

## Repository-Struktur

```text
.
├── README.md
├── firmware/
│   ├── main.py
│   ├── config.py
│   └── lib/ina219.py
├── hardware/
│   ├── bom.csv
│   ├── wiring.md
│   └── wiring_diagram.svg
├── scripts/
│   ├── generate_test_data.py
│   └── plot_results.py
├── data/
│   └── simulated_charge_log.csv
├── plots/
│   └── *.svg
└── docs/
    ├── index.html
    ├── styles.css
    └── assets/
```
