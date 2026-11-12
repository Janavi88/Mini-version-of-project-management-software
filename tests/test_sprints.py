"""Sprint tests: TB-23 (create sprints, add issues) and TB-24 (start, complete)."""
import pytest

from app import create_app


@pytest.fixture
def client():
    app = create_app({"TESTING": True,
                      "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.test_client() as c:
        yield c


def register(c):
    return c.post("/api/register",
                  json={"name": "A", "email": "a@test.com", "password": "secret1"})


def make_project(c, key="TB"):
    return c.post("/api/projects", json={"name": "TaskBoard", "key": key})


def make_issue(c, pid=1, **fields):
    fields.setdefault("title", "Issue")
    return c.post("/api/projects/%d/issues" % pid, json=fields)


def make_sprint(c, pid=1, **fields):
    fields.setdefault("name", "Sprint 1")
    return c.post("/api/projects/%d/sprints" % pid, json=fields)


def setup(c):
    register(c)
    make_project(c)


PROTECTED = [
    ("post", "/api/projects/1/sprints"),
    ("get", "/api/projects/1/sprints"),
    ("get", "/api/sprints/1"),
    ("post", "/api/sprints/1/issues"),
    ("delete", "/api/sprints/1/issues/1"),
    ("post", "/api/sprints/1/start"),
    ("post", "/api/sprints/1/complete"),
]


@pytest.mark.parametrize("method,url", PROTECTED)
def test_sprint_endpoints_require_login(client, method, url):    # TB-SR-002
    assert getattr(client, method)(url, json={}).status_code == 401


# ---------- TB-23 ----------

def test_create_sprint_defaults_to_planned(client):
    setup(client)
    r = make_sprint(client)
    assert r.status_code == 201
    s = r.get_json()
    assert (s["name"], s["status"], s["issue_count"]) == ("Sprint 1", "Planned", 0)
    assert s["start_date"] is None and s["end_date"] is None


def test_create_sprint_with_dates(client):
    setup(client)
    s = make_sprint(client, start_date="2026-11-10", end_date="2026-11-16").get_json()
    assert (s["start_date"], s["end_date"]) == ("2026-11-10", "2026-11-16")


@pytest.mark.parametrize("fields", [
    {"name": " "}, {"name": "x" * 101}, {"name": 5},
    {"start_date": "10/11/2026"}, {"end_date": 20261116},
    {"start_date": "2026-11-16", "end_date": "2026-11-10"},
])
def test_invalid_sprint_rejected(client, fields):
    setup(client)
    assert make_sprint(client, **fields).status_code == 400


def test_sprint_non_object_body_returns_400(client):
    setup(client)
    assert client.post("/api/projects/1/sprints", json=[1]).status_code == 400


def test_sprint_on_missing_project_returns_404(client):
    register(client)
    assert make_sprint(client, pid=99).status_code == 404


def test_list_and_get_sprints(client):
    setup(client)
    make_sprint(client, name="One")
    make_sprint(client, name="Two")
    r = client.get("/api/projects/1/sprints")
    assert [s["name"] for s in r.get_json()] == ["One", "Two"]
    assert client.get("/api/sprints/2").get_json()["name"] == "Two"
    assert client.get("/api/sprints/99").status_code == 404


def test_add_issue_to_sprint(client):
    setup(client)
    sid = make_sprint(client).get_json()["id"]
    iid = make_issue(client, story_points=3).get_json()["id"]
    r = client.post("/api/sprints/%d/issues" % sid, json={"issue_id": iid})
    assert r.status_code == 200 and r.get_json()["sprint_id"] == sid
    s = client.get("/api/sprints/%d" % sid).get_json()
    assert (s["issue_count"], s["story_points"]) == (1, 3)


def test_new_issue_starts_in_backlog(client):
    setup(client)
    assert make_issue(client).get_json()["sprint_id"] is None


def test_add_issue_rejects_bad_input(client):
    setup(client)
    make_project(client, key="AB")
    sid = make_sprint(client).get_json()["id"]
    other = make_issue(client, pid=2).get_json()["id"]
    url = "/api/sprints/%d/issues" % sid
    assert client.post(url, json={"issue_id": other}).status_code == 400   # other project
    assert client.post(url, json={"issue_id": 99}).status_code == 404
    assert client.post(url, json={"issue_id": "1"}).status_code == 400
    assert client.post(url, json={}).status_code == 400
    assert client.post("/api/sprints/99/issues", json={"issue_id": 1}).status_code == 404


def test_remove_issue_from_sprint(client):
    setup(client)
    sid = make_sprint(client).get_json()["id"]
    iid = make_issue(client).get_json()["id"]
    client.post("/api/sprints/%d/issues" % sid, json={"issue_id": iid})
    r = client.delete("/api/sprints/%d/issues/%d" % (sid, iid))
    assert r.status_code == 200 and r.get_json()["sprint_id"] is None
    assert client.delete("/api/sprints/%d/issues/%d" % (sid, iid)).status_code == 404


# ---------- TB-24 ----------

def test_start_sprint(client):
    setup(client)
    sid = make_sprint(client).get_json()["id"]
    r = client.post("/api/sprints/%d/start" % sid)
    assert r.status_code == 200
    s = r.get_json()
    assert s["status"] == "Active" and s["start_date"]


def test_only_one_active_sprint_per_project(client):
    setup(client)
    first = make_sprint(client, name="One").get_json()["id"]
    second = make_sprint(client, name="Two").get_json()["id"]
    assert client.post("/api/sprints/%d/start" % first).status_code == 200
    assert client.post("/api/sprints/%d/start" % second).status_code == 409


def test_active_sprints_in_different_projects_are_independent(client):
    setup(client)
    make_project(client, key="AB")
    a = make_sprint(client, pid=1).get_json()["id"]
    b = make_sprint(client, pid=2).get_json()["id"]
    assert client.post("/api/sprints/%d/start" % a).status_code == 200
    assert client.post("/api/sprints/%d/start" % b).status_code == 200


def test_cannot_start_twice_or_complete_a_planned_sprint(client):
    setup(client)
    sid = make_sprint(client).get_json()["id"]
    assert client.post("/api/sprints/%d/complete" % sid).status_code == 409
    client.post("/api/sprints/%d/start" % sid)
    assert client.post("/api/sprints/%d/start" % sid).status_code == 409


def test_complete_moves_unfinished_issues_to_backlog(client):
    setup(client)
    sid = make_sprint(client).get_json()["id"]
    done = make_issue(client).get_json()["id"]
    open_ = make_issue(client).get_json()["id"]
    for iid in (done, open_):
        client.post("/api/sprints/%d/issues" % sid, json={"issue_id": iid})
    client.patch("/api/issues/%d" % done, json={"status": "Done"})
    client.post("/api/sprints/%d/start" % sid)

    r = client.post("/api/sprints/%d/complete" % sid)
    assert r.status_code == 200
    s = r.get_json()
    assert s["status"] == "Completed" and s["end_date"]
    assert s["moved_to_backlog"] == 1 and s["issue_count"] == 1

    issues = {i["id"]: i for i in client.get("/api/projects/1/issues").get_json()}
    assert issues[done]["sprint_id"] == sid
    assert issues[open_]["sprint_id"] is None


def test_completed_sprint_is_closed_and_next_one_can_start(client):
    setup(client)
    first = make_sprint(client, name="One").get_json()["id"]
    second = make_sprint(client, name="Two").get_json()["id"]
    iid = make_issue(client).get_json()["id"]
    client.post("/api/sprints/%d/start" % first)
    client.post("/api/sprints/%d/complete" % first)
    assert client.post("/api/sprints/%d/issues" % first,
                       json={"issue_id": iid}).status_code == 409
    assert client.post("/api/sprints/%d/start" % second).status_code == 200