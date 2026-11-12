"""Database models (SQLAlchemy ORM only, TB-SR-006)."""
from datetime import datetime, timezone

from . import db


def _now():
    return datetime.now(timezone.utc)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    # TB-SR-001: only a salted hash is stored, never the password.
    password_hash = db.Column(db.String(256), nullable=False)


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(10), unique=True, nullable=False)  # stored uppercase
    name = db.Column(db.String(100), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


class Sprint(db.Model):
    """TB-23 / TB-24. status: Planned -> Active -> Completed."""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default="Planned", nullable=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)

    issues = db.relationship("Issue", back_populates="sprint")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "status": self.status,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "issue_count": len(self.issues),
            "story_points": sum(i.story_points or 0 for i in self.issues),
        }


class Issue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)
    number = db.Column(db.Integer, nullable=False)  # running number -> TB-1, TB-2
    title = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(10), nullable=False)
    priority = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), default="To Do", nullable=False)
    story_points = db.Column(db.Integer)
    assignee_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    sprint_id = db.Column(db.Integer, db.ForeignKey("sprint.id"))  # None = backlog

    project = db.relationship("Project")
    assignee = db.relationship("User")
    sprint = db.relationship("Sprint", back_populates="issues")

    def to_dict(self):
        return {
            "id": self.id,
            "key": f"{self.project.key}-{self.number}",
            "title": self.title,
            "type": self.type,
            "priority": self.priority,
            "status": self.status,
            "story_points": self.story_points,
            "assignee_id": self.assignee_id,
            "assignee": self.assignee.name if self.assignee else None,
            "sprint_id": self.sprint_id,
        }


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey("issue.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    body = db.Column(db.String(2000), nullable=False)
    created_at = db.Column(db.DateTime, default=_now)

    author = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "issue_id": self.issue_id,
            "author": self.author.name,
            "body": self.body,
            "created_at": self.created_at.isoformat(),
        }