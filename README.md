# PV Monitor - Backend

Python backend for a self-hosted PV monitoring system. Collects energy data from a Kostal inverter, smart meter, wallbox, heating rod (ELWA2), and KNX consumers (via ioBroker/MQTT), stores it in InfluxDB, and exposes it via a FastAPI REST API and WebSocket.

## Prerequisites

- Python 3.11+
- Docker Desktop (for InfluxDB)
- Network access to the devices (Modbus devices, MQTT broker, heating rod)

## Setup

### 1. Clone the repository and create a virtual environment

```bash
git clone https://github.com/oele3110/pvDataProvider
cd pvDataProvider
python -m venv .venv
```

Activate:
- Windows (PowerShell): `.venv\Scripts\Activate.ps1`
- Linux/macOS: `source .venv/bin/activate`

If PowerShell blocks script execution:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Start InfluxDB

```bash
docker compose up -d
```

InfluxDB will be available at http://localhost:8086 (login: `admin` / `pvmonitor123`).

### 4. Create InfluxDB buckets

```bash
docker exec pvmonitor-influxdb influx bucket create -n hourly -o pvmonitor -r 8760h --token pvmonitor-dev-token
docker exec pvmonitor-influxdb influx bucket create -n daily  -o pvmonitor -r 0    --token pvmonitor-dev-token
```

### 5. Set up InfluxDB aggregation tasks

In the InfluxDB UI (http://localhost:8086) go to Tasks > + Create Task > New Task:

1. Paste the contents of `influxdb/tasks/aggregate_hourly.flux` and save
2. Paste the contents of `influxdb/tasks/aggregate_daily.flux` and save

Then manually trigger the `aggregate_hourly` task once via the **Run** button.

### 6. Adjust configuration

`config/config.yaml` contains all device IPs and settings - update as needed.

### 7. Create users.yaml

Create `config/users.yaml` with the following structure:

```yaml
users:
  - username: "admin"
    hashed_password: "$2b$12$..."   # bcrypt hash

  - username: "user2"
    hashed_password: "$2b$12$..."   # bcrypt hash
```

Generate a bcrypt hash for a password:
```bash
pip install "bcrypt==4.0.1"
python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('yourPassword'))"
```

Replace the placeholder values in `users.yaml` with the generated hashes.

### 8. Set environment variables

Two variables are required:

- `PV_INFLUX_TOKEN` — the InfluxDB token defined in `docker-compose.yaml`. The default value is `pvmonitor-dev-token`, no change needed.
- `PV_JWT_SECRET` — a random secret for signing JWTs. Generate one with:
  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```
  Save the output — you will need the same value every time you start the server, otherwise existing tokens become invalid.

**Set for the current session only (lost on terminal close):**

Windows (PowerShell):
```powershell
$env:PV_JWT_SECRET = "your-generated-secret"
$env:PV_INFLUX_TOKEN = "pvmonitor-dev-token"
```

Linux/macOS:
```bash
export PV_JWT_SECRET="your-generated-secret"
export PV_INFLUX_TOKEN="pvmonitor-dev-token"
```

**Set permanently (recommended):**

Windows (PowerShell):
```powershell
[System.Environment]::SetEnvironmentVariable("PV_INFLUX_TOKEN", "pvmonitor-dev-token", "User")
[System.Environment]::SetEnvironmentVariable("PV_JWT_SECRET", "your-generated-secret", "User")
```
Then restart PowerShell.

Linux/macOS — add to `~/.bashrc` or `~/.zshrc`:
```bash
export PV_JWT_SECRET="your-generated-secret"
export PV_INFLUX_TOKEN="pvmonitor-dev-token"
```

## Starting the server

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

## API

| Endpoint | Description |
|---|---|
| POST /api/login | Login, returns a JWT |
| GET /api/status | System status and device availability |
| GET /api/history?range=today&device=all | Hourly values for today |
| GET /api/history?range=month&month=2026-04&device=inverter | Daily values for a month |
| GET /api/history?range=year&year=2026 | Monthly values for a year |
| WS /ws | WebSocket - live data stream (~1s interval) |

Swagger UI: http://localhost:8000/docs

All endpoints except `/api/login` require a Bearer token in the `Authorization` header.

## Project structure

```
pvDataProvider/
├── api/                    # FastAPI app (auth, routes, models)
├── collector/              # Data collectors (Modbus, HTTP, MQTT)
├── config/
│   ├── config.yaml         # Device configuration
│   └── users.yaml          # User credentials (bcrypt)
├── db/
│   └── influx_client.py    # InfluxDB wrapper
├── influxdb/
│   └── tasks/              # Flux tasks for aggregation
├── docker-compose.yaml     # InfluxDB container
└── requirements.txt
```
