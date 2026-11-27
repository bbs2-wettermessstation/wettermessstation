
# wettermessstation
Raspberry Pi Installation Skript Respository

DHT11-Sensor am Raspberry Pi. Messwerte werden minütlich in MariaDB (Docker) gespeichert und über eine Weboberfläche (Apache + PHP, Docker) angezeigt. Zugriff von außen über Tailscale-VPN.

Voraussetzungen
Raspberry Pi mit Raspberry Pi OS 64 Bit
Im Raspberry Pi Imager eingestellt: Hostname wetterstation, Benutzer stationsuser, WLAN inkl. Land DE, SSH aktiviert
DHT11: VCC → Pin 1 (3,3 V), DATA → Pin 7 (GPIO4), GND → Pin 6
Tailscale Auth-Key mit Tag tag:wetterstation

Installation
# Falls die Uhrzeit falsch ist (sonst schlagen apt und git fehl):
sudo date -s "$(curl -sI http://deb.debian.org | grep -i '^date:' | cut -d' ' -f2- | tr -d '\r')"

sudo apt update && upgrade -y
sudo git clone https://github.com/bbs2-wettermessstation/wettermessstation.git /opt/wettermessstation
sudo bash /opt/wettermessstation/install.sh

Einzige Eingabe: der Tailscale Auth-Key. Alle Datenbank-Passwörter werden automatisch erzeugt.

Update
cd /opt/wettermessstation
sudo git pull
sudo bash install.sh

Passwörter anzeigen
sudo cat /opt/wettermessstation/.env
sudo cat /opt/wettermessstation/db.conf







Die zuverlässige Lösung: Kernel-Treiber statt Blinka

Raspberry Pi OS bringt einen eigenen DHT11-Treiber im Linux-Kernel mit. Der Kernel misst die Pulse viel genauer als Python. Das ist die stabilste Variante, und du brauchst dafür weder Blinka noch gpiod.

1. Treiber aktivieren:

Shell
echo "dtoverlay=dht11,gpiopin=4" | sudo tee -a /boot/firmware/config.txt
sudo reboot

2. Nach dem Neustart testen:

Shell
cat /sys/bus/iio/devices/iio:device0/in_temp_input
cat /sys/bus/iio/devices/iio:device0/in_humidityrelative_input

Die Werte kommen in Tausendsteln, zum Beispiel bedeutet 21000 21,0 °C. Ein einzelner Fehler wie Connection timed out oder Input/output error ist normal, dann einfach 2 Sekunden warten und nochmal versuchen.

3. Im Skript die Lesefunktion ersetzen:

Die Imports board und adafruit_dht fallen weg. Stattdessen:

Python
SENSOR_PFAD = "/sys/bus/iio/devices/iio:device0/"
 
def wert_lesen(datei):
with open(SENSOR_PFAD + datei) as f:
return int(f.read().strip()) / 1000
 
def sensor_auslesen():
"""Liest den DHT11 über den Kernel-Treiber mit mehreren Versuchen."""
for versuch in range(1, MAX_VERSUCHE + 1):
try:
return wert_lesen("in_temp_input"), wert_lesen("in_humidityrelative_input")
except OSError as e:
print(f"Versuch {versuch}: Lesefehler - {e}")
time.sleep(2) # DHT11 braucht Pausen zwischen Messungen
return None, None
 

Der Rest des Skripts bleibt gleich. Danach den Cron-Eintrag wieder aktivieren.

4. In install.sh übernehmen: Ergänze diese Zeile, damit das Overlay bei einer Neuinstallation nicht doppelt eingetragen wird. Nach der Installation ist dann einmal ein Neustart nötig:

Shell
grep -q "dtoverlay=dht11" /boot/firmware/config.txt || echo "dtoverlay=dht11,gpiopin=4" >> /boot/firmware/config.txt

Die pip-Pakete adafruit-circuitpython-dht und gpiod brauchst du dann nicht mehr, pymysql reicht.




stationsuser@wettermessstation:~ $ sudo /opt/wettermessstation/venv/bin/python /opt/wettermessstation/dht11_messung.py
Traceback (most recent call last):
  File "/opt/wettermessstation/dht11_messung.py", line 77, in <module>
    main()
    ~~~~^^
  File "/opt/wettermessstation/dht11_messung.py", line 63, in main
    temp, feuchte = sensor_auslesen()
                    ~~~~~~~~~~~~~~~^^
  File "/opt/wettermessstation/dht11_messung.py", line 25, in sensor_auslesen
    temp = sensor.temperature
           ^^^^^^^^^^^^^^^^^^
  File "/opt/wettermessstation/venv/lib/python3.13/site-packages/adafruit_dht.py", line 269, in temperature
    self.measure()
    ~~~~~~~~~~~~^^
  File "/opt/wettermessstation/venv/lib/python3.13/site-packages/adafruit_dht.py", line 216, in measure
    pulses = self._get_pulses_bitbang()
  File "/opt/wettermessstation/venv/lib/python3.13/site-packages/adafruit_dht.py", line 158, in _get_pulses_bitbang
    with DigitalInOut(self._pin) as dhtpin:
         ~~~~~~~~~~~~^^^^^^^^^^^
  File "/opt/wettermessstation/venv/lib/python3.13/site-packages/digitalio.py", line 74, in __init__
    self.direction = Direction.INPUT
    ^^^^^^^^^^^^^^
  File "/opt/wettermessstation/venv/lib/python3.13/site-packages/digitalio.py", line 107, in direction
    self._pin.init(mode=Pin.IN)
    ~~~~~~~~~~~~~~^^^^^^^^^^^^^
  File "/opt/wettermessstation/venv/lib/python3.13/site-packages/adafruit_blinka/microcontroller/generic_linux/libgpiod/libgpiod_pin_2_x.py", line 86, in init
    self._line_request = self._chip.request_lines(
                         ~~~~~~~~~~~~~~~~~~~~~~~~^
        config={int(self._num): None}, consumer=self._CONSUMER
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/opt/wettermessstation/venv/lib/python3.13/site-packages/gpiod/chip.py", line 322, in request_lines
    req_internal = cast("_ext.Chip", self._chip).request_lines(
        line_cfg, consumer, event_buffer_size
    )
OSError: [Errno 16] Device or resource busy
stationsuser@wettermessstation:~ $







cat /sys/bus/iio/devices/iio:device0/name
cat /sys/bus/iio/devices/iio:device0/in_temp_input
cat /sys/bus/iio/devices/iio:device0/in_humidityrelative_input





#!/usr/bin/env python3
"""
Liest Temperatur und Luftfeuchtigkeit vom DHT11 (GPIO4)
über den Kernel-Treiber (dtoverlay=dht11) und speichert sie
in der Tabelle messdaten_dht11.
Wird per Cron jede Minute gestartet.
"""
import sys
import time
import glob
import configparser

import pymysql

CONFIG_DATEI = "/opt/wettermessstation/db.conf"
MAX_VERSUCHE = 5


def sensor_pfad_finden():
    """Sucht das IIO-Gerät des DHT11-Kernel-Treibers."""
    for pfad in glob.glob("/sys/bus/iio/devices/iio:device*"):
        with open(pfad + "/name") as f:
            if f.read().strip().startswith("dht11"):
                return pfad
    return None


def wert_lesen(pfad, datei):
    """Liest einen Wert (in Tausendsteln) und rechnet ihn um."""
    with open(f"{pfad}/{datei}") as f:
        return int(f.read().strip()) / 1000


def sensor_auslesen():
    """Liest den Sensor mit mehreren Versuchen aus."""
    pfad = sensor_pfad_finden()
    if pfad is None:
        print("FEHLER: DHT11-Kernel-Treiber nicht gefunden (dtoverlay aktiv?).")
        return None, None

    for versuch in range(1, MAX_VERSUCHE + 1):
        try:
            temp = wert_lesen(pfad, "in_temp_input")
            feuchte = wert_lesen(pfad, "in_humidityrelative_input")
            return temp, feuchte
        except OSError as e:
            print(f"Versuch {versuch}: Lesefehler - {e}")
            time.sleep(2)  # DHT11 braucht Pausen zwischen Messungen
    return None, None


def werte_plausibel(temp, feuchte):
    """Messbereich DHT11: 0-50 Grad C, 0-100 % rel. Feuchte."""
    return 0 <= temp <= 50 and 0 <= feuchte <= 100


def in_datenbank_speichern(temp, feuchte):
    config = configparser.ConfigParser()
    config.read(CONFIG_DATEI)
    db = config["datenbank"]

    verbindung = pymysql.connect(
        host=db["host"],
        user=db["user"],
        password=db["password"],
        database=db["database"],
    )
    try:
        with verbindung.cursor() as cursor:
            sql = "INSERT INTO messdaten_dht11 (temperatur, luftfeuchtigkeit) VALUES (%s, %s)"
            cursor.execute(sql, (temp, feuchte))
        verbindung.commit()
    finally:
        verbindung.close()


def main():
    temp, feuchte = sensor_auslesen()
    if temp is None:
        print("FEHLER: Sensor konnte nicht ausgelesen werden.")
        sys.exit(1)

    if not werte_plausibel(temp, feuchte):
        print(f"FEHLER: Unplausible Werte ({temp} C, {feuchte} %) - nicht gespeichert.")
        sys.exit(1)

    in_datenbank_speichern(temp, feuchte)
    print(f"Gespeichert: {temp} C, {feuchte} %")


if __name__ == "__main__":
    main()
