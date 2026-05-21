# Firmware fuer 18650 Ladelogik

Diese MicroPython-Firmware laeuft auf einem Raspberry Pi Pico und ueberwacht
ein fertiges TP4056-Lademodul. Der Pico misst Spannung, Strom und Temperatur,
schaltet ein Relais in der 5-V-Versorgung des TP4056 und schreibt Messwerte in
eine CSV-Datei auf das Pico-Dateisystem.

## Dateien

- `main.py`: Hauptprogramm mit Messung, Zweipunktregler, Fehlerlatch und CSV-Logging
- `config.py`: Pins, Grenzwerte und Sensoroptionen
- `lib/ina219.py`: kompakter MicroPython-Treiber fuer INA219-Module

## Installation auf dem Pico

1. MicroPython UF2 auf den Raspberry Pi Pico flashen.
2. `main.py`, `config.py` und den Ordner `lib/` auf den Pico kopieren.
3. Pins und Sensorvariante in `config.py` an den realen Aufbau anpassen.
4. Seriellen Monitor oeffnen und den ersten Test ohne angeschlossene Zelle
   beziehungsweise mit Labornetzteil und Strombegrenzung pruefen.

Das Projekt ersetzt kein zertifiziertes Ladegeraet und keine
Batterieschutzschaltung.
