"""Extra Sprint 1 API tests (TB-28, Member 3): auth, projects, issues, comments.

Covers what tests/test_api.py does not: security checks (Test Plan 5.1),
validation of every field, assignment, comments, persistence, malformed input,
and the endpoints the web page calls (login, logout, users, list projects,
list issues, edit issue, delete issue).

All known bugs (BUG-01, BUG-02, BUG-05 to BUG-09) are fixed, so no test
carries an xfail marker any more.
"""
import pytest

from app import create_app, db
from app.models import Comment, Issue, User


@pytest.fixture
def app():
    return create_app({'TESTING': True,
                       'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})


@pytest.fixture
def client(app):
    with app.test_client() as c:
        yield c


@pytest.fixture
def safe_client():
    """Client whose unhandled errors become HTTP 500 instead of exceptions,
    so a crash shows up as a status code, as it would for a real user."""
    app = create_app({'TESTING': False, 'PROPAGATE_EXCEPTIONS': False,
                      'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
    with app.test_client() as c:
        yield c


def register(c, email='a@test.com', name='Asha', password='secret1'):
    return c.post('/api/register',
                  json={'name': name, 'email': email, 'password': password})


def make_project(c, key='TB', name='TaskBoard'):
    return c.post('/api/projects', json={'key': key, 'name': name})


def make_issue(c, pid=1, **fields):
    fields.setdefault('title', 'Issue')
    return c.post('/api/projects/%d/issues' % pid, json=fields)


def setup_issue(c):
    register(c)
    make_project(c)
    return make_issue(c).get_json()


# ---------- Security (Test Plan 5.1) ----------

PROTECTED = [
    ('get', '/api/me'),
    ('get', '/api/users'),
    ('get', '/api/projects'),
    ('post', '/api/projects'),
    ('get', '/api/projects/1/issues'),
    ('post', '/api/projects/1/issues'),
    ('patch', '/api/issues/1'),
    ('delete', '/api/issues/1'),
    ('patch', '/api/issues/1/assignee'),
    ('post', '/api/issues/1/comments'),
]


@pytest.mark.parametrize('method,url', PROTECTED)
def test_every_protected_endpoint_requires_login(client, method, url):  # TB-SR-002
    assert getattr(client, method)(url, json={}).status_code == 401


def test_password_stored_only_as_hash(app, client):             # TB-SR-001
    register(client, password='secret1')
    with app.app_context():
        stored = User.query.first().password_hash
    assert 'secret1' not in stored
    assert stored.startswith(('scrypt:', 'pbkdf2:'))


def test_password_not_returned(client):
    for body in (register(client).get_json(), client.get('/api/me').get_json()):
        assert 'password' not in body and 'password_hash' not in body


def test_duplicate_email_rejected_ignoring_case(client):        # TB-F-002
    register(client, email='a@test.com')
    r = register(client, email='A@TEST.COM')
    assert r.status_code in (400, 409)
    assert 'already registered' in r.get_json()['error']


def test_email_stored_lowercase(client):
    assert register(client, email='Asha@Test.COM').get_json()['email'] == 'asha@test.com'


@pytest.mark.parametrize('payload', [
    {'email': 'b@test.com', 'password': 'secret1'},             # no name
    {'name': ' ', 'email': 'b@test.com', 'password': 'secret1'},
    {'name': 'B', 'email': 'no-at-sign', 'password': 'secret1'},
    {'name': 'B', 'email': 'b@test.com', 'password': '12345'},
])
def test_invalid_registration_rejected(client, payload):        # TB-F-001
    assert client.post('/api/register', json=payload).status_code == 400


def test_sql_injection_text_is_stored_as_plain_data(app, client):  # TB-SR-006
    evil = "x'); DROP TABLE issue; --"
    register(client)
    make_project(client)
    assert make_issue(client, title=evil).get_json()['title'] == evil
    make_issue(client, title='Second')
    with app.app_context():
        assert Issue.query.count() == 2


def test_script_title_is_stored_as_plain_text(client):           # TB-SR-004 (API side)
    register(client)
    make_project(client)
    title = '<script>alert(1)</script>'
    assert make_issue(client, title=title).get_json()['title'] == title


# ---------- Projects (TB-F-005) ----------

def test_project_key_stored_uppercase(client):
    register(client)
    assert make_project(client, 'tb').get_json()['key'] == 'TB'


def test_project_creator_is_owner(client):
    me = register(client).get_json()
    assert make_project(client).get_json()['owner_id'] == me['id']


@pytest.mark.parametrize('key', ['T', 'ABCDEFGHIJK', 'T1', 'T B', '', 'ÄÖ'])
def test_invalid_project_keys_rejected(client, key):
    register(client)
    assert make_project(client, key).status_code == 400


def test_project_name_required(client):
    register(client)
    assert make_project(client, name=' ').status_code == 400


# ---------- Issues (TB-F-008, TB-F-009) ----------

def test_issue_defaults(client):
    issue = setup_issue(client)
    assert (issue['type'], issue['priority'], issue['status']) == ('Task', 'Medium', 'To Do')
    assert issue['story_points'] is None and issue['assignee'] is None


def test_issue_title_is_trimmed(client):
    register(client)
    make_project(client)
    assert make_issue(client, title='  Login page  ').get_json()['title'] == 'Login page'


def test_issue_keys_are_numbered_per_project(client):
    register(client)
    make_project(client, 'TB')
    make_project(client, 'AB')
    make_issue(client, 1)
    make_issue(client, 1)
    assert make_issue(client, 2).get_json()['key'] == 'AB-1'
    assert make_issue(client, 1).get_json()['key'] == 'TB-3'


def test_issue_on_missing_project_returns_404(client):
    register(client)
    assert make_issue(client, 99).status_code == 404


@pytest.mark.parametrize('field,value', [
    ('type', 'Feature'), ('priority', 'Urgent'),
    ('story_points', 4), ('story_points', '3'), ('story_points', True),
])
def test_invalid_issue_fields_rejected_and_nothing_created(app, client, field, value):
    register(client)
    make_project(client)
    r = make_issue(client, **{field: value})
    assert r.status_code == 400 and 'error' in r.get_json()
    with app.app_context():
        assert Issue.query.count() == 0


@pytest.mark.parametrize('points', [1, 2, 3, 5, 8, 13])
def test_valid_story_points_accepted(client, points):
    register(client)
    make_project(client)
    assert make_issue(client, story_points=points).get_json()['story_points'] == points


# ---------- Assignment (TB-F-012) ----------

def test_assign_then_unassign(client):
    issue = setup_issue(client)
    me = client.get('/api/me').get_json()
    url = '/api/issues/%d/assignee' % issue['id']
    assert client.patch(url, json={'assignee_id': me['id']}).get_json()['assignee'] == 'Asha'
    assert client.patch(url, json={'assignee_id': None}).get_json()['assignee'] is None


@pytest.mark.parametrize('value', [999, 'abc', True, 1.5])
def test_assign_to_invalid_user_rejected(client, value):
    issue = setup_issue(client)
    r = client.patch('/api/issues/%d/assignee' % issue['id'], json={'assignee_id': value})
    assert r.status_code == 400


def test_assign_missing_issue_returns_404(client):
    register(client)
    assert client.patch('/api/issues/99/assignee', json={'assignee_id': 1}).status_code == 404


# ---------- Comments (TB-F-015) ----------

def test_comment_stores_author_and_time(client):                # TC-21
    issue = setup_issue(client)
    url = '/api/issues/%d/comments' % issue['id']
    c = client.post(url, json={'body': ' Looks good '}).get_json()
    assert (c['author'], c['body']) == ('Asha', 'Looks good') and c['created_at']


def test_whitespace_comment_rejected(app, client):               # TC-22
    issue = setup_issue(client)
    url = '/api/issues/%d/comments' % issue['id']
    assert client.post(url, json={'body': '   '}).status_code == 400
    with app.app_context():
        assert Comment.query.count() == 0


def test_comment_on_missing_issue_returns_404(client):
    register(client)
    assert client.post('/api/issues/99/comments', json={'body': 'hi'}).status_code == 404


# ---------- Reliability (TB-NF-005) ----------

def test_data_persists_across_restart(tmp_path):                # TC-Rel-01
    uri = 'sqlite:///%s' % (tmp_path / 'tb.db')
    first = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': uri})
    with first.test_client() as c:
        register(c)
        make_project(c)
        make_issue(c, title='Survives restart')
    with first.app_context():
        db.engine.dispose()
    second = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': uri})
    with second.app_context():
        assert Issue.query.one().title == 'Survives restart'


# ---------- Fixed bugs ----------

JSON_BODY_ENDPOINTS = [
    ('post', '/api/register'), ('post', '/api/projects'),
    ('post', '/api/projects/1/issues'), ('patch', '/api/issues/1/assignee'),
    ('post', '/api/issues/1/comments'),
]


@pytest.mark.parametrize('method,url', JSON_BODY_ENDPOINTS)
def test_non_object_json_body_returns_400(safe_client, method, url):   # BUG-05 / TB-40
    setup_issue(safe_client)
    assert getattr(safe_client, method)(url, json=[1]).status_code == 400


@pytest.mark.parametrize('field,value', [('type', ['Bug']), ('priority', ['High']),
                                         ('story_points', [3])])
def test_list_values_in_issue_fields_return_400(safe_client, field, value):  # BUG-06 / TB-41
    register(safe_client)
    make_project(safe_client)
    assert make_issue(safe_client, **{field: value}).status_code == 400


def test_malformed_email_rejected(client):                      # BUG-07 / TB-42
    assert register(client, email='@').status_code == 400


def test_overlong_title_rejected(client):                       # BUG-08 / TB-43
    register(client)
    make_project(client)
    assert make_issue(client, title='x' * 5000).status_code == 400


def test_overlong_comment_rejected(client):                     # BUG-08 / TB-43
    issue = setup_issue(client)
    r = client.post('/api/issues/%d/comments' % issue['id'], json={'body': 'y' * 5000})
    assert r.status_code == 400


def test_duplicate_email_returns_409(client):                   # BUG-09 / TB-44
    register(client)
    assert register(client).status_code == 409


def test_duplicate_project_key_returns_409(client):             # BUG-09 / TB-44
    register(client)
    make_project(client)
    assert make_project(client, 'tb').status_code == 409


def test_web_page_is_served(client):                            # BUG-01 / TB-36
    r = client.get('/')
    assert r.status_code == 200 and b'<html' in r.data.lower()


# ---------- Endpoints the web page calls (TB-37) ----------

def test_login_success_and_generic_error(client):               # TC-04, TC-05, TB-SR-007
    register(client)
    client.post('/api/logout')
    ok = client.post('/api/login', json={'email': 'a@test.com', 'password': 'secret1'})
    assert ok.status_code == 200
    unknown = client.post('/api/login', json={'email': 'nobody@test.com', 'password': 'secret1'})
    wrong = client.post('/api/login', json={'email': 'a@test.com', 'password': 'wrong!!'})
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.get_json() == wrong.get_json()


def test_logout_then_protected_call_returns_401(client):        # TC-06, TB-F-004
    register(client)
    assert client.post('/api/logout').status_code == 200
    assert client.get('/api/me').status_code == 401


def test_users_list(client):
    register(client)
    r = client.get('/api/users')
    assert r.status_code == 200
    assert [u['name'] for u in r.get_json()] == ['Asha']


def test_list_projects(client):                                 # TC-07, TB-F-006
    register(client)
    make_project(client)
    r = client.get('/api/projects')
    assert r.status_code == 200
    assert [p['key'] for p in r.get_json()] == ['TB']


def test_list_issues(client):                                   # TC-09, TB-F-013
    setup_issue(client)
    r = client.get('/api/projects/1/issues')
    assert r.status_code == 200
    assert [i['key'] for i in r.get_json()] == ['TB-1']


def test_list_issues_of_missing_project_returns_404(client):
    register(client)
    assert client.get('/api/projects/99/issues').status_code == 404


def test_change_status_and_edit(client):                        # TC-12, TC-24, TB-F-010
    issue = setup_issue(client)
    r = client.patch('/api/issues/%d' % issue['id'],
                     json={'status': 'In Progress', 'title': 'New', 'priority': 'High'})
    assert r.status_code == 200
    assert (r.get_json()['status'], r.get_json()['title']) == ('In Progress', 'New')


def test_invalid_status_rejected(client):
    issue = setup_issue(client)
    r = client.patch('/api/issues/%d' % issue['id'], json={'status': 'Flying'})
    assert r.status_code == 400


def test_invalid_edit_changes_nothing(client):
    issue = setup_issue(client)
    url = '/api/issues/%d' % issue['id']
    r = client.patch(url, json={'title': 'Changed', 'priority': 'Urgent'})
    assert r.status_code == 400
    # The valid title must not be applied when another field is invalid.
    issues = client.get('/api/projects/1/issues').get_json()
    assert issues[0]['title'] == 'Issue'


def test_edit_can_assign_and_unassign(client):                  # TB-38
    issue = setup_issue(client)
    me = client.get('/api/me').get_json()
    url = '/api/issues/%d' % issue['id']
    assert client.patch(url, json={'assignee_id': me['id']}).get_json()['assignee'] == 'Asha'
    assert client.patch(url, json={'assignee_id': None}).get_json()['assignee'] is None
    assert client.patch(url, json={'assignee_id': 999}).status_code == 400


def test_edit_missing_issue_returns_404(client):
    register(client)
    assert client.patch('/api/issues/99', json={'title': 'x'}).status_code == 404


def test_delete_issue(client):                                  # TC-13, TB-F-011
    issue = setup_issue(client)
    assert client.delete('/api/issues/%d' % issue['id']).status_code == 200
    assert client.patch('/api/issues/%d/assignee' % issue['id'],
                        json={'assignee_id': None}).status_code == 404


def test_delete_issue_removes_its_comments(app, client):
    issue = setup_issue(client)
    client.post('/api/issues/%d/comments' % issue['id'], json={'body': 'hi'})
    assert client.delete('/api/issues/%d' % issue['id']).status_code == 200
    with app.app_context():
        assert Comment.query.count() == 0