<?php
// Datenbank-Verbindungsdaten
$host    = 'db';                          // Name des Datenbank-Containers
$db      = 'bsef3_projekt';
$user    = 'web_viewer';
$pass    = getenv('WEB_DB_PASSWORD');     // kommt aus der .env ueber docker-compose
$charset = 'utf8mb4';

$dsn = "mysql:host=$host;dbname=$db;charset=$charset";
$options = [
    PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    PDO::ATTR_EMULATE_PREPARES   => false,
];

try {
    $pdo = new PDO($dsn, $user, $pass, $options);
    $stmt = $pdo->query("SELECT * FROM messdaten_dht11 ORDER BY zeitstempel DESC LIMIT 10");
    $messdaten = $stmt->fetchAll();
    $aktuell = $messdaten[0] ?? null;
} catch (\PDOException $e) {
    die("Fehler bei der Datenbankverbindung.");
}
?>
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DHT11 Sensor Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; }
        h1 { color: #333; }
        .card-container { display: flex; gap: 20px; margin-bottom: 30px; }
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); flex: 1; text-align: center; }
        .card h2 { margin: 0 0 10px 0; color: #666; font-size: 1.1rem; }
        .card .value { font-size: 2rem; font-weight: bold; color: #007bff; }
        table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #007bff; color: white; }
        tr:hover { background-color: #f1f1f1; }
    </style>
</head>
<body>

    <h1>Raspberry Pi - DHT11 Dashboard</h1>

    <div class="card-container">
        <div class="card">
            <h2>Aktuelle Temperatur</h2>
            <div class="value">
                <?= $aktuell ? htmlspecialchars($aktuell['temperatur']) . ' °C' : 'Keine Daten' ?>
            </div>
        </div>
        <div class="card">
            <h2>Aktuelle Luftfeuchtigkeit</h2>
            <div class="value">
                <?= $aktuell ? htmlspecialchars($aktuell['luftfeuchtigkeit']) . ' %' : 'Keine Daten' ?>
            </div>
        </div>
        <div class="card">
            <h2>Letzte Aktualisierung</h2>
            <div class="value" style="font-size: 1.2rem; color: #555;">
                <?= $aktuell ? htmlspecialchars($aktuell['zeitstempel']) : '-' ?>
            </div>
        </div>
    </div>

    <h2>Messhistorie (Letzte 10 Einträge)</h2>
    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Zeitstempel</th>
                <th>Temperatur (°C)</th>
                <th>Luftfeuchtigkeit (%)</th>
            </tr>
        </thead>
        <tbody>
            <?php if (!empty($messdaten)): ?>
                <?php foreach ($messdaten as $zeile): ?>
                    <tr>
                        <td><?= htmlspecialchars($zeile['id']) ?></td>
                        <td><?= htmlspecialchars($zeile['zeitstempel']) ?></td>
                        <td><?= htmlspecialchars($zeile['temperatur']) ?> °C</td>
                        <td><?= htmlspecialchars($zeile['luftfeuchtigkeit']) ?> %</td>
                    </tr>
                <?php endforeach; ?>
            <?php else: ?>
                <tr><td colspan="4">Keine Messdaten in der Datenbank vorhanden.</td></tr>
            <?php endif; ?>
        </tbody>
    </table>

    <!-- Auto-Refresh: Seite alle 60 Sekunden neu laden -->
    <script>
        setTimeout(function(){
            location.reload();
        }, 60000);
    </script>
</body>
</html>
