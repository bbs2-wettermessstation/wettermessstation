
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

Als Nächstes muss die angezeigt Tailscale URL in den Browser des PCs eingegeben und die Verbindung bestätigt werden.  

Tailscale: Zugriffskontrolle (ACLs und Tags)
Diese Einrichtung erfolgt einmalig von Hand in der Tailscale Admin Console, nachdem install.sh durchgelaufen ist und der Raspberry Pi im Tailnet erscheint.

Standardmäßig darf jedes Gerät im Tailnet mit jedem anderen kommunizieren. Nach dem Prinzip der minimalen Rechtevergabe wird das so eingeschränkt, dass Endgeräte nur auf die Wettermessstation zugreifen können und nicht untereinander kommunizieren.

1. Zugriffsregeln im JSON-Editor anpassen
Admin Console → Access controls → JSON-Editor. Den Inhalt durch folgenden ersetzen und speichern:

{
  // Tag für den Raspberry Pi (Verwaltung durch Administratoren)
  "tagOwners": {
    "tag:wettermessstation": ["autogroup:admin"]
  },

  // Mitglieder dürfen nur auf die Wettermessstation zugreifen
  "grants": [
    {
      "src": ["autogroup:member"],
      "dst": ["tag:wettermessstation"],
      "ip":  ["*"]
    }
  ]
}

2. Tag dem Raspberry Pi zuweisen
Admin Console → Machines → beim Gerät wettermessstation auf … → Edit ACL tag → tag:wettermessstation auswählen und speichern.


Update
cd /opt/wettermessstation
sudo git pull
sudo bash install.sh

Passwörter anzeigen
sudo cat /opt/wettermessstation/.env
sudo cat /opt/wettermessstation/db.conf

