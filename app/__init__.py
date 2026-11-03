"""TaskBoard app factory."""
import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app(test_config=None):
    # static/ lives at the repo root, not inside app/ (TB-36)
    app = Flask(__name__, static_folder="../static", static_url_path="/static")

    # TB-SR-008: secret key comes from an environment variable.
    # "dev" is only a fallback for local development.
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///taskboard.db"

    # Tests pass their own config (e.g. in-memory DB).
    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    from .routes import bp, web
    app.register_blueprint(bp)
    app.register_blueprint(web)

    with app.app_context():
        from . import models  # noqa: F401  (registers the tables)
        db.create_all()

    return app