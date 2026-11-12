"""Extra Sprint 2 API tests (TB-31, Member 3).

Sprints, the sprint summary and the board filter.

Checks the sprint API against the SRS (TB-F-016 to TB-F-020) and the test plan
(FR-10 to FR-13, TC-15 to TC-19). Covers what tests/test_sprints.py does not:
the SRS acceptance examples, every sprint status move, closed-sprint rules,
bad input that must give 4xx and never 500 (TB-NF-005), and the sprint/backlog
filter the board calls.

Known bugs are marked xfail(strict=True). When a bug is fixed its test starts
passing, strict mode turns that into a failure, and the marker must be removed.
"""
import sys

import pytest

from app import create_app


@pytest.fixture
def client():
    app = create_app({'TESTING': True,
                      'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
    with app.test_client() as c:
        yield c


@pytest.fixture
def safe_client():
    """Unhandled errors become HTTP 500, as a user would see them."""
    app = create_app({'TESTING': False, 'PROPAGATE_EXCEPTIONS': False,
                      'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
    with app.test_client() as c:
        yield c


def setup(c):
    c.post('/api/register',
           json={'name': 'Asha', 'email': 'a@test.com', 'password': 'secret1'})
    c.post('/api/projects', json={'key': 'TB', 'name': 'TaskBoard'})


def make_issue(c, pid=1, **fields):
    fields.setdefault('title', 'Issue')
    r = c.post('/api/projects/%d/issues' % pid, json=fields)
    return r.get_json()['id']


def make_sprint(c, pid=1, **fields):
    fields.setdefault('name', 'Sprint 1')
    return c.post('/api/projects/%d/sprints' % pid, json=fields)


def new_sprint(c, pid=1, **fields):
    return make_sprint(c, pid, **fields).get_json()['id']


def add(c, sid, iid):
    return c.post('/api/sprints/%d/issues' % sid, json={'issue_id': iid})


def set_status(c, iid, status):
    return c.patch('/api/issues/%d' % iid, json={'status': status})


def issues(c, query=''):
    return c.get('/api/projects/1/issues' + query).get_json()


def sprint_with_3_done_and_5_open(c):
    """SRS AC-F-019 example: a 3-point Done issue and a 5-point open issue."""
    sid = new_sprint(c)
    done = make_issue(c, title='Done one', story_points=3)
    open_ = make_issue(c, title='Open one', story_points=5)
    backlog = make_issue(c, title='Backlog one', story_points=8)
    add(c, sid, done)
    add(c, sid, open_)
    set_status(c, done, 'Done')
    return sid, done, open_, backlog


# ---------- TB-F-016 / FR-10: create a sprint (TC-15) ----------

def test_sprint_with_same_start_and_end_date_is_allowed(client):
    setup(client)
    r = make_sprint(client, start_date='2026-11-10', end_date='2026-11-10')
    assert r.status_code == 201


# AC-F-016
def test_reversed_dates_give_error_message(client):
    setup(client)
    r = make_sprint(client, start_date='2026-11-16', end_date='2026-11-10')
    assert r.status_code == 400
    assert 'before' in r.get_json()['error']
    assert client.get('/api/projects/1/sprints').get_json() == []


@pytest.mark.parametrize('value', ['2026-02-30', '2026-13-01', '', 'tomorrow'])
def test_impossible_dates_rejected(client, value):
    setup(client)
    assert make_sprint(client, start_date=value).status_code == 400


@pytest.mark.xfail(
    sys.version_info >= (3, 11), strict=True,
    reason='BUG-15: on Python 3.11+ date.fromisoformat also accepts 20261110 '
           'and 2026-W46-1, although the API says dates must be YYYY-MM-DD')
@pytest.mark.parametrize('value', ['20261110', '2026-W46-1'])
def test_only_yyyy_mm_dd_dates_accepted(client, value):
    setup(client)
    assert make_sprint(client, start_date=value).status_code == 400


def test_sprint_name_is_trimmed(client):
    setup(client)
    r = make_sprint(client, name='  Sprint 2  ')
    assert r.get_json()['name'] == 'Sprint 2'


def test_sprint_name_of_100_characters_is_allowed(client):
    setup(client)
    assert make_sprint(client, name='x' * 100).status_code == 201


def test_list_sprints_of_missing_project_returns_404(client):
    setup(client)
    assert client.get('/api/projects/99/sprints').status_code == 404


def test_sprints_are_listed_per_project(client):
    setup(client)
    client.post('/api/projects', json={'key': 'AB', 'name': 'Other'})
    new_sprint(client, pid=1, name='TB sprint')
    new_sprint(client, pid=2, name='AB sprint')
    sprints = client.get('/api/projects/2/sprints').get_json()
    assert [s['name'] for s in sprints] == ['AB sprint']


# ---------- FR-10: put issues into a sprint ----------

def test_issue_list_shows_sprint_id(client):
    setup(client)
    sid = new_sprint(client)
    iid = make_issue(client)
    add(client, sid, iid)
    assert issues(client)[0]['sprint_id'] == sid


def test_moving_issue_to_another_sprint(client):
    setup(client)
    one = new_sprint(client, name='One')
    two = new_sprint(client, name='Two')
    iid = make_issue(client, story_points=2)
    add(client, one, iid)
    assert add(client, two, iid).get_json()['sprint_id'] == two
    assert client.get('/api/sprints/%d' % one).get_json()['issue_count'] == 0
    assert client.get('/api/sprints/%d' % two).get_json()['story_points'] == 2


def test_issue_can_be_added_to_active_sprint(client):
    setup(client)
    sid = new_sprint(client)
    client.post('/api/sprints/%d/start' % sid)
    assert add(client, sid, make_issue(client)).status_code == 200


def test_cannot_remove_issue_from_completed_sprint(client):
    setup(client)
    sid = new_sprint(client)
    iid = make_issue(client)
    add(client, sid, iid)
    set_status(client, iid, 'Done')
    client.post('/api/sprints/%d/start' % sid)
    client.post('/api/sprints/%d/complete' % sid)
    r = client.delete('/api/sprints/%d/issues/%d' % (sid, iid))
    assert r.status_code == 409


def test_remove_issue_that_is_in_another_sprint_returns_404(client):
    setup(client)
    one = new_sprint(client, name='One')
    two = new_sprint(client, name='Two')
    iid = make_issue(client)
    add(client, one, iid)
    r = client.delete('/api/sprints/%d/issues/%d' % (two, iid))
    assert r.status_code == 404
    assert issues(client)[0]['sprint_id'] == one


def test_deleting_issue_updates_sprint_totals(client):
    setup(client)
    sid = new_sprint(client)
    iid = make_issue(client, story_points=5)
    add(client, sid, iid)
    assert client.delete('/api/issues/%d' % iid).status_code in (200, 204)
    s = client.get('/api/sprints/%d' % sid).get_json()
    assert (s['issue_count'], s['story_points']) == (0, 0)


@pytest.mark.parametrize('issue_id', [True, 1.0, [1], {'id': 1}, None])
def test_add_issue_with_bad_issue_id_returns_400(safe_client, issue_id):
    setup(safe_client)
    sid = new_sprint(safe_client)
    make_issue(safe_client)
    assert add(safe_client, sid, issue_id).status_code == 400


@pytest.mark.parametrize('url', ['/api/projects/1/sprints',
                                 '/api/sprints/1/issues'])
# TB-NF-005
def test_broken_json_returns_400_not_500(safe_client, url):
    setup(safe_client)
    new_sprint(safe_client)
    r = safe_client.post(url, data='{not json',
                         content_type='application/json')
    assert r.status_code == 400


# ---------- TB-F-017 / FR-11: start a sprint (TC-16) ----------

# AC-F-017
def test_second_start_gives_conflict_and_changes_nothing(client):
    setup(client)
    one = new_sprint(client, name='Sprint 1')
    two = new_sprint(client, name='Sprint 2')
    client.post('/api/sprints/%d/start' % one)
    r = client.post('/api/sprints/%d/start' % two)
    assert r.status_code == 409
    assert 'active' in r.get_json()['error']
    assert client.get('/api/sprints/%d' % one).get_json()['status'] == 'Active'
    r = client.get('/api/sprints/%d' % two)
    assert r.get_json()['status'] == 'Planned'


def test_start_keeps_planned_start_date(client):
    setup(client)
    sid = new_sprint(client, start_date='2026-11-10', end_date='2026-11-16')
    s = client.post('/api/sprints/%d/start' % sid).get_json()
    assert s['start_date'] == '2026-11-10'


def test_completed_sprint_cannot_be_started_again(client):
    setup(client)
    sid = new_sprint(client)
    client.post('/api/sprints/%d/start' % sid)
    client.post('/api/sprints/%d/complete' % sid)
    assert client.post('/api/sprints/%d/start' % sid).status_code == 409


@pytest.mark.parametrize('action', ['start', 'complete'])
def test_start_or_complete_missing_sprint_returns_404(client, action):
    setup(client)
    assert client.post('/api/sprints/99/%s' % action).status_code == 404


def test_remove_from_missing_sprint_returns_404(client):
    setup(client)
    make_issue(client)
    assert client.delete('/api/sprints/99/issues/1').status_code == 404


# ---------- TB-F-018 / FR-11: complete a sprint (TC-17) ----------

# AC-F-018
def test_complete_returns_every_unfinished_status_to_backlog(client):
    setup(client)
    sid = new_sprint(client)
    ids = {}
    for status in ['To Do', 'In Progress', 'In Review', 'Done']:
        ids[status] = make_issue(client, title=status)
        add(client, sid, ids[status])
        set_status(client, ids[status], status)
    client.post('/api/sprints/%d/start' % sid)

    s = client.post('/api/sprints/%d/complete' % sid).get_json()
    assert s['moved_to_backlog'] == 3
    by_id = {i['id']: i for i in issues(client)}
    assert by_id[ids['Done']]['sprint_id'] == sid
    for status in ['To Do', 'In Progress', 'In Review']:
        assert by_id[ids[status]]['sprint_id'] is None
        assert by_id[ids[status]]['status'] == status   # status is kept


def test_completed_sprint_keeps_only_done_points(client):
    setup(client)
    sid, *_ = sprint_with_3_done_and_5_open(client)
    client.post('/api/sprints/%d/start' % sid)
    s = client.post('/api/sprints/%d/complete' % sid).get_json()
    assert (s['issue_count'], s['story_points']) == (1, 3)


def test_complete_empty_sprint(client):
    setup(client)
    sid = new_sprint(client)
    client.post('/api/sprints/%d/start' % sid)
    r = client.post('/api/sprints/%d/complete' % sid)
    assert r.status_code == 200 and r.get_json()['moved_to_backlog'] == 0


def test_completed_sprint_cannot_be_completed_again(client):
    setup(client)
    sid = new_sprint(client)
    client.post('/api/sprints/%d/start' % sid)
    client.post('/api/sprints/%d/complete' % sid)
    assert client.post('/api/sprints/%d/complete' % sid).status_code == 409


# ---------- TB-F-019 / FR-12: sprint summary (TC-18) ----------

def test_sprint_total_points(client):
    setup(client)
    sid, *_ = sprint_with_3_done_and_5_open(client)
    s = client.get('/api/sprints/%d' % sid).get_json()
    assert (s['issue_count'], s['story_points']) == (2, 8)


# AC-F-019: 3 of 8
def test_sprint_summary_points(client):
    setup(client)
    sid, *_ = sprint_with_3_done_and_5_open(client)
    shown = issues(client, '?sprint_id=%d' % sid)    # what the board loads
    total = sum(i['story_points'] or 0 for i in shown)
    done = sum(i['story_points'] or 0 for i in shown if i['status'] == 'Done')
    assert (done, total) == (3, 8)


# ---------- TB-F-020 / FR-13: filter by sprint or backlog (TC-15, TC-19) ---

def test_unfiltered_list_still_returns_every_issue(client):
    setup(client)
    sprint_with_3_done_and_5_open(client)
    assert len(issues(client)) == 3


# AC-F-020
def test_filter_by_sprint_shows_only_its_issues(client):
    setup(client)
    sid, done, open_, backlog = sprint_with_3_done_and_5_open(client)
    shown = issues(client, '?sprint_id=%d' % sid)
    assert {i['id'] for i in shown} == {done, open_}


# AC-F-020
def test_filter_backlog_shows_only_issues_without_sprint(client):
    setup(client)
    sid, done, open_, backlog = sprint_with_3_done_and_5_open(client)
    assert [i['id'] for i in issues(client, '?sprint_id=none')] == [backlog]


def test_filter_by_sprint_with_no_issues_is_empty(client):
    setup(client)
    sprint_with_3_done_and_5_open(client)
    empty = new_sprint(client, name='Empty')
    assert issues(client, '?sprint_id=%d' % empty) == []


def test_filter_with_bad_sprint_id_returns_400(client):
    setup(client)
    sprint_with_3_done_and_5_open(client)
    r = client.get('/api/projects/1/issues?sprint_id=abc')
    assert r.status_code == 400
