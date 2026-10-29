"""REST API. Paths are my guess: compare with SAD section 4.3 and rename
if they differ, because the frontend codes against the SAD."""
import re
from functools import wraps

from flask import Blueprint, jsonify, request, session
from sqlalchemy import func
from werkzeug.security import generate_password_hash

from . import db
from .models import Comment, Issue, Project, User

bp = Blueprint("api", __name__, url_prefix="/api")

TYPES = {"Epic", "Story", "Task", "Bug"}
PRIORITIES = {"Low", "Medium", "High"}
POINTS = {1, 2, 3, 5, 8, 13}


def err(msg, code=400):
    return jsonify(error=msg), code


def login_required(f):
    """TB-SR-002: protected endpoints return 401 without a session."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return err("login required", 401)
        return f(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------
# TB-13  Register a new account   (TB-F-001, TB-F-002, TB-SR-001)
# ---------------------------------------------------------------
@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not name or "@" not in email:
        return err("name and a valid email are required")
    if len(password) < 6:
        return err("password must be at least 6 characters")
    # Duplicate check ignores letter case (TB-F-002).
    if User.query.filter(func.lower(User.email) == email).first():
        return err("email already registered")

    user = User(name=name, email=email,
                password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    session["user_id"] = user.id  # registering also logs the user in
    return jsonify(id=user.id, name=user.name, email=user.email), 201


@bp.get("/me")
@login_required
def me():
    user = db.session.get(User, session["user_id"])
    return jsonify(id=user.id, name=user.name, email=user.email)


# ---------------------------------------------------------------
# TB-15  Create a project with a unique key   (TB-F-005)
# ---------------------------------------------------------------
@bp.post("/projects")
@login_required
def create_project():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    key = str(data.get("key", "")).strip()

    if not name:
        return err("project name is required")
    if not re.fullmatch(r"[A-Za-z]{2,10}", key):
        return err("key must be 2 to 10 letters")
    key = key.upper()
    if Project.query.filter_by(key=key).first():
        return err("project key already exists")

    project = Project(key=key, name=name, owner_id=session["user_id"])
    db.session.add(project)
    db.session.commit()
    return jsonify(id=project.id, key=project.key, name=project.name,
                   owner_id=project.owner_id), 201


# ---------------------------------------------------------------
# TB-17  Create an issue with auto-generated key   (TB-F-008, TB-F-009)
# ---------------------------------------------------------------
@bp.post("/projects/<int:pid>/issues")
@login_required
def create_issue(pid):
    project = db.session.get(Project, pid)
    if not project:
        return err("project not found", 404)

    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    typ = data.get("type", "Task")
    priority = data.get("priority", "Medium")
    points = data.get("story_points")

    if not title:
        return err("title is required")
    if typ not in TYPES:
        return err("invalid type")
    if priority not in PRIORITIES:
        return err("invalid priority")
    # bool is an int in Python, so reject True/False explicitly.
    if points is not None and (isinstance(points, bool) or points not in POINTS):
        return err("story points must be one of 1, 2, 3, 5, 8, 13")

    # Running number per project: TB-1, TB-2, ...
    last = (db.session.query(func.max(Issue.number))
            .filter_by(project_id=pid).scalar() or 0)
    issue = Issue(project_id=pid, number=last + 1, title=title, type=typ,
                  priority=priority, story_points=points)
    db.session.add(issue)
    db.session.commit()
    return jsonify(issue.to_dict()), 201


# ---------------------------------------------------------------
# TB-19  Assign an issue to a team member   (TB-F-012)
# ---------------------------------------------------------------
@bp.patch("/issues/<int:iid>/assignee")
@login_required
def assign_issue(iid):
    issue = db.session.get(Issue, iid)
    if not issue:
        return err("issue not found", 404)

    uid = (request.get_json(silent=True) or {}).get("assignee_id")
    # null un-assigns; anything else must be an existing user id.
    if uid is not None:
        if isinstance(uid, bool) or not isinstance(uid, int) \
                or not db.session.get(User, uid):
            return err("unknown user")
    issue.assignee_id = uid
    db.session.commit()
    return jsonify(issue.to_dict())


# ---------------------------------------------------------------
# TB-20  Comment on an issue   (TB-F-015)
# ---------------------------------------------------------------
@bp.post("/issues/<int:iid>/comments")
@login_required
def add_comment(iid):
    if not db.session.get(Issue, iid):
        return err("issue not found", 404)

    body = str((request.get_json(silent=True) or {}).get("body", "")).strip()
    if not body:
        return err("comment cannot be empty")

    comment = Comment(issue_id=iid, author_id=session["user_id"], body=body)
    db.session.add(comment)
    db.session.commit()
    return jsonify(comment.to_dict()), 201
