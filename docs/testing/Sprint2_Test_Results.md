# Sprint 2 test results (TB-31)

Tester: Member 3 (Harsh). Date: 2026-11-09.
Environment: Windows 11, Python 3.13.7, Chromium, `python run.py` with a fresh database.

## 1. Sprint 1 retest on develop @ fd11327

`pytest`: 92 passed, 0 failed.

| TC | Req | Result | Notes |
|---|---|---|---|
| TC-01 | FR-01 | Pass | Register opens the board |
| TC-02 | FR-01 | Pass | "email already registered" |
| TC-03 | FR-01 | Pass | "Password must be at least 6 characters." |
| TC-04 | FR-02 | Pass | Was Fail in Sprint 1 |
| TC-05 | FR-02 | Pass | "invalid email or password". Was Fail |
| TC-06 | FR-02 | Pass | Logout + reload shows login. Was Fail |
| TC-07 | FR-03 | Pass | Project appears in the dropdown. Was Fail |
| TC-08 | FR-03 | Pass | "Project key must contain 2-10 letters." |
| TC-09 | FR-04 | Pass | TB-1 in To Do. Was Blocked |
| TC-10 | FR-04 | Pass | Page and API reject an empty title |
| TC-11 | FR-04 | Pass | Second issue is TB-2 |
| TC-12 | FR-06 | Pass | Status dropdown moves the card. Was Blocked |
| TC-13 | FR-07 | Pass | Delete with confirm. Was Blocked |
| TC-14 | FR-08 | Pass | Assign through the edit dialog |
| TC-20 | NFR-03 | Pass | Script tag in a title is shown as plain text. Was Blocked |
| TC-21 | FR-09 | Pass (API) | No comment panel in the UI (see deviations) |
| TC-22 | FR-09 | Pass (API) | 400 "comment cannot be empty" |
| TC-23 | FR-05 | Pass | All four columns. Was Blocked |
| TC-24 | FR-07 | Pass | Edit saved and still shown after reload. Was Blocked |

19 executed, 19 passed. BUG-01 to BUG-09 verified fixed. BUG-10 (SECRET_KEY fallback) and
BUG-11 (README saved as UTF-16) are still open.

## 2. Sprint 2 cases

Run on a local, never-pushed branch that merges develop @ fd11327 with
`TB-23-24-sprints` @ 7516652, `TB-25-sprint-summary` @ fb1ba55 and
`feature/TB-26-filter-board` @ 84e42ca. `pytest` there: 120 passed.
With `tests/test_sprints_extra.py` added: 155 passed, 7 xfailed (known bugs).

| TC | Req | Result | What was seen |
|---|---|---|---|
| TC-15 | FR-10 | Fail | No way to create a sprint or put an issue into one in the UI (BUG-13). Through the API the issue joins the sprint, but choosing that sprint in the filter still shows every issue (BUG-12) |
| TC-16 | FR-11 | Pass (API) | Second start returns 409 "project already has an active sprint". No Start button in the UI (BUG-13) |
| TC-17 | FR-11 | Pass (API) | To Do issue returns to the backlog, Done issue stays, `moved_to_backlog: 1`. No Complete button in the UI (BUG-13) |
| TC-18 | FR-12 | Fail | Sprint with 3 done + 5 open points shows "3 / 16 points done", because it counts every issue in the project (BUG-12) |
| TC-19 | FR-13 | Fail | Backlog filter still shows issues that are in a sprint (BUG-12) |

The filter label also never shows "(active)" or "(completed)" (BUG-14).

## 3. New automated tests

`tests/test_sprints_extra.py`: 42 tests against TB-F-016 to TB-F-020.
35 pass. 7 are `xfail(strict=True)` and point at a bug:

| Test | Bug |
|---|---|
| `test_sprint_summary_points` | BUG-12 |
| `test_filter_by_sprint_shows_only_its_issues` | BUG-12 |
| `test_filter_backlog_shows_only_issues_without_sprint` | BUG-12 |
| `test_filter_by_sprint_with_no_issues_is_empty` | BUG-12 |
| `test_filter_with_bad_sprint_id_returns_400` | BUG-12 |
| `test_only_yyyy_mm_dd_dates_accepted` (2 cases) | BUG-15 |

When a bug is fixed, its tests start passing and strict mode fails the run until the marker is removed.

## 4. Sprint 2 bugs

### BUG-12: Board filter and sprint summary ignore the selected sprint
Severity: Major. Area: backend, issue list (FR-12, FR-13).

Steps to reproduce:
1. Create a project with three issues (3, 5 and 8 points).
2. Through the API, create Sprint 1 and add the 3 and 5 point issues. Mark the 3 point issue Done.
3. Reload the page and choose "Sprint 1" in the Show filter, then "Backlog".

Expected result: Sprint 1 shows two issues and "3 / 8 points done". Backlog shows only the 8 point issue (AC-F-019, AC-F-020).
Actual result: every choice shows all three issues and "3 / 16 points done".
Cause: the page calls `GET /api/projects/{id}/issues?sprint_id=1` (or `?sprint_id=none`), but `list_issues` in `app/routes.py` ignores the query string.
Suggested fix: in `list_issues`, read `request.args.get("sprint_id")`: `none` filters `sprint_id IS NULL`, a number filters that sprint, anything else returns 400.
Environment: integration of develop @ fd11327 + the three Sprint 2 branches, Chromium, Windows 11.

### BUG-13: No UI to create, start or complete a sprint or to put an issue into a sprint
Severity: Major. Area: frontend (FR-10, FR-11).

Steps to reproduce: log in, open a project, look for sprint controls.
Expected result: a user can create a sprint, add issues to it, start it and complete it from the page (TB-F-016, 017, 018, 020 say "the system shall let a user").
Actual result: the page only has the Show filter and the points summary. `static/app.js` never calls `POST /sprints`, `/sprints/{id}/issues`, `/start` or `/complete`. TC-15 to TC-17 can only be run through the API.
Suggested fix: a "New sprint" button (name + dates), Start / Complete buttons for the selected sprint, and a sprint dropdown in the create and edit issue forms.
Environment: as BUG-12.

### BUG-14: Sprint filter never marks the active or completed sprint
Severity: Minor. Area: frontend.

Steps to reproduce: start Sprint 2 and complete Sprint 1 through the API, reload the page, open the Show filter.
Expected result: "Sprint 2 (active)", "Sprint 1 (completed)".
Actual result: "Sprint 1", "Sprint 2".
Cause: `loadSprints` reads `sprint.active` and `sprint.completed`, but the API returns `status: "Active" | "Completed"`.
Suggested fix: use `sprint.status === 'Active'` and `sprint.status === 'Completed'`.
Environment: as BUG-12.

### BUG-15: Sprint dates in other formats are accepted on Python 3.11+
Severity: Minor. Area: backend, create sprint (FR-10).

Steps to reproduce: `POST /api/projects/1/sprints` with `{"name": "S", "start_date": "20261110"}` (or `"2026-W46-1"`).
Expected result: 400 "dates must be YYYY-MM-DD".
Actual result: 201 on Python 3.11 and newer (CI uses 3.11). Python 3.10 rejects it, so behaviour differs between supported versions (TB-NF-003).
Suggested fix: in `parse_date`, also check `re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)` before `date.fromisoformat`.
Environment: Python 3.13.7 locally, 3.11 in CI.

## 5. Observation (not filed)

Every logged-in user sees every project (a second user saw the first user's project straight after
registering). The SRS does not mention project membership, so this is noted for the deviations log
rather than raised as a bug.
