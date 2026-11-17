"""Demo data: `flask --app tracker seed` creates 14 fictional clients at different stages."""

from __future__ import annotations

import random
from datetime import date, timedelta

import click

from tracker.models import Client, Note, db

CLIENTS = [
    ("Acme Health", "Enterprise", "Healthcare"), ("Northwind Retail", "Growth", "Retail"),
    ("BluePeak Logistics", "Growth", "Logistics"), ("Cedar Learning", "Starter", "EdTech"),
    ("Quartz Finance", "Enterprise", "FinTech"), ("Harbor Cloud", "Growth", "IT Services"),
    ("Summit Mobility", "Starter", "Logistics"), ("Zenith Foods", "Growth", "Retail"),
    ("Indigo Health", "Enterprise", "Healthcare"), ("Kite Analytics", "Starter", "IT Services"),
    ("Orbit Systems", "Growth", "Manufacturing"), ("Prime Labs", "Starter", "Healthcare"),
    ("Vertex Group", "Enterprise", "FinTech"), ("Lumen Works", "Growth", "Manufacturing"),
]
CSMS = ["Asha", "Ravi", "Meera"]


def seed_demo(rng: random.Random | None = None) -> int:
    rng = rng or random.Random(7)
    today = date.today()
    for i, (name, plan, industry) in enumerate(CLIENTS):
        kickoff = today - timedelta(days=rng.randint(3, 75))
        length = {"Starter": 21, "Growth": 30, "Enterprise": 45}[plan]
        c = Client(name=name, plan=plan, industry=industry, csm_owner=CSMS[i % len(CSMS)],
                   contact_name=f"{name.split()[0]} Admin",
                   contact_email=f"admin@{name.lower().replace(' ', '')}.com",
                   kickoff_date=kickoff, target_go_live=kickoff + timedelta(days=length))
        c.apply_playbook()
        # Simulate progress: each client works at a different pace / reliability.
        pace = rng.uniform(0.6, 1.4)
        for task in c.tasks:
            finish = kickoff + timedelta(days=round((task.due_date - kickoff).days * pace) + rng.randint(-1, 2))
            if finish < today:
                task.completed_at = max(finish, kickoff)
        if all(t.done for t in c.tasks):
            c.go_live_date = max(t.completed_at for t in c.tasks)
        c.notes.append(Note(author=c.csm_owner, kind="call", text="Kickoff call: goals and success criteria agreed."))
        if pace > 1.2:
            c.notes.append(Note(author=c.csm_owner, kind="risk",
                                text="Customer IT team slow to respond on data import. Escalated to sponsor."))
        db.session.add(c)
    db.session.commit()
    return len(CLIENTS)


def register_cli(app) -> None:
    @app.cli.command("seed")
    @click.option("--reset", is_flag=True, help="Delete existing data first")
    def seed(reset: bool) -> None:
        """Load demo clients."""
        if reset:
            db.drop_all()
            db.create_all()
        if Client.query.count():
            click.echo("Database already has data. Use --reset to start over.")
            return
        click.echo(f"Seeded {seed_demo()} demo clients.")
