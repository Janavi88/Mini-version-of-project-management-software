from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from . import db

STATUSES = ['To Do', 'In Progress', 'In Review', 'Done']
TYPES = ['Epic', 'Story', 'Task', 'Bug']
PRIORITIES = ['Low', 'Medium', 'High']
POINTS = [1, 2, 3, 5, 8, 13]

def utcnow():
    return datetime.now(timezone.utc)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(30), default='Developer')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'email': self.email, 'role': self.role}

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, default='')
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    issue_counter = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=utcnow)
    issues = db.relationship('Issue', backref='project', cascade='all, delete-orphan')
    sprints = db.relationship('Sprint', backref='project', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'name': self.name,
            'description': self.description,
            'owner_id': self.owner_id,
        }

class Sprint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    active = db.Column(db.Boolean, default=False)
    completed = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'name': self.name,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'active': self.active,
            'completed': self.completed,
        }

class Issue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(20), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    sprint_id = db.Column(db.Integer, db.ForeignKey('sprint.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    type = db.Column(db.String(20), default='Task')
    status = db.Column(db.String(20), default='To Do')
    priority = db.Column(db.String(20), default='Medium')
    story_points = db.Column(db.Integer, nullable=True)
    assignee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    assignee = db.relationship('User', foreign_keys=[assignee_id])
    reporter = db.relationship('User', foreign_keys=[reporter_id])
    comments = db.relationship(
        'Comment', backref='issue', cascade='all, delete-orphan', order_by='Comment.id'
    )

    def to_dict(self, detail=False):
        data = {
            'id': self.id,
            'key': self.key,
            'project_id': self.project_id,
            'sprint_id': self.sprint_id,
            'title': self.title,
            'description': self.description,
            'type': self.type,
            'status': self.status,
            'priority': self.priority,
            'story_points': self.story_points,
            'assignee_id': self.assignee_id,
            'assignee': self.assignee.name if self.assignee else None,
            'reporter_id': self.reporter_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if detail:
            data['comments'] = [c.to_dict() for c in self.comments]
        return data

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey('issue.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    author = db.relationship('User')

    def to_dict(self):
        return {
            'id': self.id,
            'issue_id': self.issue_id,
            'author': self.author.name,
            'body': self.body,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
