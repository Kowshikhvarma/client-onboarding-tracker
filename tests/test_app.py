from datetime import date, timedelta

import pytest

from tracker import create_app
from tracker.metrics import portfolio_metrics
from tracker.models import PLAYBOOK, Client, Task, db
from tracker.seed import seed_demo


@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def make_client(api, **overrides):
    payload = {"name": "Acme Health", "csm_owner": "Asha", "plan": "Enterprise",
               "kickoff_date": date.today().isoformat()}
    payload.update(overrides)
    return api.post("/api/clients", json=payload)


def test_create_client_applies_playbook(client):
    r = make_client(client)
    assert r.status_code == 201
    body = r.json
    assert body["progress"] == 0 and body["phase"] == "Kickoff" and body["health"] == "On Track"
    detail = client.get(f"/api/clients/{body['id']}").json
    assert len(detail["tasks"]) == len(PLAYBOOK)


def test_validation_errors(client):
    assert client.post("/api/clients", json={"name": "X"}).status_code == 400
    assert make_client(client, kickoff_date="31-12-2026").status_code == 400
    assert make_client(client, target_go_live=(date.today() - timedelta(days=5)).isoformat()).status_code == 400
    make_client(client)
    dup = make_client(client)
    assert dup.status_code == 400 and "already exists" in dup.json["error"]


def test_completing_tasks_updates_progress_and_phase(client):
    cid = make_client(client).json["id"]
    tasks = client.get(f"/api/clients/{cid}").json["tasks"]
    kickoff_tasks = [t for t in tasks if t["phase"] == "Kickoff"]
    for t in kickoff_tasks:
        r = client.patch(f"/api/tasks/{t['id']}", json={"done": True})
    assert r.json["client"]["phase"] == "Setup"
    assert r.json["client"]["progress"] == round(100 * len(kickoff_tasks) / len(tasks))
    undo = client.patch(f"/api/tasks/{kickoff_tasks[0]['id']}", json={"done": False}).json
    assert undo["task"]["done"] is False and undo["client"]["phase"] == "Kickoff"


def test_overdue_tasks_drive_health(app):
    with app.app_context():
        c = Client(name="Late Co", csm_owner="Ravi", kickoff_date=date.today() - timedelta(days=20),
                   target_go_live=date.today() + timedelta(days=10))
        c.apply_playbook()
        db.session.add(c)
        db.session.commit()
        # kickoff + 20 days: 6 playbook tasks due before today, all incomplete
        assert len(c.overdue_tasks) >= 3 and c.health == "Delayed"
        for t in c.tasks[:-1]:
            if t.is_overdue:
                t.completed_at = date.today()
        overdue = c.tasks[0]
        overdue.completed_at = None
        assert c.health == "At Risk"


def test_go_live_and_time_to_value(client):
    kickoff = date.today() - timedelta(days=25)
    cid = make_client(client, kickoff_date=kickoff.isoformat(),
                      target_go_live=(kickoff + timedelta(days=30)).isoformat()).json["id"]
    body = client.post(f"/api/clients/{cid}/go-live", json={}).json
    assert body["health"] == "Live" and body["days_to_go_live"] == 25
    m = client.get("/api/metrics").json
    assert m["live"] == 1 and m["go_live_on_target_pct"] == 100.0


def test_custom_task_and_notes(client):
    cid = make_client(client).json["id"]
    assert client.post(f"/api/clients/{cid}/tasks", json={"title": "Custom report", "phase": "Nope"}).status_code == 400
    t = client.post(f"/api/clients/{cid}/tasks", json={"title": "Custom report", "phase": "Training"})
    assert t.status_code == 201 and t.json["owner"] == "Asha"
    n = client.post(f"/api/clients/{cid}/notes", json={"text": "Sponsor call went well", "kind": "call"})
    assert n.status_code == 201 and n.json["author"] == "Asha"
    assert client.post(f"/api/clients/{cid}/notes", json={"text": "  "}).status_code == 400


def test_task_on_time_metric(app):
    with app.app_context():
        c = Client(name="Metric Co", csm_owner="Meera", kickoff_date=date.today() - timedelta(days=10),
                   target_go_live=date.today() + timedelta(days=20))
        c.tasks = [
            Task(phase="Kickoff", title="a", due_date=date.today() - timedelta(days=5),
                 completed_at=date.today() - timedelta(days=6)),
            Task(phase="Kickoff", title="b", due_date=date.today() - timedelta(days=5),
                 completed_at=date.today() - timedelta(days=1)),
        ]
        db.session.add(c)
        db.session.commit()
        m = portfolio_metrics([c])
        assert m["task_on_time_pct"] == 50.0
        assert m["csm_workload"]["Meera"]["clients"] == 1


def test_seed_and_pages_render(app, client):
    with app.app_context():
        assert seed_demo() == 14
    page = client.get("/")
    assert page.status_code == 200 and b"Onboarding portfolio" in page.data and b"Acme Health" in page.data
    assert client.get("/?health=Delayed").status_code == 200
    detail = client.get("/clients/1")
    assert detail.status_code == 200 and b"Onboarding checklist" in detail.data
    assert client.get("/clients/999").status_code == 404
    m = client.get("/api/metrics").json
    assert m["clients_total"] == 14


def test_new_client_form(client):
    assert client.get("/clients/new").status_code == 200
    r = client.post("/clients/new", data={"name": "Form Co", "csm_owner": "Ravi", "plan": "Starter"})
    assert r.status_code == 302
    assert client.post("/clients/new", data={"name": "", "csm_owner": ""}).status_code == 400
    assert client.get("/api/clients?csm_owner=Ravi").json[0]["name"] == "Form Co"
