"""Database models: clients, onboarding tasks and activity notes."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

PHASES = ["Kickoff", "Setup", "Training", "Go-Live"]

# Standard onboarding playbook: (phase, title, days after kickoff it is due)
PLAYBOOK: list[tuple[str, str, int]] = [
    ("Kickoff", "Welcome email + kickoff call scheduled", 1),
    ("Kickoff", "Kickoff call held, success criteria agreed", 3),
    ("Kickoff", "Stakeholders and admin users identified", 4),
    ("Setup", "Account configured and SSO / logins created", 7),
    ("Setup", "Customer data imported and validated", 10),
    ("Setup", "Integrations connected", 12),
    ("Training", "Admin training session delivered", 15),
    ("Training", "End-user training session delivered", 18),
    ("Go-Live", "Go-live sign-off from customer", 21),
    ("Go-Live", "30-day success plan shared", 24),
]


class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    plan = db.Column(db.String(20), nullable=False, default="Growth")
    industry = db.Column(db.String(60))
    csm_owner = db.Column(db.String(60), nullable=False)
    contact_name = db.Column(db.String(120))
    contact_email = db.Column(db.String(200))
    kickoff_date = db.Column(db.Date, nullable=False, default=date.today)
    target_go_live = db.Column(db.Date, nullable=False)
    go_live_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=utcnow)

    tasks = db.relationship("Task", backref="client", cascade="all, delete-orphan", order_by="Task.due_date")
    notes = db.relationship("Note", backref="client", cascade="all, delete-orphan", order_by="Note.created_at.desc()")

    # ---- derived metrics -------------------------------------------------
    @property
    def progress(self) -> int:
        if not self.tasks:
            return 0
        return round(100 * sum(t.done for t in self.tasks) / len(self.tasks))

    @property
    def overdue_tasks(self) -> list["Task"]:
        return [t for t in self.tasks if t.is_overdue]

    @property
    def current_phase(self) -> str:
        if self.go_live_date:
            return "Live"
        for phase in PHASES:
            if any(not t.done for t in self.tasks if t.phase == phase):
                return phase
        return "Go-Live"

    @property
    def days_to_go_live(self) -> int | None:
        """Time-to-value in days (only once live)."""
        return (self.go_live_date - self.kickoff_date).days if self.go_live_date else None

    @property
    def health(self) -> str:
        """On Track / At Risk / Delayed, a simple rule a CSM can explain."""
        if self.go_live_date:
            return "Live"
        overdue = len(self.overdue_tasks)
        if date.today() > self.target_go_live or overdue >= 3:
            return "Delayed"
        if overdue >= 1:
            return "At Risk"
        return "On Track"

    def apply_playbook(self) -> None:
        for phase, title, offset in PLAYBOOK:
            self.tasks.append(Task(phase=phase, title=title, owner=self.csm_owner,
                                   due_date=self.kickoff_date + timedelta(days=offset)))

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "plan": self.plan, "industry": self.industry,
            "csm_owner": self.csm_owner, "contact_name": self.contact_name, "contact_email": self.contact_email,
            "kickoff_date": self.kickoff_date.isoformat(), "target_go_live": self.target_go_live.isoformat(),
            "go_live_date": self.go_live_date.isoformat() if self.go_live_date else None,
            "progress": self.progress, "phase": self.current_phase, "health": self.health,
            "overdue_tasks": len(self.overdue_tasks), "days_to_go_live": self.days_to_go_live,
        }


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"), nullable=False)
    phase = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    owner = db.Column(db.String(60))
    due_date = db.Column(db.Date, nullable=False)
    completed_at = db.Column(db.Date)

    @property
    def done(self) -> bool:
        return self.completed_at is not None

    @property
    def is_overdue(self) -> bool:
        return not self.done and self.due_date < date.today()

    @property
    def on_time(self) -> bool | None:
        return None if not self.done else self.completed_at <= self.due_date

    def to_dict(self) -> dict:
        return {
            "id": self.id, "client_id": self.client_id, "phase": self.phase, "title": self.title,
            "owner": self.owner, "due_date": self.due_date.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "done": self.done, "overdue": self.is_overdue,
        }


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"), nullable=False)
    author = db.Column(db.String(60))
    kind = db.Column(db.String(20), default="note")  # note | call | email | risk
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
