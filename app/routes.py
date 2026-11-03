"""REST API. Paths are my guess: compare with SAD section 4.3 and rename
if they differ, because the frontend codes against the SAD."""
import os
import re
from functools import wraps

from flask import (Blueprint, current_app, jsonify, request, session)
from sqlalchemy import func
from werkzeug.security import generate_password_hash

from . import db
from .models import Comment, Issue, Project, User

bp = Blueprint("api", __name__, url_prefix="/api")
web = Blueprint("web", __name__)  # serves the web page at "/" (TB-36)

TYPES = {"Epic", "Story", "Task", "Bug"}
PRIORITIES = {"Low", "Medium", "High"}
POINTS = {1, 2, 3, 5, 8, 13}

EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
MAX_NAME = 100        # user name, project name
MAX_EMAIL = 254
MAX_TITLE = 200       # issue title
MAX_COMMENT = 2000    # comment body


def err(msg, code=400):
    return jsonify(error=msg), code


def body():
    """Return the JSON body only if it is an object, else None (TB-40)."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def text(data, field):
    """Stripped string value of a field, or "" if missing or not a string."""
    value = data.get(field)
    return value.strip() if isinstance(value, str) else ""


def login_required(f):
    """TB-SR-002: protected endpoints return 401 without a session."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return err("login required", 401)
        return f(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------
# TB-36  Serve the web page at GET /
# ---------------------------------------------------------------
@web.get("/")
def index():
    return current_app.send_static_file("index.html")


# ---------------------------------------------------------------
# TB-13  Register a new account   (TB-F-001, TB-F-002, TB-SR-001)
# ---------------------------------------------------------------
@bp.post("/register")
def register():
    data = body()
    if data is None:
        return err("JSON object body required")

    name = text(data, "name")
    email = text(data, "email").lower()
    password = data.get("password")

    if not name or not EMAIL_RE.fullmatch(email):
        return err("name and a valid email are required")
    if len(name) > MAX_NAME or len(email) > MAX_EMAIL:
        return err("name or email is too long")
    if not isinstance(password, str) or len(password) < 6:
        return err("password must be at least 6 characters")
    # Duplicate check ignores letter case (TB-F-002).
    if User.query.filter(func.lower(User.email) == email).first():
        return err("email already registered", 409)

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
    data = body()
    if data is None:
        return err("JSON object body required")

    name = text(data, "name")
    key = text(data, "key")

    if not name:
        return err("project name is required")
    if len(name) > MAX_NAME:
        return err("project name is too long")
    if not re.fullmatch(r"[A-Za-z]{2,10}", key):
        return err("key must be 2 to 10 letters")
    key = key.upper()
    if Project.query.filter_by(key=key).first():
        return err("project key already exists", 409)

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

    data = body()
    if data is None:
        return err("JSON object body required")

    title = text(data, "title")
    typ = data.get("type", "Task")
    priority = data.get("priority", "Medium")
    points = data.get("story_points")

    if not title:
        return err("title is required")
    if len(title) > MAX_TITLE:
        return err("title is too long")
    # isinstance first: a list/dict here would crash `in` with HTTP 500 (TB-41)
    if not isinstance(typ, str) or typ not in TYPES:
        return err("invalid type")
    if not isinstance(priority, str) or priority not in PRIORITIES:
        return err("invalid priority")
    # bool is an int in Python, so reject True/False explicitly.
    if points is not None and (isinstance(points, bool)
                               or not isinstance(points, int)
                               or points not in POINTS):
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

    data = body()
    if data is None:
        return err("JSON object body required")

    uid = data.get("assignee_id")
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

    data = body()
    if data is None:
        return err("JSON object body required")

    text_body = text(data, "body")
    if not text_body:
        return err("comment cannot be empty")
    if len(text_body) > MAX_COMMENT:
        return err("comment is too long")

    comment = Comment(issue_id=iid, author_id=session["user_id"],
                      body=text_body)
    db.session.add(comment)
    db.session.commit()
    return jsonify(comment.to_dict()), 201