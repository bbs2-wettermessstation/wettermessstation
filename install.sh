#!/bin/bash
# =====================================================================
# Installationsskript Wettermessstation - BSEF3 Gruppe B
# Aufruf: sudo bash /opt/wettermessstation/install.sh
# Kann beliebig oft ausgeführt werden (z. B. nach git pull).
# =====================================================================
set -euo pipefail

PROJEKT=/opt/wettermessstation
ADMIN=stationsuser          # Admin-Benutzer (Besitzer der Projektdateien)

[ "$EUID" -eq 0 ] || { echo "Bitte mit sudo starten."; exit 1; }
cd "$PROJEKT"

echo "== 1. Zeit synchronisieren =="
timedatectl set-timezone Europe/Berlin
timedatectl set-ntp true
sleep 10
if [ "$(timedatectl show -p NTPSynchronized --value)" != "yes" ]; then
    echo "NTP nicht erreichbar - setze Zeit per HTTP"
    date -s "$(curl -sI http://deb.debian.org | grep -i '^date:' | cut -d' ' -f2- | tr -d '\r')"
fi

echo "== 2. Pakete installieren =="
apt update
apt upgrade -y
apt install -y git curl openssl ufw python3 python3-venv
apt autoremove -y

echo "== 3. DHT11-Kernel-Treiber aktivieren (wirksam nach Neustart) =="
BOOT_CONFIG=/boot/firmware/config.txt
[ -f "$BOOT_CONFIG" ] || BOOT_CONFIG=/boot/config.txt
grep -q "dtoverlay=dht11" "$BOOT_CONFIG" || \
    echo "dtoverlay=dht11,gpiopin=4" >> "$BOOT_CONFIG"

echo "== 4. Docker installieren (falls noetig) =="
if ! command -v docker >/dev/null 2>&1; then
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sh /tmp/get-docker.sh
fi
systemctl enable --now docker

echo "== 5. Tailscale installieren und anmelden (falls noetig) =="
if ! command -v tailscale >/dev/null 2>&1; then
    curl -fsSL https://tailscale.com/install.sh | sh
fi
systemctl enable --now tailscaled
if ! tailscale status >/dev/null 2>&1; then
    echo "Bitte die folgende URL im Browser oeffnen und das Geraet bestaetigen:"
    tailscale up --hostname=wettermessstation
fi

echo "== 6. Passwoerter erzeugen (nur beim ersten Lauf) =="
if [ ! -f .env ]; then
    ROOT_PW=$(openssl rand -hex 16)
    SENSOR_PW=$(openssl rand -hex 16)
    WEB_PW=$(openssl rand -hex 16)

    cat > .env << EOF
DB_ROOT_PASSWORD=$ROOT_PW
WEB_DB_PASSWORD=$WEB_PW
EOF

    cat > db.conf << EOF
[datenbank]
host = 127.0.0.1
user = sensor_writer
password = $SENSOR_PW
database = bsef3_projekt
EOF

    sed -e "s/__SENSOR_PW__/$SENSOR_PW/" \
        -e "s/__WEB_PW__/$WEB_PW/" \
        init_database.sql.template > init_database.sql

    echo "Neue Passwoerter erzeugt (siehe .env und db.conf)."
else
    echo ".env existiert bereits - Passwoerter bleiben unveraendert."
fi

echo "== 7. Python-Umgebung fuer den Sensor =="
[ -d venv ] || python3 -m venv venv
venv/bin/pip install --upgrade pymysql

echo "== 8. Container bauen und starten =="
docker compose up -d --build

echo "== 9. Cron-Job eintragen (ohne Doppelungen) =="
( crontab -l 2>/dev/null | grep -v dht11_messung.py || true
  echo "* * * * * $PROJEKT/venv/bin/python $PROJEKT/dht11_messung.py >/dev/null 2>&1"
) | crontab -

echo "== 10. Firewall =="
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH Administration'
ufw allow 80/tcp comment 'Weboberflaeche'
ufw --force enable

echo "== 11. Rechte setzen (erst jetzt, wenn alle Dateien existieren) =="
chown -R "$ADMIN":www-data "$PROJEKT"
find "$PROJEKT" -path "$PROJEKT/venv" -prune -o -type d -exec chmod 750 {} +
chmod 640 www/index.php dht11_messung.py docker-compose.yml docker/Dockerfile install.sh init_database.sql.template
chmod 644 init_database.sql
chown root:root .env db.conf
chmod 600 .env db.conf
# root darf git pull im Ordner von stationsuser ausfuehren
git config --global --add safe.directory "$PROJEKT"

echo "== 12. Auto-Login deaktivieren =="
raspi-config nonint do_boot_behaviour B3

echo
echo "Installation abgeschlossen."
echo "Weboberflaeche lokal:     http://$(hostname -I | awk '{print $1}')"
echo "Weboberflaeche Tailscale: http://$(tailscale ip -4 2>/dev/null || echo '-')"
echo
echo "WICHTIG: Der Raspberry Pi startet jetzt neu, damit der DHT11-Treiber aktiv wird."

sudo reboot
