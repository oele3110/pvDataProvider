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

For the **first start**, uncomment the `environment` block in `docker-compose.yaml` so InfluxDB gets initialized with the correct org, bucket, and token:

```yaml
environment:
  DOCKER_INFLUXDB_INIT_MODE: setup
  DOCKER_INFLUXDB_INIT_USERNAME: admin
  DOCKER_INFLUXDB_INIT_PASSWORD: pvmonitor123
  DOCKER_INFLUXDB_INIT_ORG: pvmonitor
  DOCKER_INFLUXDB_INIT_BUCKET: raw
  DOCKER_INFLUXDB_INIT_ADMIN_TOKEN: pvmonitor-dev-token
```

Then start InfluxDB:

```bash
docker compose up -d influxdb
```

InfluxDB will be available at http://localhost:8086 (login: `admin` / `pvmonitor123`).

**Important:** After the first start, comment out the `environment` block again in `docker-compose.yaml`. Otherwise InfluxDB will be re-initialized on every restart and all data will be lost.

### 4. Create InfluxDB buckets and set retention

```bash
# Create buckets
docker exec pvmonitor-influxdb influx bucket create -n hourly -o pvmonitor -r 8760h --token pvmonitor-dev-token
docker exec pvmonitor-influxdb influx bucket create -n daily  -o pvmonitor -r 0    --token pvmonitor-dev-token

# Set retention on the raw bucket (14 days)
docker exec pvmonitor-influxdb influx bucket update --name raw --retention 336h --token pvmonitor-dev-token --org pvmonitor
```

Retention policy per bucket:

| Bucket | Retention | Description |
|---|---|---|
| raw | 14 days (336h) | Raw 1s values |
| hourly | 1 year (8760h) | Hourly aggregates |
| daily | unlimited | Daily aggregates |

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

### Local development (Windows/macOS)

Run InfluxDB only via Docker, and the backend directly with uvicorn:

```bash
docker compose up -d influxdb
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Production (Raspberry Pi)

On the Pi, both InfluxDB and the backend run as Docker containers. `network_mode: host` is required so the backend container can reach the Modbus devices, MQTT broker, and heating rod on the local network.

```bash
# 1. Create .env file from the example
cp .env.example .env

# 2. Fill in the values
nano .env

# 3. Start everything
docker compose up -d
```

After the first start, create the additional InfluxDB buckets and aggregation tasks as described in steps 4 and 5 above.

### InfluxDB data on external SSD (recommended for Raspberry Pi)

InfluxDB writes data continuously — storing it on the SD card will wear it out quickly. The `docker-compose.yaml` is configured to write to `/mnt/ssd/influxdb` on an external USB-SSD.

Make sure the SSD is mounted at `/mnt/ssd` before starting the containers. Create the data directory:

```bash
sudo mkdir -p /mnt/ssd/influxdb
```

**Migrating existing data from SD card to SSD:**

```bash
# Stop InfluxDB
docker compose stop influxdb

# Find the current Docker volume mountpoint (volume name may vary)
docker volume ls
sudo cp -r $(docker volume inspect <volume-name> --format '{{.Mountpoint}}')/ /mnt/ssd/influxdb/

# Restart
docker compose up -d influxdb
```

Verify InfluxDB started correctly:
```bash
docker logs pvmonitor-influxdb --tail 20
```

## Cloudflare Tunnel

The API is exposed publicly via a Cloudflare Tunnel — no open ports or VPS required.

### Initial setup (once, on any machine with cloudflared installed)

```bash
# Install cloudflared
# Windows: winget install Cloudflare.cloudflared
# Linux:   curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb -o cloudflared.deb && sudo dpkg -i cloudflared.deb

cloudflared tunnel login
cloudflared tunnel create pvmonitor
cloudflared tunnel route dns pvmonitor pv.yourdomain.de
```

This creates a credentials file at `~/.cloudflared/<tunnel-id>.json`.

### Tunnel configuration

Create `~/.cloudflared/config.yml`:

```yaml
tunnel: pvmonitor
credentials-file: /home/pi/.cloudflared/<tunnel-id>.json   # adjust path for your OS

ingress:
  - hostname: pv.yourdomain.de
    service: http://localhost:8000
  - service: http_status:404
```

### Run manually

```bash
cloudflared tunnel run pvmonitor
```

### Run as a system service on the Raspberry Pi (recommended)

```bash
sudo cloudflared service install
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

The tunnel then starts automatically on boot.

### Deploying to the Pi

Copy the following from your development machine to the Pi:

- The repository (via `git clone` or `scp`)
- `~/.cloudflared/<tunnel-id>.json` → `/home/pi/.cloudflared/<tunnel-id>.json`

Then update `credentials-file` in `config.yml` to the correct Linux path.

The API is then available at:
- REST: `https://pv.yourdomain.de/api/`
- WebSocket: `wss://pv.yourdomain.de/ws`

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

## Operations

### Docker

```bash
# Show running containers and their status
docker ps

# Start all services
docker compose up -d

# Stop all services
docker compose down

# Restart a single service
docker compose restart backend
docker compose restart influxdb

# Rebuild and restart the backend after code changes
docker compose build backend && docker compose up -d backend
```

### Logs

```bash
# Follow backend logs live
docker logs pvmonitor-backend -f

# Follow InfluxDB logs live
docker logs pvmonitor-influxdb -f

# Show last 100 lines
docker logs pvmonitor-backend --tail 100

# Cloudflare Tunnel logs
sudo journalctl -u cloudflared -f
```

### Cloudflare Tunnel

```bash
# Check tunnel status
sudo systemctl status cloudflared

# Restart tunnel
sudo systemctl restart cloudflared

# Stop/start tunnel
sudo systemctl stop cloudflared
sudo systemctl start cloudflared
```

### System

```bash
# Check disk usage (relevant for InfluxDB data volume)
df -h

# Check memory usage
free -h

# Check CPU/memory per process
top
```

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
├── docker-compose.yaml     # InfluxDB + backend containers
├── Dockerfile              # Backend container image
├── .env.example            # Environment variable template
└── requirements.txt
```
