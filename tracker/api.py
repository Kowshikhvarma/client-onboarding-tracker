"""JSON REST API (used by the front-end JavaScript and usable by other tools)."""

from __future__ import annotations

from datetime import date, timedelta

from flask import Blueprint, abort, jsonify, request

from tracker.metrics import portfolio_metrics
from tracker.models import PHASES, Client, Note, Task, db

api_bp = Blueprint("api", __name__)


def _parse_date(value: str | None, field: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        abort(400, description=f"'{field}' must be a date in YYYY-MM-DD format")


@api_bp.errorhandler(400)
@api_bp.errorhandler(404)
def json_error(err):
    return jsonify(error=err.description), err.code


@api_bp.get("/clients")
def list_clients():
    clients = Client.query.order_by(Client.target_go_live).all()
    health = request.args.get("health")
    owner = request.args.get("csm_owner")
    if health:
        clients = [c for c in clients if c.health == health]
    if owner:
        clients = [c for c in clients if c.csm_owner == owner]
    return jsonify([c.to_dict() for c in clients])


@api_bp.post("/clients")
def create_client():
    data = request.get_json(silent=True) or {}
    for field in ("name", "csm_owner"):
        if not str(data.get(field, "")).strip():
            abort(400, description=f"'{field}' is required")
    if Client.query.filter_by(name=data["name"].strip()).first():
        abort(400, description="A client with this name already exists")
    kickoff = _parse_date(data.get("kickoff_date"), "kickoff_date") or date.today()
    target = _parse_date(data.get("target_go_live"), "target_go_live") or kickoff + timedelta(days=30)
    if target < kickoff:
        abort(400, description="target_go_live cannot be before kickoff_date")
    client = Client(
        name=data["name"].strip(), plan=data.get("plan", "Growth"), industry=data.get("industry"),
        csm_owner=data["csm_owner"].strip(), contact_name=data.get("contact_name"),
        contact_email=data.get("contact_email"), kickoff_date=kickoff, target_go_live=target,
    )
    if data.get("use_playbook", True):
        client.apply_playbook()
    db.session.add(client)
    db.session.commit()
    return jsonify(client.to_dict()), 201


@api_bp.get("/clients/<int:client_id>")
def get_client(client_id: int):
    client = db.get_or_404(Client, client_id, description="Client not found")
    return jsonify({**client.to_dict(), "tasks": [t.to_dict() for t in client.tasks]})


@api_bp.post("/clients/<int:client_id>/go-live")
def mark_live(client_id: int):
    client = db.get_or_404(Client, client_id, description="Client not found")
    data = request.get_json(silent=True) or {}
    client.go_live_date = _parse_date(data.get("go_live_date"), "go_live_date") or date.today()
    db.session.add(Note(client=client, author=client.csm_owner, kind="note", text="Client marked as live 🎉"))
    db.session.commit()
    return jsonify(client.to_dict())


@api_bp.post("/clients/<int:client_id>/tasks")
def add_task(client_id: int):
    client = db.get_or_404(Client, client_id, description="Client not found")
    data = request.get_json(silent=True) or {}
    if not str(data.get("title", "")).strip():
        abort(400, description="'title' is required")
    phase = data.get("phase", "Setup")
    if phase not in PHASES:
        abort(400, description=f"phase must be one of {PHASES}")
    task = Task(client=client, title=data["title"].strip(), phase=phase,
                owner=data.get("owner") or client.csm_owner,
                due_date=_parse_date(data.get("due_date"), "due_date") or date.today() + timedelta(days=7))
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201


@api_bp.patch("/tasks/<int:task_id>")
def update_task(task_id: int):
    task = db.get_or_404(Task, task_id, description="Task not found")
    data = request.get_json(silent=True) or {}
    if "done" in data:
        task.completed_at = date.today() if data["done"] else None
    if "due_date" in data:
        task.due_date = _parse_date(data["due_date"], "due_date")
    if "owner" in data:
        task.owner = data["owner"]
    db.session.commit()
    return jsonify({"task": task.to_dict(), "client": task.client.to_dict()})


@api_bp.post("/clients/<int:client_id>/notes")
def add_note(client_id: int):
    client = db.get_or_404(Client, client_id, description="Client not found")
    data = request.get_json(silent=True) or {}
    if not str(data.get("text", "")).strip():
        abort(400, description="'text' is required")
    note = Note(client=client, author=data.get("author") or client.csm_owner,
                kind=data.get("kind", "note"), text=data["text"].strip())
    db.session.add(note)
    db.session.commit()
    return jsonify({"id": note.id, "text": note.text, "kind": note.kind,
                    "author": note.author, "created_at": note.created_at.isoformat()}), 201


@api_bp.get("/metrics")
def metrics():
    return jsonify(portfolio_metrics(Client.query.all()))
