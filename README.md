# Client Onboarding Tracker

A web app for Customer Success teams to run client onboarding from **kickoff to go-live**: a standard playbook for every new client, a live checklist, an activity log, automatic **On Track / At Risk / Delayed** health, and portfolio KPIs like **time-to-go-live** and **on-time task completion**.

It's a lightweight version of what CS teams usually build in spreadsheets and Jira, designed around how a CSM actually works through a portfolio of new clients.

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Flask](https://img.shields.io/badge/Flask-web%20app-black) ![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-SQLite%20%7C%20PostgreSQL-red) ![JavaScript](https://img.shields.io/badge/JavaScript-vanilla-yellow) ![tests](https://img.shields.io/badge/tests-9%20passing-brightgreen)

![Dashboard](docs/dashboard.png)

---

## Why

Slow onboarding is one of the strongest early predictors of churn. A CSM onboarding several clients at once needs to see, at a glance:

- which clients are slipping **before** the go-live date is missed
- which tasks are overdue and who owns them
- how the team performs over time (time-to-go-live, tasks done on time)

## Features

**Portfolio dashboard**
- KPIs: clients in onboarding, live clients, average days to go-live, % go-lives on target, % tasks done on time, overdue tasks
- Health breakdown and CSM workload (clients, open tasks, overdue tasks per CSM)
- Client list sorted by risk, filterable by CSM and health

**Client workspace**
- 10-step onboarding playbook created automatically, with due dates calculated from the kickoff date:
  `Kickoff → Setup → Training → Go-Live`
- Tick tasks off and progress, phase and health update instantly (no page reload)
- Add custom tasks, log calls / emails / notes / risks in an activity timeline
- One-click **Mark as live** records time-to-value

**Health rules (simple enough to explain to a client):**

| Health | Rule |
|---|---|
| 🟢 On Track | No overdue tasks |
| 🟠 At Risk | 1-2 overdue tasks |
| 🔴 Delayed | 3+ overdue tasks or the target go-live date has passed |
| 🔵 Live | Client has gone live |

**REST API**, so other tools (n8n, Slack bots, BI dashboards) can read and update onboarding data.

![Client workspace](docs/client.png)

## Quick start

```bash
git clone https://github.com/<your-username>/client-onboarding-tracker.git
cd client-onboarding-tracker
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

flask --app tracker seed        # load 14 demo clients (fictional)
flask --app tracker run         # open http://127.0.0.1:5000
pytest                          # run the tests
```

### Use PostgreSQL instead of SQLite

```bash
pip install "psycopg[binary]"
export DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/onboarding
flask --app tracker seed
```

### Deploy

Works on Render / Railway / any host that runs Python:

```bash
gunicorn "tracker:create_app()"
```

Set `DATABASE_URL` and `SECRET_KEY` as environment variables.

## REST API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/clients` | All clients with progress, phase and health. Filters: `health`, `csm_owner` |
| `POST` | `/api/clients` | Create a client (playbook tasks are added automatically) |
| `GET` | `/api/clients/<id>` | Client with all tasks |
| `POST` | `/api/clients/<id>/tasks` | Add a custom task |
| `PATCH` | `/api/tasks/<id>` | Complete / reopen a task, change due date or owner |
| `POST` | `/api/clients/<id>/notes` | Log a note, call, email or risk |
| `POST` | `/api/clients/<id>/go-live` | Mark client as live |
| `GET` | `/api/metrics` | Portfolio KPIs and CSM workload |

```bash
curl -X POST localhost:5000/api/clients -H "Content-Type: application/json" \
  -d '{"name": "Acme Health", "csm_owner": "Asha", "plan": "Enterprise", "kickoff_date": "2026-11-20"}'
```

## Project structure

```
client-onboarding-tracker/
├── tracker/
│   ├── __init__.py      # app factory, config
│   ├── models.py        # Client, Task, Note + playbook and health logic
│   ├── metrics.py       # portfolio KPIs
│   ├── api.py           # JSON REST API
│   ├── views.py         # HTML pages
│   ├── seed.py          # demo data CLI command
│   ├── templates/       # Jinja2 templates
│   └── static/          # CSS + vanilla JavaScript
└── tests/               # 9 pytest tests
```

## Tech stack

Python · Flask · SQLAlchemy · SQLite / PostgreSQL · Jinja2 · HTML5 · CSS3 · JavaScript (Fetch API) · pytest · gunicorn

## Author

**Kowshikh Varma Balerao**, Customer Success Manager · [LinkedIn](https://www.linkedin.com/) · kowshikhvarma@gmail.com
