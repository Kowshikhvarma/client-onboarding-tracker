"""Client Onboarding Tracker: Flask app factory."""

from __future__ import annotations

import os

from flask import Flask

from tracker.models import db


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    database_url = os.getenv("DATABASE_URL", "sqlite:///onboarding.db")
    # Heroku/Render style URLs start with postgres://, SQLAlchemy needs postgresql://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config.update(
        SQLALCHEMY_DATABASE_URI=database_url,
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-only-change-me"),
    )
    if config:
        app.config.update(config)

    db.init_app(app)

    from tracker.api import api_bp
    from tracker.views import views_bp
    from tracker.seed import register_cli

    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    register_cli(app)

    with app.app_context():
        db.create_all()

    return app
