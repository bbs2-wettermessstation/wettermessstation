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
