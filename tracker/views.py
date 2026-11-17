"""Server-rendered pages."""

from __future__ import annotations

from datetime import date, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for

from tracker.metrics import portfolio_metrics
from tracker.models import PHASES, Client, db

views_bp = Blueprint("views", __name__)

HEALTH_ORDER = {"Delayed": 0, "At Risk": 1, "On Track": 2, "Live": 3}


@views_bp.get("/")
def dashboard():
    clients = Client.query.all()
    owner = request.args.get("owner")
    health = request.args.get("health")
    shown = [c for c in clients if (not owner or c.csm_owner == owner) and (not health or c.health == health)]
    shown.sort(key=lambda c: (HEALTH_ORDER[c.health], c.target_go_live))
    owners = sorted({c.csm_owner for c in clients})
    return render_template("dashboard.html", clients=shown, m=portfolio_metrics(clients),
                           owners=owners, owner=owner, health=health)


@views_bp.route("/clients/new", methods=["GET", "POST"])
def new_client():
    if request.method == "POST":
        form = request.form
        name = form.get("name", "").strip()
        if not name or not form.get("csm_owner", "").strip():
            flash("Client name and CSM owner are required.", "error")
            return render_template("new_client.html", form=form), 400
        if Client.query.filter_by(name=name).first():
            flash("A client with this name already exists.", "error")
            return render_template("new_client.html", form=form), 400
        kickoff = date.fromisoformat(form["kickoff_date"]) if form.get("kickoff_date") else date.today()
        target = (date.fromisoformat(form["target_go_live"]) if form.get("target_go_live")
                  else kickoff + timedelta(days=30))
        client = Client(name=name, plan=form.get("plan", "Growth"), industry=form.get("industry"),
                        csm_owner=form["csm_owner"].strip(), contact_name=form.get("contact_name"),
                        contact_email=form.get("contact_email"), kickoff_date=kickoff, target_go_live=target)
        client.apply_playbook()
        db.session.add(client)
        db.session.commit()
        flash(f"{client.name} added with the standard 10-step onboarding playbook.", "success")
        return redirect(url_for("views.client_detail", client_id=client.id))
    return render_template("new_client.html", form={})


@views_bp.get("/clients/<int:client_id>")
def client_detail(client_id: int):
    client = db.get_or_404(Client, client_id)
    by_phase = {p: [t for t in client.tasks if t.phase == p] for p in PHASES}
    return render_template("client.html", c=client, by_phase=by_phase, phases=PHASES, today=date.today())
