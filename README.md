# WebPulse — Website Availability & Downtime Monitoring Platform

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Database](https://img.shields.io/badge/Database-MySQL%208-orange.svg)](https://www.mysql.com/)
[![Framework](https://img.shields.io/badge/Framework-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![ORM](https://img.shields.io/badge/ORM-SQLAlchemy%202.0-red.svg)](https://www.sqlalchemy.org/)
[![Scheduler](https://img.shields.io/badge/Worker-APScheduler-green.svg)](https://apscheduler.readthedocs.io/)
[![Tests](https://img.shields.io/badge/Tests-pytest-blueviolet.svg)](https://docs.pytest.org/)

WebPulse is a website availability and downtime monitoring platform built in Python with MySQL and a Streamlit dashboard. It continuously checks registered websites and APIs, measures response time, records every check, and alerts the owner by email before users are affected. If a website fails two checks in a row, WebPulse opens a downtime incident; when the site recovers, the incident is closed automatically with the total downtime recorded.

---

## Features

- **Real HTTP checks** — actual requests with status codes, redirects (3xx), TLS verification, and millisecond latency. No plain ping.
- **Error taxonomy** — HTTP 4xx / 5xx, connection timeouts, read timeouts, DNS errors, connection refused, and SSL errors are recorded as distinct types.
- **No false alarms** — an incident opens only after **2 consecutive failures** (configurable), so one network blip is ignored.
- **Incident lifecycle** — start time, live duration, cause summary, auto-resolve on recovery with total downtime.
- **Uptime analytics** — uptime % over 24h / 7d / 30d, latency charts, and per-website comparison. Shows "No data" instead of a misleading 100% when no checks exist yet.
  - `Uptime % = (Successful Checks ÷ Total Checks) × 100`
- **Email alerts** — downtime and recovery mails over SMTP, with deduplication and a delivery audit log.
- **Dashboard** — Streamlit UI with Plotly charts, status badges, incident lists, and per-website management.
- **SSRF protection** — registered URLs are validated; loopback (`127.0.0.1`, `localhost`), private subnets (`10/8`, `172.16/12`, `192.168/16`), link-local IPs, and cloud metadata endpoints (`169.254.169.254`) are blocked.
- **SQLite fallback** — if MySQL is not configured, WebPulse automatically falls back to a local SQLite database (`webpulse.db`) so it runs with zero setup.

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Language** | Python 3.12 |
| **Dashboard** | Streamlit, Plotly |
| **HTTP checks** | Requests |
| **Database** | MySQL 8 (`webpulse_db`), SQLAlchemy 2.0 ORM, PyMySQL |
| **Background worker** | APScheduler — one scheduled job per active website |
| **Validation & config** | Pydantic, python-dotenv |
| **Testing** | pytest |

---

## Project Structure

```text
webpulse/
├── Dashboard.py               # Streamlit dashboard (main app)
├── pages/                     # Dashboard pages: Websites, Incidents, Analytics, Settings
├── components/                # Sidebar, KPI cards, status badges, charts
├── static/styles.css          # Dashboard theme
├── config.py                  # Settings loaded from environment / .env
├── database/
│   ├── models.py              # SQLAlchemy models (5 tables)
│   ├── schema.sql             # Database schema (commented, for manual setup)
│   ├── connection.py          # Engine + session handling
│   └── init_db.py             # Create tables + seed data
├── services/                  # Website, Monitoring, Incident, Alert, Analytics
├── repositories/              # Data access layer
├── workers/
│   └── monitor_worker.py      # APScheduler background worker
└── tests/                     # pytest suite
```

---

## Setup & Run

### Prerequisites

- Python 3.12
- MySQL 8 (optional — SQLite fallback works without it)

### 1. Clone and install

```bash
git clone https://github.com/Bhavaniprasad-gurram/webpulse.git
cd webpulse
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your MySQL credentials (see [Environment Variables](#environment-variables)). If you skip this step, WebPulse runs on SQLite automatically.

### 3. Initialise the database

```bash
python -m database.init_db
```

This creates the database and all tables, and seeds three example websites (`example.com`, `python.org`, `github.com`) when the database is empty.

### 4. Start the dashboard

```bash
streamlit run Dashboard.py
```

Open http://localhost:8501

### 5. Start the background worker (separate terminal)

```bash
python -m workers.monitor_worker
```

The worker runs the scheduled checks. Without it, the dashboard works but no new checks are recorded. Both processes must run for full monitoring.

### Run the tests

```bash
pytest -v tests
```

Covers URL validation, SSRF defences, HTTP responses (200 / 301 / 404 / 500 / timeout / SSL / DNS), incident thresholds and lifecycle, uptime math, and the service layer.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values. Never commit `.env` — it is already in `.gitignore`.

| Variable | Default | Description |
|---|---|---|
| `DB_HOST` | `127.0.0.1` | MySQL host |
| `DB_PORT` | `3306` | MySQL port |
| `DB_USER` | `root` | MySQL user |
| `DB_PASSWORD` | *(empty)* | MySQL password |
| `DB_NAME` | `webpulse_db` | Database name |
| `DATABASE_URL` | *(unset)* | Full database URL. Overrides the `DB_*` values when set. Use `sqlite:///webpulse.db` to force SQLite. |
| `DEFAULT_INTERVAL_SECONDS` | `60` | How often each website is checked |
| `DEFAULT_TIMEOUT_SECONDS` | `10` | Per-check request timeout |
| `FAILURE_THRESHOLD` | `2` | Consecutive failures before an incident opens |
| `SLOW_RESPONSE_THRESHOLD_MS` | `1500` | Response time flagged as slow |
| `SMTP_ENABLED` | `false` | Set `true` to enable email alerts |
| `SMTP_HOST` | `smtp.gmail.com` | SMTP server |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USER` | *(empty)* | SMTP login |
| `SMTP_PASSWORD` | *(empty)* | SMTP password / app password |
| `SMTP_SENDER` | `WebPulse Alerts <alerts@webpulse.local>` | From address on alert mails |
| `ALERT_RECIPIENT` | *(empty)* | Who receives downtime / recovery mails |
| `LOG_LEVEL` | `INFO` | Logging level |

---

## Pages

| Page | What it does |
|---|---|
| **Dashboard** (`Dashboard.py`) | Key numbers, response-time chart, status overview, website list with Check now, recent incidents |
| **Websites** | Add, edit, pause, delete websites; per-website check history |
| **Incidents** | Open incidents, incident history with downtime, alert log |
| **Analytics** | Response-time and uptime charts for a selected period and website, full check history |
| **Settings** | Monitoring defaults, SMTP status, database connection test, record counts, worker info |

---

## Database

- **Primary database:** MySQL 8, database `webpulse_db` (created automatically by `python -m database.init_db`).
- **Fallback:** SQLite file `webpulse.db` when MySQL is unavailable or unconfigured.
- **Tables (5):**

| Table | Purpose |
|---|---|
| `users` | Accounts that own websites |
| `websites` | Monitored sites — URL, check interval (default 60s), timeout (default 10s), active flag |
| `monitoring_results` | One row per check — status code, response time (ms), available flag, error type/message |
| `incidents` | Downtime incidents — status `OPEN` / `RESOLVED`, started/resolved time, duration |
| `alert_history` | Every alert sent — type (`DOWNTIME` / `RECOVERY`), recipient, delivery status |

- **Relationships:** one website → many checks, incidents, and alerts. Deleting a website deletes its checks, incidents, and alerts (`ON DELETE CASCADE`).
- **Rules:** website URLs are unique; check interval and timeout must be above 0; incident status is `OPEN` or `RESOLVED` only; alert type is `DOWNTIME` or `RECOVERY` only; delivery status is `SENT`, `FAILED` or `SKIPPED` only.
- **View:** `v_latest_check` — the latest check of every website, used by the dashboard.
- **No triggers:** incident duration is calculated in Python (`IncidentService`), not in the database.
- **Indexes:** `(website_id, checked_at)`, `(is_available, checked_at)`, `(website_id, status)`.
- **Growth:** one website checked every 60s produces 1,440 check rows per day. There is no limit on the number of websites.

The full commented schema is in `database/schema.sql`.

---

## Troubleshooting

- **MySQL connection error** — check `DB_PASSWORD` in `.env`. WebPulse falls back to SQLite so you can still run it.
- **Dashboard works but no new checks appear** — the worker is not running. Start `python -m workers.monitor_worker` in a second terminal.
- **URL rejected when adding a website** — URLs must start with `http://` or `https://` and point to a public site. `localhost` and private IPs are blocked on purpose.
- **Port 8501 in use** — stop the other process, or run `streamlit run Dashboard.py --server.port 8502`.

---

## License

MIT License. Built by Bhavani Prasad — Full-Stack Developer (Sole Developer).
