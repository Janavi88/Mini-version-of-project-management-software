"""API tests for TB-13, TB-15, TB-17, TB-19, TB-20.
Each test name matches the Test Plan RTM (section 13.1)."""
import pytest

from app import create_app


@pytest.fixture
def client():
    # Fresh in-memory DB for every test.
    app = create_app({"TESTING": True,
                      "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.test_client() as c:
        yield c


def reg(c, email="a@test.com", pw="secret1"):
    return c.post("/api/register",
                  json={"name": "A", "email": email, "password": pw})


def make_project(c, key="TB"):
    return c.post("/api/projects", json={"name": "TaskBoard", "key": key})


def make_issue(c):
    make_project(c)
    return c.post("/api/projects/1/issues", json={"title": "x"})


# ---- TB-13 Register (TC-01, TC-02, TC-03) ----
def test_register_and_me(client):
    assert reg(client).status_code == 201
    assert client.get("/api/me").status_code == 200


def test_duplicate_email_rejected(client):
    reg(client)
    assert reg(client, email="A@TEST.com").status_code == 400


def test_short_password_rejected(client):
    assert reg(client, pw="abc").status_code == 400


# ---- TB-15 Create project (TC-07, TC-08) ----
def test_project_key_validation(client):
    reg(client)
    assert client.post("/api/projects",
                       json={"name": "P", "key": "1"}).status_code == 400
    r = make_project(client, key="tb")
    assert r.status_code == 201 and r.get_json()["key"] == "TB"


def test_duplicate_project_key(client):
    reg(client)
    make_project(client)
    assert make_project(client, key="tb").status_code == 400


# ---- TB-17 Create issue (TC-09, TC-10, TC-11) ----
def test_issue_keys_increment(client):
    reg(client)
    assert make_issue(client).get_json()["key"] == "TB-1"
    r = client.post("/api/projects/1/issues", json={"title": "y"})
    assert r.get_json()["key"] == "TB-2"


def test_issue_requires_title(client):
    reg(client)
    make_project(client)
    r = client.post("/api/projects/1/issues", json={"title": ""})
    assert r.status_code == 400


def test_invalid_story_points(client):
    reg(client)
    make_project(client)
    r = client.post("/api/projects/1/issues",
                    json={"title": "x", "story_points": 4})
    assert r.status_code == 400


# ---- TB-19 Assign issue (TC-14) ----
def test_assign_issue(client):
    reg(client)
    make_issue(client)
    r = client.patch("/api/issues/1/assignee", json={"assignee_id": 1})
    assert r.get_json()["assignee"] == "A"
    r = client.patch("/api/issues/1/assignee", json={"assignee_id": 99})
    assert r.status_code == 400


# ---- TB-20 Comment (TC-21, TC-22) ----
def test_comment_and_empty_comment(client):
    reg(client)
    make_issue(client)
    r = client.post("/api/issues/1/comments", json={"body": "hi"})
    assert r.status_code == 201 and r.get_json()["author"] == "A"
    r = client.post("/api/issues/1/comments", json={"body": "  "})
    assert r.status_code == 400


# ---- TB-SR-002 ----
def test_requires_login(client):
    assert client.post("/api/projects", json={}).status_code == 401
