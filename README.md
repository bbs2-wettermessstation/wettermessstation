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
