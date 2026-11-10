"""Requirement gaps found while writing the deviations log (TB-31 / TB-32).

Sprint 1 requirements that the test plan v1.0 had no case for:
- TB-F-007 / TB-SR-005: only the owner can delete a project (BUG-16)
- TB-F-013: filter the issue list by status, type and assignee (fixed, TB-53)
- SAD 4.3.4: GET /api/issues/{id} returns the issue and its comments (D-06)

The tests still marked xfail(strict=True) are for features not built yet:
when the feature is built the test passes, strict mode fails the run, and the
marker must be removed in the same PR.
"""
import pytest

from app import create_app, db
from app.models import Issue, Project


@pytest.fixture
def app():
    return create_app({'TESTING': True,
                       'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})


@pytest.fixture
def client(app):
    with app.test_client() as c:
        yield c


def register(c, email='a@test.com', name='Asha'):
    return c.post('/api/register',
                  json={'name': name, 'email': email, 'password': 'secret1'})


def make_issue(c, **fields):
    fields.setdefault('title', 'Issue')
    return c.post('/api/projects/1/issues', json=fields).get_json()


def setup(c):
    register(c)
    c.post('/api/projects', json={'key': 'TB', 'name': 'TaskBoard'})


BUG_16 = pytest.mark.xfail(
    strict=True, reason='BUG-16: no DELETE /api/projects/{id} endpoint')


# ---------- TB-F-007 / TB-SR-005: delete a project (TC-28) ----------

@BUG_16
def test_owner_can_delete_project(app, client):
    setup(client)
    make_issue(client)
    r = client.delete('/api/projects/1')
    assert r.status_code == 200
    with app.app_context():
        assert db.session.get(Project, 1) is None
        assert Issue.query.count() == 0      # its issues are removed too


@BUG_16
def test_non_owner_delete_gets_403(app, client):
    setup(client)
    client.post('/api/logout')
    register(client, email='b@test.com', name='Ben')
    assert client.delete('/api/projects/1').status_code == 403
    with app.app_context():
        assert db.session.get(Project, 1) is not None


@BUG_16
def test_delete_project_requires_login(client):
    setup(client)
    client.post('/api/logout')
    assert client.delete('/api/projects/1').status_code == 401


@BUG_16
def test_delete_missing_project_returns_404_with_message(client):
    setup(client)
    r = client.delete('/api/projects/99')
    assert r.status_code == 404 and r.get_json()['error']


# ---------- TB-F-013: filter the issue list (fixed, TB-47 / TB-53) ----------

def keys(client, query):
    return [i['key'] for i in
            client.get('/api/projects/1/issues' + query).get_json()]


def test_filter_issues_by_status(client):
    setup(client)
    make_issue(client)
    done = make_issue(client)
    client.patch('/api/issues/%d' % done['id'], json={'status': 'Done'})
    assert keys(client, '?status=Done') == ['TB-2']


def test_filter_issues_by_type(client):
    setup(client)
    make_issue(client, type='Bug')
    make_issue(client, type='Story')
    assert keys(client, '?type=Bug') == ['TB-1']


def test_filter_issues_by_assignee(client):
    setup(client)
    me = client.get('/api/me').get_json()
    make_issue(client, assignee_id=me['id'])
    make_issue(client)
    assert keys(client, '?assignee_id=%d' % me['id']) == ['TB-1']
    assert keys(client, '?assignee_id=none') == ['TB-2']


def test_filters_combine(client):
    setup(client)
    make_issue(client, type='Bug')
    bug = make_issue(client, type='Bug')
    make_issue(client, type='Story')
    client.patch('/api/issues/%d' % bug['id'], json={'status': 'Done'})
    assert keys(client, '?type=Bug&status=Done') == ['TB-2']


def test_invalid_filter_value_returns_400(client):
    setup(client)
    make_issue(client)
    r = client.get('/api/projects/1/issues?status=Finished')
    assert r.status_code == 400


# ---------- SAD 4.3.4: GET /api/issues/{id} (D-06) ----------

@pytest.mark.xfail(strict=True,
                   reason='D-06: GET /api/issues/{id} is not implemented')
def test_get_issue_with_comments(client):
    setup(client)
    issue = make_issue(client)
    client.post('/api/issues/%d/comments' % issue['id'],
                json={'body': 'Looks good'})
    r = client.get('/api/issues/%d' % issue['id'])
    assert r.status_code == 200
    assert [c['body'] for c in r.get_json()['comments']] == ['Looks good']


@pytest.mark.xfail(strict=True,
                   reason='D-06: GET /api/issues/{id} is not implemented, '
                          'so a deleted issue gives 405, not 404 (AC-F-011)')
def test_deleted_issue_url_returns_404(client):
    setup(client)
    issue = make_issue(client)
    client.delete('/api/issues/%d' % issue['id'])
    assert client.get('/api/issues/%d' % issue['id']).status_code == 404