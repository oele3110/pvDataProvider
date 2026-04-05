# PV Monitor — Projektkontext für Claude Code

## Projektübersicht

Eigenentwickeltes PV-Monitoring-System bestehend aus zwei Teilen:

1. **Backend (Python)** — läuft auf einem Raspberry Pi 5 (4GB RAM), sammelt Energiedaten von mehreren Quellen, speichert sie in InfluxDB und stellt sie über eine API bereit.
Entwicklungsumgebung: Windows mit PowerShell und PyCharm, später Ausführung auf Raspberry Pi OS
2. **Android App (Kotlin)** — native App mit Jetpack Compose, zeigt Live-Daten und historische Statistiken an.
Entwicklungsumgebung: Windows mit Android Studio

Der Raspberry Pi ist über einen **Cloudflare Tunnel** (`cloudflared`) von überall erreichbar — kein VPS, kein Port-Forwarding.

## Architekturentscheidungen

### Warum diese Architektur?
- **Kein VPS nötig** — alles läuft lokal auf dem Pi, Cloudflare Tunnel stellt den sicheren Zugang her
- **Keine laufenden Kosten** — Cloudflare Free Tier reicht aus
- **Kein offener Port** — `cloudflared` baut eine ausgehende Verbindung auf
- **Nur 2 Nutzer** — der Eigentümer und seine Frau, daher reicht JWT-Auth mit zwei Accounts

### Hardware
- Raspberry Pi 5 mit 4 GB RAM
- Externe USB-SSD für InfluxDB (nicht SD-Karte, wegen Schreiblast)
- PV-Anlage mit Kostal Wechselrichter und Kostal Smartmeter

### Datenquellen & Protokolle

| Gerät | Protokoll | Polling-Intervall |
|---|---|---|
| Kostal Wechselrichter | Modbus TCP | 1 Sekunde |
| Kostal Smartmeter | Modbus TCP | 1 Sekunde |
| Wallbox | Modbus TCP | 1 Sekunde |
| Heizstab | HTTP → JSON | 5–10 Sekunden |
| Hausverbraucher (Kühlschrank, Waschmaschine etc.) | MQTT (via ioBroker, Quelle: KNX) | Event-basiert |

- Modbus-Geräte werden **sequenziell** gepollt (nicht parallel), ein kompletter Zyklus dauert ~100–200ms
- MQTT-Daten kommen event-basiert vom ioBroker, kein Polling nötig
- Kostal hat keine offene API für historische Daten — alle Daten müssen selbst gesammelt und aggregiert werden

### Datenaggregation (3 Ebenen)

1. **Rohdaten** (Bucket `raw`, Retention: 14 Tage) — Momentanwerte in Watt, jede Sekunde
2. **Stundenwerte** (Bucket `hourly`, Retention: 1 Jahr) — Summe (kWh), Durchschnitt, Min, Max pro Stunde
3. **Tageswerte** (Bucket `daily`, Retention: unbegrenzt) — Tagesgesamtwerte, Eigenverbrauchsquote, Autarkiegrad

Automatische Aggregation über InfluxDB Tasks. Umrechnung: Leistung (W) × Intervall (s) ÷ 3600 = Energie (Wh).

### Abgeleitete Kennzahlen
- **Eigenverbrauch** = Erzeugung − Einspeisung
- **Eigenverbrauchsquote** = Eigenverbrauch ÷ Erzeugung × 100
- **Autarkiegrad** = Eigenverbrauch ÷ Gesamtverbrauch × 100
- **Netzbezug** = direkt vom Smartmeter (Zählerstand)

Smartmeter-Zählerstände (kWh) werden als Referenzwerte mitlesen.

## Tech-Stack

### Backend (Raspberry Pi)
- **Python 3.11+**
- **FastAPI** — REST-API + WebSocket für Live-Daten
- **InfluxDB 2.x** — Zeitreihendatenbank
- **pyModbusTCP** — Modbus TCP Client (aus bestehendem Projekt übernommen, nicht wechseln)
- **paho-mqtt** — MQTT Client für ioBroker-Daten
- **requests/httpx** — HTTP Client für Heizstab
- **python-jose + passlib** — JWT-Authentifizierung
- **cloudflared** — Cloudflare Tunnel Client

### Android App
- **Kotlin**
- **Jetpack Compose** — UI-Framework
- **OkHttp + Retrofit** — REST-API-Calls
- **OkHttp WebSocket** — Live-Datenverbindung
- Domain: `wss://pv.deinedomain.de/ws` (WebSocket), `https://pv.deinedomain.de/api/` (REST)

## Projektstruktur — Backend

```
pv-monitor-backend/
├── config/
│   ├── config.yaml            # Geräte-IPs, Modbus-Register, Polling-Intervalle
│   └── users.yaml             # Nutzer-Credentials (bcrypt-gehashed)
├── collector/
│   ├── __init__.py
│   ├── base_reader.py         # Abstrakte Basisklasse für alle Reader
│   ├── modbus_reader.py       # Wechselrichter, Smartmeter, Wallbox
│   ├── http_reader.py         # Heizstab (JSON-API)
│   ├── mqtt_reader.py         # ioBroker KNX-Verbraucher
│   └── collector_service.py   # Orchestriert alle Reader, schreibt in InfluxDB
├── api/
│   ├── __init__.py
│   ├── main.py                # FastAPI-App, CORS, Startup/Shutdown
│   ├── auth.py                # JWT-Login, Token-Validierung, Middleware
│   ├── routes_live.py         # WebSocket-Endpunkt: Live-Daten-Stream
│   ├── routes_history.py      # REST: /api/history?range=today&device=inverter
│   ├── routes_status.py       # REST: /api/status — Systemstatus, Geräteverfügbarkeit
│   └── models.py              # Pydantic-Modelle (EnergyData, Stats, LoginRequest)
├── db/
│   ├── __init__.py
│   └── influx_client.py       # InfluxDB-Wrapper (Schreiben + Flux-Abfragen)
├── tests/
│   ├── test_modbus_reader.py
│   ├── test_collector.py
│   └── test_api.py
├── influxdb/
│   └── tasks/                 # InfluxDB Task-Definitionen (Flux)
│       ├── aggregate_hourly.flux
│       └── aggregate_daily.flux
├── requirements.txt
├── docker-compose.yaml        # InfluxDB + Backend als Container
├── Dockerfile
├── CLAUDE.md                  # Diese Datei
└── README.md
```

## Projektstruktur — Android App

```
pv-monitor-app/
├── app/src/main/java/de/pvmonitor/
│   ├── data/
│   │   ├── api/
│   │   │   ├── PvApiService.kt         # Retrofit-Interface (REST-Endpunkte)
│   │   │   └── WebSocketManager.kt     # WebSocket-Verbindung + Auto-Reconnect
│   │   ├── auth/
│   │   │   ├── AuthRepository.kt       # Login, Token-Speicherung (EncryptedSharedPrefs)
│   │   │   └── TokenInterceptor.kt     # OkHttp Interceptor: JWT an jeden Request
│   │   └── model/
│   │       ├── EnergyData.kt           # Live-Datenmodell (Erzeugung, Verbrauch, etc.)
│   │       └── Statistics.kt           # Historische Aggregationen
│   ├── ui/
│   │   ├── dashboard/
│   │   │   ├── DashboardScreen.kt      # Hauptansicht: Live-Energiefluss
│   │   │   └── DashboardViewModel.kt
│   │   ├── detail/
│   │   │   ├── DetailScreen.kt         # Detailansicht pro Gerät
│   │   │   └── DetailViewModel.kt
│   │   ├── history/
│   │   │   ├── HistoryScreen.kt        # Tages-/Monats-/Jahres-Charts
│   │   │   └── HistoryViewModel.kt
│   │   ├── login/
│   │   │   └── LoginScreen.kt
│   │   └── components/
│   │       ├── EnergyFlowDiagram.kt    # Animiertes Energiefluss-Diagramm
│   │       ├── PowerGauge.kt           # Aktuelle Leistung als Gauge
│   │       └── ConsumptionCard.kt      # Einzelverbraucher-Karte
│   └── PvMonitorApp.kt                # Navigation, Hilt DI-Setup
├── app/src/main/res/
└── build.gradle.kts
```

## API-Design

### Auth
- `POST /api/login` — Body: `{username, password}` → Response: `{access_token, token_type}`
- JWT-Token wird im `Authorization: Bearer <token>` Header mitgeschickt

### Live-Daten
- `WS /ws` — WebSocket-Verbindung, sendet alle ~1s ein JSON-Objekt:
```json
{
  "timestamp": "2026-04-05T14:30:00Z",
  "inverter": {"power_w": 3500, "daily_kwh": 18.4},
  "smartmeter": {"grid_feed_w": 1200, "grid_consume_w": 0, "total_feed_kwh": 12345.6},
  "wallbox": {"power_w": 7400, "session_kwh": 12.3, "state": "charging"},
  "heater": {"power_w": 2000, "state": "on"},
  "consumers": {
    "fridge": {"power_w": 45},
    "washer": {"power_w": 0}
  },
  "calculated": {
    "self_consumption_w": 2300,
    "self_consumption_rate": 65.7,
    "autarky_rate": 82.3
  }
}
```

### Historische Daten
- `GET /api/history?range=today&device=all` — Stundenwerte des heutigen Tages
- `GET /api/history?range=month&month=2026-04&device=inverter` — Tageswerte eines Monats
- `GET /api/history?range=year&year=2026` — Monatswerte eines Jahres
- Response ist immer ein Array von Zeitreihen-Datenpunkten

### Status
- `GET /api/status` — Systemstatus, Geräteverfügbarkeit, InfluxDB-Status

## Migration vom bestehenden Code (pvDataProvider)

### Bestehendes Repository
- GitHub: https://github.com/oele3110/pvDataProvider
- Zusätzliche Modbus-Library: https://github.com/oele3110/modbusReader

### Bestehende Struktur (IST-Zustand)
```
pvDataProvider/
├── configs/
│   ├── ModbusConfig.py        # ⭐ Modbus-Register-Definitionen (Adressen, Einheiten, Datentypen)
│   ├── HeaterRodConfig.py     # ⭐ Heizstab JSON-Felder und Zuordnungen
│   └── MqttConfig.py          # ⭐ MQTT-Topics und Mapping
├── modbus/
│   └── ModbusClient.py        # Modbus-Polling-Logik
├── heaterRod/
│   └── HeaterRodClient.py     # HTTP-Polling des Heizstabs
├── mqtt/
│   └── MqttClient.py          # MQTT-Subscriber für ioBroker
├── websocket/
│   └── WebsocketServer.py     # Einfacher WebSocket-Server (websockets-Paket)
├── jsonParser/
│   └── JsonConverter.py       # Wandelt alle Datenquellen in einheitliches JSON
├── utils/
├── main.py                    # Async-Orchestrierung aller Clients
├── sampleSmartMeterConfig.json
└── requirements.txt
```

### Bestehende Dependencies
```
git+https://github.com/oele3110/modbusReader@main
pyModbusTCP~=0.3.0
websockets~=15.0.1
paho-mqtt~=2.1.0
requests~=2.32.3
aiohttp~=3.11.13
```

### Bestehende Architektur (was bereits funktioniert)
- `main.py` startet alle Clients als async Tasks mit sauberem Signal-Handling (SIGINT/SIGTERM)
- Drei Data Stores (Dicts): `heater_rod_data_store`, `mqtt_data_store`, `modbus_data_store`
- `JsonConverter` führt alle Stores zu einem einheitlichen JSON zusammen
- WebSocket-Server pushed das kombinierte JSON an verbundene Clients (1x pro Sekunde)
- Graceful Shutdown: Alle Tasks werden sauber beendet
- Heizstab-IP: `192.168.178.174`
- MQTT-Broker (ioBroker): `192.168.178.182:1883`

### Migrationsstrategie (IST → SOLL)

#### Was übernommen wird (1:1 oder leicht angepasst)
1. **configs/ModbusConfig.py** → Die Modbus-Register-Definitionen (Adressen, Einheiten, Datentypen) sind das Herzstück. Diese werden in das neue `config/config.yaml` überführt oder als Python-Dicts direkt weiterverwendet. WICHTIG: Lies diese Datei zuerst und verstehe die Struktur, bevor du den neuen Modbus-Reader schreibst.
2. **configs/HeaterRodConfig.py** → Heizstab-Felder und deren Zuordnung. In die neue Config übernehmen.
3. **configs/MqttConfig.py** → MQTT-Topics und Mapping. In die neue Config übernehmen.
4. **modbus/ModbusClient.py** → Die Polling-Logik kann als Grundlage für den neuen `collector/modbus_reader.py` dienen. Prüfe ob `pyModbusTCP` oder `pymodbus` verwendet wird und behalte die gleiche Library bei.
5. **heaterRod/HeaterRodClient.py** → HTTP-Polling-Logik übernehmen in `collector/http_reader.py`.
6. **mqtt/MqttClient.py** → MQTT-Subscriber-Logik übernehmen in `collector/mqtt_reader.py`.
7. **modbusReader** (externes Repo) → Prüfe ob diese Library weiterhin als Dependency nötig ist oder ob die Funktionalität in den neuen Reader integriert werden kann.

#### Was neu gebaut wird
1. **InfluxDB-Integration** — Statt nur In-Memory-Dicts werden alle Werte auch in InfluxDB geschrieben
2. **FastAPI-Server** — Ersetzt den einfachen `websockets`-Server, bietet zusätzlich REST-Endpunkte
3. **JWT-Authentifizierung** — Neu, da bisher keine Auth vorhanden
4. **Datenaggregation** — Neu, InfluxDB Tasks für Stunden-/Tageswerte
5. **REST-API für historische Daten** — Neu, Abfrage der aggregierten Daten

#### Was wegfällt
1. **jsonParser/JsonConverter.py** — Die Konvertierungslogik wandert in die Pydantic-Modelle und den Collector-Service
2. **websocket/WebsocketServer.py** — Wird durch FastAPI-WebSocket ersetzt
3. **Einfache Dict-Stores** — Werden durch InfluxDB + einen In-Memory-Cache für Live-Daten ersetzt

### Schritt-für-Schritt Migration

**Schritt 1: Bestehenden Code analysieren**
- Lies ALLE Dateien in `configs/` — dort steckt das domänenspezifische Wissen (Modbus-Register, MQTT-Topics, Heizstab-Felder)
- Lies `modbus/ModbusClient.py` und die externe `modbusReader`-Library — verstehe wie die Register aktuell gelesen werden
- Lies `jsonParser/JsonConverter.py` — verstehe das aktuelle Datenformat

**Schritt 2: Config-Migration**
- Extrahiere alle Geräte-Konfigurationen aus den Python-Dicts in `configs/` in eine einheitliche `config/config.yaml`
- Struktur der YAML: ein Abschnitt pro Gerät mit IP, Protokoll, Polling-Intervall und geräte-spezifischen Parametern (Register für Modbus, Felder für HTTP, Topics für MQTT)

**Schritt 3: Reader-Migration**
- Erstelle die neuen Reader in `collector/` basierend auf dem bestehenden Code
- Hauptunterschied: Die neuen Reader schreiben nicht nur in ein Dict, sondern auch in InfluxDB
- Die bestehende Polling-Logik (async, mit Sleep-Intervall) kann weitgehend übernommen werden
- WICHTIG: Die bestehende Library `pyModbusTCP` beibehalten, nicht auf `pymodbus` wechseln (vermeidet unnötige Breaking Changes)

**Schritt 4: API aufsetzen**
- FastAPI-App erstellen, die den bestehenden WebSocket-Output als Grundlage nimmt
- Das JSON-Format aus `JsonConverter.py` als Vorlage für die Pydantic-Modelle nutzen
- JWT-Auth hinzufügen

**Schritt 5: Testen**
- Der neue Stack muss die gleichen Daten liefern wie der alte
- Parallelbetrieb: Alten und neuen Code gleichzeitig laufen lassen und Outputs vergleichen

## Coding-Richtlinien

- Python: Type Hints verwenden, async/await wo sinnvoll (FastAPI ist async)
- Config nicht hardcoden — alles über `config.yaml`
- Modbus-Register in der Config definieren, nicht im Code
- Error Handling: Geräte können offline gehen, der Collector muss damit umgehen und weiterlaufen
- Logging: strukturiertes Logging mit `logging` Modul
- Tests: pytest, Modbus-Geräte mocken

## Reihenfolge der Implementierung

1. **Projekt-Setup** — Verzeichnisstruktur, venv, requirements.txt, Docker-Compose für InfluxDB
2. **Config-System** — config.yaml Laden und Validierung
3. **InfluxDB-Client** — Verbindung, Schreiben, Abfragen
4. **Modbus-Reader** — Wechselrichter + Smartmeter auslesen (Kernfunktionalität)
5. **Collector-Service** — Orchestrierung, Polling-Loop
6. **FastAPI + Auth** — Grundgerüst mit JWT-Login
7. **WebSocket-Endpunkt** — Live-Daten-Stream
8. **REST-Endpunkte** — Historische Abfragen
9. **InfluxDB-Tasks** — Automatische Aggregation
10. **MQTT + HTTP Reader** — Heizstab und ioBroker anbinden
11. **Android App** — nach stabilem Backend