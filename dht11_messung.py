#!/usr/bin/env python3
"""
Liest Temperatur und Luftfeuchtigkeit vom DHT11 (GPIO4)
und speichert sie in der Tabelle messdaten_dht11.
Wird per Cron jede Minute gestartet.
"""
import sys
import time
import configparser

import board
import adafruit_dht
import pymysql

CONFIG_DATEI = "/opt/wettermessstation/db.conf"
MAX_VERSUCHE = 5


def sensor_auslesen():
    """Liest den Sensor mit mehreren Versuchen aus."""
    sensor = adafruit_dht.DHT11(board.D4, use_pulseio=False)
    try:
        for versuch in range(1, MAX_VERSUCHE + 1):
            try:
                temp = sensor.temperature
                feuchte = sensor.humidity
                if temp is not None and feuchte is not None:
                    return temp, feuchte
            except RuntimeError as e:
                print(f"Versuch {versuch}: Lesefehler - {e}")
            time.sleep(2)  # DHT11 braucht Pausen zwischen Messungen
        return None, None
    finally:
        sensor.exit()


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
