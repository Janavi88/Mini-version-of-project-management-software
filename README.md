# TaskBoard

A mini project-management tool for small teams: projects, issues, a Kanban board and sprints.
Built as a Software Engineering course project (Semester 5) with a full process around it:
protected branches, pull requests, CI, automated tests and documentation.

## Features

- **Accounts:** register, log in and log out. Passwords are stored as salted hashes.
- **Projects:** create a project with a unique key (stored in upper case) and switch between projects.
- **Issues:** create issues with an auto-generated key (for example `TB-12`), edit them, delete them and assign them to a team member. Each issue has a type, priority, status and optional story points.
- **Comments:** add comments to an issue (through the API).
- **Kanban board:** view issues in columns and change their status.
- **Sprints:** create sprints, add or remove issues, start and complete a sprint. Unfinished issues return to the backlog when a sprint is completed.
- **Filters:** filter the board by sprint or backlog, and see a sprint summary.

| Field | Allowed values |
|---|---|
| Issue type | Epic, Story, Task, Bug |
| Priority | Low, Medium, High |
| Status | To Do, In Progress, In Review, Done |
| Sprint status | Planned, Active, Completed |

## Tech stack

- Python 3.11, Flask 3.0, Flask-SQLAlchemy 3.1 (SQLite database)
- Plain HTML, CSS and JavaScript front end (in `static/`)
- Pytest for automated tests
- GitHub Actions for CI (runs the tests on Python 3.11 for every push and pull request)
- Docker for running the app as an image

## Getting started

### 1. Get the code

```bash
git clone https://github.com/Janavi88/Mini-version-of-project-management-software.git
cd Mini-version-of-project-management-software
git checkout develop
```

### 2. Install the dependencies

Python 3.11 or newer is recommended. A virtual environment keeps things tidy:

```bash
python -m venv .venv
```

Activate it:

- Windows (PowerShell): `.venv\Scripts\Activate.ps1`
- macOS / Linux: `source .venv/bin/activate`

Then install:

```bash
pip install -r requirements.txt
```

### 3. Set the secret key

The app signs login sessions with a secret key that is read from the `SECRET_KEY` environment variable. Use a long random string and never commit it.

Windows (PowerShell):

```powershell
$env:SECRET_KEY="replace-with-a-long-random-string"
```

macOS / Linux:

```bash
export SECRET_KEY="replace-with-a-long-random-string"
```

### 4. Run the app

```bash
python run.py
```

Open http://localhost:5000, register an account and create your first project. The SQLite database (`taskboard.db`) is created automatically on the first run.

## Run with Docker

Requires Docker Desktop (or Docker Engine).

```bash
docker build -t taskboard .
docker run -p 5000:5000 -e SECRET_KEY=replace-with-a-long-random-string taskboard
```

Then open http://localhost:5000. The secret key is passed at run time and is never baked into the image.

## Run the tests

```bash
pytest
```

Tests live in `tests/` and use an in-memory database, so they never touch your real data. The same command runs in CI on every push and pull request.

Performance check (1000 issues, 200 list calls, must stay under 500 ms for 95% of calls):

```bash
python tools/perf_check.py --issues 1000 --calls 200 --limit-ms 500
```

## API overview

All endpoints are under `/api` and return JSON. Every endpoint except register and login requires a logged-in session.

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/register` | Create an account (name, email, password) |
| POST | `/api/login` | Log in |
| POST | `/api/logout` | Log out |
| GET | `/api/me` | Current user |
| GET | `/api/users` | List users (for assigning issues) |
| POST | `/api/projects` | Create a project (name, unique key) |
| GET | `/api/projects` | List projects |
| POST | `/api/projects/{id}/issues` | Create an issue |
| GET | `/api/projects/{id}/issues` | List issues (filters: status, type, assignee, sprint) |
| PATCH | `/api/issues/{id}` | Edit an issue (title, type, priority, status, story points, assignee) |
| PATCH | `/api/issues/{id}/assignee` | Assign an issue (older route, kept for compatibility) |
| DELETE | `/api/issues/{id}` | Delete an issue |
| POST | `/api/issues/{id}/comments` | Add a comment |
| POST | `/api/projects/{id}/sprints` | Create a sprint (name, optional start and end date as `YYYY-MM-DD`) |
| GET | `/api/projects/{id}/sprints` | List a project's sprints |
| GET | `/api/sprints/{id}` | Get one sprint (with issue count and story points) |
| POST | `/api/sprints/{id}/issues` | Add an issue to a sprint |
| DELETE | `/api/sprints/{id}/issues/{issue_id}` | Remove an issue from a sprint (back to the backlog) |
| POST | `/api/sprints/{id}/start` | Start a sprint (only one active sprint per project) |
| POST | `/api/sprints/{id}/complete` | Complete a sprint |

Errors use clear status codes: `400` for invalid input, `401` when not logged in, `404` when something does not exist and `409` for conflicts such as a duplicate key or an invalid sprint state change.

## Project structure

```text
.
├── app/                  Flask application
│   ├── __init__.py       App factory (create_app), config, database setup
│   ├── models.py         User, Project, Sprint, Issue, Comment
│   ├── routes.py         Auth, projects, issues and comments endpoints
│   └── sprints.py        Sprint endpoints
├── static/               Web page (index.html, app.js, style.css)
├── tests/                Automated tests (pytest)
├── tools/perf_check.py   Performance check script
├── docs/                 Deviations log and test results
├── .github/              CI workflow and pull request template
├── run.py                Entry point: python run.py
├── requirements.txt      Python dependencies
└── Dockerfile            Container image
```

## Documentation

- Software Requirements Specification: `TaskBoard SRS (Software Requirements Specification).docx`
- Software Architecture Document: `TaskBoard_SAD.pdf`
- Test Plan: `TaskBoard_Test_Plan.pdf`
- Deviations from the plan: `docs/deviations.md`
- Test results: `docs/testing/`

## Team workflow

- Work is tracked on the Jira board (project key `TB`).
- `develop` and `main` are protected: every change goes through a feature branch and a pull request, and CI must pass before merging.
- Branch names include the ticket, for example `fix/TB-45-secret-key`, and commit messages start with the ticket key.

## Team

| Name | Focus |
|---|---|
| Janavi Agrawal | Process and setup, CI/CD, release |
| Bhoomika Kshatriya | Backend: auth, projects, issues |
| Deana Naveen A | Front end: board and sprint UI |
| Harsh Agarwal | Testing and documentation |

## Known limitations

These are tracked in `docs/deviations.md` and on the Jira board:

- Comments can be added through the API, but there is no comment panel in the web page.
- There is no endpoint to fetch a single issue by id.
- Only the Windows and Linux setups are tested; macOS and browsers other than Chromium are untested.
