from datetime import date
from functools import wraps

from flask import Blueprint, jsonify, request, session

from . import db
from .models import (POINTS, PRIORITIES, STATUSES, TYPES, Comment, Issue,
                     Project, Sprint, User)

api = Blueprint('api', __name__)

EDITABLE = ('title', 'description', 'type', 'status', 'priority',
            'story_points', 'assignee_id', 'sprint_id')

@api.app_errorhandler(404)
def not_found(error):
    return jsonify(error='Not found'), 404

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify(error='Login required'), 401
        return f(*args, **kwargs)
    return wrapper

def body():
    return request.get_json(silent=True) or {}

# ---------- Auth ----------

@api.post('/register')
def register():
    d = body()
    name = str(d.get('name') or '').strip()
    email = str(d.get('email') or '').strip().lower()
    password = str(d.get('password') or '')
    if not name or '@' not in email or len(password) < 6:
        return jsonify(error='Name, valid email and password (min 6 characters) are required'), 400
    if User.query.filter_by(email=email).first():
        return jsonify(error='Email already registered'), 409
    user = User(name=name, email=email, role=d.get('role') or 'Developer')
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    session['user_id'] = user.id
    return jsonify(user.to_dict()), 201

@api.post('/login')
def login():
    d = body()
    email = str(d.get('email') or '').strip().lower()
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(str(d.get('password') or '')):
        return jsonify(error='Invalid email or password'), 401
    session['user_id'] = user.id
    return jsonify(user.to_dict())

@api.post('/logout')
def logout():
    session.clear()
    return jsonify(ok=True)

@api.get('/me')
@login_required
def me():
    return jsonify(db.session.get(User, session['user_id']).to_dict())

@api.get('/users')
@login_required
def users():
    return jsonify([u.to_dict() for u in User.query.order_by(User.name).all()])

# ---------- Projects ----------

@api.get('/projects')
@login_required
def list_projects():
    return jsonify([p.to_dict() for p in Project.query.order_by(Project.id).all()])

@api.post('/projects')
@login_required
def create_project():
    d = body()
    key = str(d.get('key') or '').strip().upper()
    name = str(d.get('name') or '').strip()
    if not (2 <= len(key) <= 10) or not key.isalpha() or not name:
        return jsonify(error='Key (2-10 letters) and name are required'), 400
    if Project.query.filter_by(key=key).first():
        return jsonify(error='Project key already exists'), 409
    project = Project(key=key, name=name, description=d.get('description') or '',
                      owner_id=session['user_id'])
    db.session.add(project)
    db.session.commit()
    return jsonify(project.to_dict()), 201

@api.delete('/projects/<int:pid>')
@login_required
def delete_project(pid):
    project = db.get_or_404(Project, pid)
    if project.owner_id != session['user_id']:
        return jsonify(error='Only the project owner can delete it'), 403
    db.session.delete(project)
    db.session.commit()
    return jsonify(ok=True)

# ---------- Issues ----------

def validate_issue(d, project, partial=False):
    errors = []
    if 'title' in d or not partial:
        if not str(d.get('title') or '').strip():
            errors.append('title is required')
    if 'type' in d and d['type'] not in TYPES:
        errors.append('invalid type')
    if 'status' in d and d['status'] not in STATUSES:
        errors.append('invalid status')
    if 'priority' in d and d['priority'] not in PRIORITIES:
        errors.append('invalid priority')
    if d.get('story_points') is not None and d['story_points'] not in POINTS:
        errors.append('story_points must be one of 1, 2, 3, 5, 8, 13')
    if d.get('assignee_id') is not None and db.session.get(User, d['assignee_id']) is None:
        errors.append('assignee not found')
    if d.get('sprint_id') is not None:
        sprint = db.session.get(Sprint, d['sprint_id'])
        if sprint is None or sprint.project_id != project.id:
            errors.append('sprint not found in this project')
    return errors

@api.get('/projects/<int:pid>/issues')
@login_required
def list_issues(pid):
    db.get_or_404(Project, pid)
    query = Issue.query.filter_by(project_id=pid)
    for field in ('status', 'type', 'assignee_id', 'sprint_id'):
        value = request.args.get(field)
        if value is None:
            continue
        if value == 'none':
            value = None
        elif field.endswith('_id'):
            value = int(value) if value.isdigit() else -1
        query = query.filter(getattr(Issue, field) == value)
    return jsonify([i.to_dict() for i in query.order_by(Issue.id).all()])

@api.post('/projects/<int:pid>/issues')
@login_required
def create_issue(pid):
    project = db.get_or_404(Project, pid)
    d = body()
    errors = validate_issue(d, project)
    if errors:
        return jsonify(error='; '.join(errors)), 400
    project.issue_counter += 1
    issue = Issue(
        key=f'{project.key}-{project.issue_counter}',
        project_id=project.id,
        sprint_id=d.get('sprint_id'),
        title=d['title'].strip(),
        description=d.get('description') or '',
        type=d.get('type', 'Task'),
        status=d.get('status', 'To Do'),
        priority=d.get('priority', 'Medium'),
        story_points=d.get('story_points'),
        assignee_id=d.get('assignee_id'),
        reporter_id=session['user_id'],
    )
    db.session.add(issue)
    db.session.commit()
    return jsonify(issue.to_dict()), 201

@api.get('/issues/<int:iid>')
@login_required
def get_issue(iid):
    return jsonify(db.get_or_404(Issue, iid).to_dict(detail=True))

@api.patch('/issues/<int:iid>')
@login_required
def update_issue(iid):
    issue = db.get_or_404(Issue, iid)
    d = {k: v for k, v in body().items() if k in EDITABLE}
    errors = validate_issue(d, issue.project, partial=True)
    if errors:
        return jsonify(error='; '.join(errors)), 400
    for key, value in d.items():
        setattr(issue, key, value.strip() if key == 'title' else value)
    db.session.commit()
    return jsonify(issue.to_dict())

@api.delete('/issues/<int:iid>')
@login_required
def delete_issue(iid):
    issue = db.get_or_404(Issue, iid)
    db.session.delete(issue)
    db.session.commit()
    return jsonify(ok=True)

@api.post('/issues/<int:iid>/comments')
@login_required
def add_comment(iid):
    issue = db.get_or_404(Issue, iid)
    text = str(body().get('body') or '').strip()
    if not text:
        return jsonify(error='Comment cannot be empty'), 400
    comment = Comment(issue_id=issue.id, author_id=session['user_id'], body=text)
    db.session.add(comment)
    db.session.commit()
    return jsonify(comment.to_dict()), 201

# ---------- Sprints ----------

@api.get('/projects/<int:pid>/sprints')
@login_required
def list_sprints(pid):
    db.get_or_404(Project, pid)
    sprints = Sprint.query.filter_by(project_id=pid).order_by(Sprint.id).all()
    return jsonify([s.to_dict() for s in sprints])

@api.post('/projects/<int:pid>/sprints')
@login_required
def create_sprint(pid):
    db.get_or_404(Project, pid)
    d = body()
    try:
        start = date.fromisoformat(str(d.get('start_date')))
        end = date.fromisoformat(str(d.get('end_date')))
    except ValueError:
        return jsonify(error='start_date and end_date must be in YYYY-MM-DD format'), 400
    name = str(d.get('name') or '').strip()
    if not name or end < start:
        return jsonify(error='Name is required and end_date cannot be before start_date'), 400
    sprint = Sprint(project_id=pid, name=name, start_date=start, end_date=end)
    db.session.add(sprint)
    db.session.commit()
    return jsonify(sprint.to_dict()), 201

@api.post('/sprints/<int:sid>/start')
@login_required
def start_sprint(sid):
    sprint = db.get_or_404(Sprint, sid)
    if sprint.completed:
        return jsonify(error='Sprint is already completed'), 400
    if Sprint.query.filter_by(project_id=sprint.project_id, active=True).first():
        return jsonify(error='Another sprint is already active'), 409
    sprint.active = True
    db.session.commit()
    return jsonify(sprint.to_dict())

@api.post('/sprints/<int:sid>/complete')
@login_required
def complete_sprint(sid):
    sprint = db.get_or_404(Sprint, sid)
    if not sprint.active:
        return jsonify(error='Sprint is not active'), 400
    for issue in Issue.query.filter_by(sprint_id=sprint.id).filter(Issue.status != 'Done'):
        issue.sprint_id = None
    sprint.active = False
    sprint.completed = True
    db.session.commit()
    return jsonify(sprint.to_dict())

@api.get('/sprints/<int:sid>/summary')
@login_required
def sprint_summary(sid):
    sprint = db.get_or_404(Sprint, sid)
    issues = Issue.query.filter_by(sprint_id=sprint.id).all()
    total = sum(i.story_points or 0 for i in issues)
    done = sum(i.story_points or 0 for i in issues if i.status == 'Done')
    by_status = {s: sum(1 for i in issues if i.status == s) for s in STATUSES}
    return jsonify(sprint=sprint.to_dict(), total_points=total,
                   done_points=done, by_status=by_status)
