"""Sprints: TB-23 (create sprints, add issues) and TB-24 (start, complete)."""
from datetime import date

from flask import Blueprint, jsonify

from . import db
from .models import Issue, Project, Sprint
from .routes import MAX_NAME, body, err, login_required, text

sprints_bp = Blueprint("sprints", __name__, url_prefix="/api")


def parse_date(value):
    """None -> (None, True); 'YYYY-MM-DD' -> (date, True); else (None, False)."""
    if value is None:
        return None, True
    if not isinstance(value, str):
        return None, False
    try:
        return date.fromisoformat(value), True
    except ValueError:
        return None, False


# ---------------------------------------------------------------
# TB-23  Create sprints and add issues to them
# ---------------------------------------------------------------
@sprints_bp.post("/projects/<int:pid>/sprints")
@login_required
def create_sprint(pid):
    if not db.session.get(Project, pid):
        return err("project not found", 404)

    data = body()
    if data is None:
        return err("JSON object body required")

    name = text(data, "name")
    if not name:
        return err("sprint name is required")
    if len(name) > MAX_NAME:
        return err("sprint name is too long")

    start, ok_start = parse_date(data.get("start_date"))
    end, ok_end = parse_date(data.get("end_date"))
    if not (ok_start and ok_end):
        return err("dates must be YYYY-MM-DD")
    if start and end and end < start:
        return err("end date is before start date")

    sprint = Sprint(project_id=pid, name=name, start_date=start, end_date=end)
    db.session.add(sprint)
    db.session.commit()
    return jsonify(sprint.to_dict()), 201


@sprints_bp.get("/projects/<int:pid>/sprints")
@login_required
def list_sprints(pid):
    if not db.session.get(Project, pid):
        return err("project not found", 404)
    sprints = Sprint.query.filter_by(project_id=pid).order_by(Sprint.id).all()
    return jsonify([s.to_dict() for s in sprints])


@sprints_bp.get("/sprints/<int:sid>")
@login_required
def get_sprint(sid):
    sprint = db.session.get(Sprint, sid)
    if not sprint:
        return err("sprint not found", 404)
    return jsonify(sprint.to_dict())


@sprints_bp.post("/sprints/<int:sid>/issues")
@login_required
def add_issue_to_sprint(sid):
    sprint = db.session.get(Sprint, sid)
    if not sprint:
        return err("sprint not found", 404)

    data = body()
    if data is None:
        return err("JSON object body required")

    iid = data.get("issue_id")
    if isinstance(iid, bool) or not isinstance(iid, int):
        return err("issue_id is required")
    issue = db.session.get(Issue, iid)
    if not issue:
        return err("issue not found", 404)
    if issue.project_id != sprint.project_id:
        return err("issue belongs to a different project")
    if sprint.status == "Completed":
        return err("sprint is completed", 409)

    issue.sprint_id = sprint.id
    db.session.commit()
    return jsonify(issue.to_dict())


@sprints_bp.delete("/sprints/<int:sid>/issues/<int:iid>")
@login_required
def remove_issue_from_sprint(sid, iid):
    sprint = db.session.get(Sprint, sid)
    if not sprint:
        return err("sprint not found", 404)
    issue = db.session.get(Issue, iid)
    if not issue or issue.sprint_id != sid:
        return err("issue is not in this sprint", 404)
    if sprint.status == "Completed":
        return err("sprint is completed", 409)

    issue.sprint_id = None  # back to the backlog
    db.session.commit()
    return jsonify(issue.to_dict())


# ---------------------------------------------------------------
# TB-24  Start and complete a sprint
# ---------------------------------------------------------------
@sprints_bp.post("/sprints/<int:sid>/start")
@login_required
def start_sprint(sid):
    sprint = db.session.get(Sprint, sid)
    if not sprint:
        return err("sprint not found", 404)
    if sprint.status != "Planned":
        return err("only a planned sprint can be started", 409)
    if Sprint.query.filter_by(project_id=sprint.project_id,
                              status="Active").first():
        return err("project already has an active sprint", 409)

    sprint.status = "Active"
    if not sprint.start_date:
        sprint.start_date = date.today()
    db.session.commit()
    return jsonify(sprint.to_dict())


@sprints_bp.post("/sprints/<int:sid>/complete")
@login_required
def complete_sprint(sid):
    sprint = db.session.get(Sprint, sid)
    if not sprint:
        return err("sprint not found", 404)
    if sprint.status != "Active":
        return err("only an active sprint can be completed", 409)

    # Unfinished issues go back to the backlog; Done issues stay in the sprint.
    moved = 0
    for issue in list(sprint.issues):
        if issue.status != "Done":
            issue.sprint_id = None
            moved += 1

    sprint.status = "Completed"
    sprint.end_date = date.today()
    db.session.commit()

    result = sprint.to_dict()
    result["moved_to_backlog"] = moved
    return jsonify(result)