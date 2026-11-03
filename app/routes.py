"""REST API. Paths follow SAD section 4.3 and what static/app.js calls."""
import re
from functools import wraps

from flask import (Blueprint, current_app, jsonify, request, session)
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

from . import db
from .models import Comment, Issue, Project, User

bp = Blueprint("api", __name__, url_prefix="/api")
web = Blueprint("web", __name__)  # serves the web page at "/" (TB-36)

TYPES = {"Epic", "Story", "Task", "Bug"}
PRIORITIES = {"Low", "Medium", "High"}
STATUSES = {"To Do", "In Progress", "In Review", "Done"}
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


def valid_user_id(uid):
    """True if uid is an int (not bool) that belongs to an existing user."""
    return (not isinstance(uid, bool) and isinstance(uid, int)
            and db.session.get(User, uid) is not None)


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


# ---------------------------------------------------------------
# TB-37  Login / logout / current user / user list
# ---------------------------------------------------------------
@bp.post("/login")
def login():
    data = body()
    if data is None:
        return err("JSON object body required")

    email = text(data, "email").lower()
    password = data.get("password")

    user = (User.query.filter(func.lower(User.email) == email).first()
            if email else None)
    # Same message for unknown email and wrong password (TB-SR-007).
    if (not user or not isinstance(password, str)
            or not check_password_hash(user.password_hash, password)):
        return err("invalid email or password", 401)

    session["user_id"] = user.id
    return jsonify(id=user.id, name=user.name, email=user.email)


@bp.post("/logout")
def logout():
    session.clear()
    return jsonify(ok=True)


@bp.get("/me")
@login_required
def me():
    user = db.session.get(User, session["user_id"])
    return jsonify(id=user.id, name=user.name, email=user.email)


@bp.get("/users")
@login_required
def list_users():
    users = User.query.order_by(User.id).all()
    return jsonify([{"id": u.id, "name": u.name, "email": u.email}
                    for u in users])


# ---------------------------------------------------------------
# TB-15  Create a project with a unique key   (TB-F-005)
# TB-16  List projects                         (TB-F-006)
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


@bp.get("/projects")
@login_required
def list_projects():
    projects = Project.query.order_by(Project.id).all()
    return jsonify([{"id": p.id, "key": p.key, "name": p.name,
                     "owner_id": p.owner_id} for p in projects])


# ---------------------------------------------------------------
# TB-17  Create an issue with auto-generated key   (TB-F-008, TB-F-009)
# TB-37  List issues of a project                  (TB-F-013)
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


@bp.get("/projects/<int:pid>/issues")
@login_required
def list_issues(pid):
    if not db.session.get(Project, pid):
        return err("project not found", 404)
    issues = (Issue.query.filter_by(project_id=pid)
              .order_by(Issue.number).all())
    return jsonify([i.to_dict() for i in issues])


# ---------------------------------------------------------------
# TB-37 / TB-38  Edit an issue: status, title, type, priority,
#                story points and assignee in one PATCH
#                (TB-F-010, TB-F-012, which is what the web page calls)
# ---------------------------------------------------------------
@bp.patch("/issues/<int:iid>")
@login_required
def update_issue(iid):
    issue = db.session.get(Issue, iid)
    if not issue:
        return err("issue not found", 404)

    data = body()
    if data is None:
        return err("JSON object body required")

    # Validate everything first, apply only if all fields are valid.
    changes = {}

    if "title" in data:
        title = text(data, "title")
        if not title:
            return err("title is required")
        if len(title) > MAX_TITLE:
            return err("title is too long")
        changes["title"] = title

    if "status" in data:
        status = data["status"]
        if not isinstance(status, str) or status not in STATUSES:
            return err("invalid status")
        changes["status"] = status

    if "type" in data:
        typ = data["type"]
        if not isinstance(typ, str) or typ not in TYPES:
            return err("invalid type")
        changes["type"] = typ

    if "priority" in data:
        priority = data["priority"]
        if not isinstance(priority, str) or priority not in PRIORITIES:
            return err("invalid priority")
        changes["priority"] = priority

    if "story_points" in data:
        points = data["story_points"]
        if points is not None and (isinstance(points, bool)
                                   or not isinstance(points, int)
                                   or points not in POINTS):
            return err("story points must be one of 1, 2, 3, 5, 8, 13")
        changes["story_points"] = points

    if "assignee_id" in data:
        uid = data["assignee_id"]
        # null un-assigns; anything else must be an existing user id.
        if uid is not None and not valid_user_id(uid):
            return err("unknown user")
        changes["assignee_id"] = uid

    for field, value in changes.items():
        setattr(issue, field, value)
    db.session.commit()
    return jsonify(issue.to_dict())


@bp.delete("/issues/<int:iid>")
@login_required
def delete_issue(iid):
    issue = db.session.get(Issue, iid)
    if not issue:
        return err("issue not found", 404)
    # Remove its comments first so the delete cannot hit a foreign key error.
    Comment.query.filter_by(issue_id=iid).delete()
    db.session.delete(issue)
    db.session.commit()
    return jsonify(ok=True)


# ---------------------------------------------------------------
# TB-19  Assign an issue to a team member   (TB-F-012)
# Kept for the existing tests; the web page uses PATCH /issues/<id>.
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
    if uid is not None and not valid_user_id(uid):
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