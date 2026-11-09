# Deviations log (TB-32)

Every place where the built system, the process or the schedule differs from the
SRS v1.0, the SAD v1.0 or the Test Plan v1.0. Each entry is explained in the demo.

Checked against develop @ fd11327 and the open Sprint 2 PRs (#14, #15, #16) on 2026-11-09
by Member 3 (Harsh). Bug IDs are ours; the Jira key is in brackets.

**Type:** Design = API or data model differs from the SAD · Scope = a requirement is
missing or reduced · Process = testing or planning differs from the test plan ·
Doc = a document needs correcting.

| ID | Type | Document says | What is built / what happened | Impact and reason | Action / status |
|---|---|---|---|---|---|
| D-01 | Process | Test Plan §7: Sprint 1 manual pass on 29-Oct, regression 30-Oct | Sprint 1 UI testing was **suspended on 01-Nov** under Test Plan §12 (suspension criteria): the page was not served (GET / 404) and 7 endpoints were missing (BUG-01, BUG-02) | 6 cases blocked, 4 failed. Resumed after TB-36/37/38/39 merged on 03-Nov; full browser retest on 09-Nov passed 19/19 | Closed. Results in `docs/testing/Sprint2_Test_Results.md` |
| D-02 | Process | Test Plan §13.2: TC-10, TC-11, TC-14, TC-21, TC-22 are UI cases | In Sprint 1 they were run **through the API**, because the page had no create box or comment panel | The behaviour was still verified. In the 09-Nov retest TC-10, TC-11 and TC-14 were run in the UI; TC-21 and TC-22 stay API-only (see D-03) | Closed |
| D-03 | Doc | Test Plan TC-21, TC-22: "Open an issue and add a comment" (a UI step) | **Comments are API-only**; the UI has no comment panel or issue detail view | Allowed by SRS TB-F-015 ("a UI panel is optional") and SAD §4.5 (comment panel out of scope); only the test plan wording is wrong. TC-21 and TC-22 are run through the API | Test plan wording fixed (T-01) |
| D-04 | Design | SAD §4.3.4: assign through `PATCH /api/issues/{id}` with `assignee_id` | Both `PATCH /api/issues/{id}` (what the page uses) **and** the older `PATCH /api/issues/{id}/assignee` exist | No user impact. The extra route was kept so older tests and clients still work (TB-38) | Accepted |
| D-05 | Design | SAD §4.3.4–4.3.5: an issue joins a sprint through `sprint_id` on `POST`/`PATCH /issues`; `GET /api/sprints/{id}/summary`; Sprint has `active` and `completed` booleans | Issues join and leave through `POST /api/sprints/{sid}/issues` and `DELETE /api/sprints/{sid}/issues/{iid}`; extra `GET /api/sprints/{id}`; **no summary endpoint** (the page computes points itself); Sprint has one `status` field (Planned, Active, Completed) | Simpler API with one state field. The summary is only correct once the issue-list filter works (BUG-12 [TB-47]). The page still reads `active`/`completed` (BUG-14 [TB-49]) | Open until PR #16 merges and TB-47/TB-49 are fixed. Update SAD §4.3.5 |
| D-06 | Design | SAD §4.3.4: `GET /api/issues/{id}` returns the issue with its comments; SRS AC-F-011: a deleted issue's direct URL returns not found | `GET /api/issues/{id}` is **not implemented** (returns 405 for every id) | Comments can be added but never read back through the API. AC-F-011 cannot be checked as written | Open. Implement the endpoint or remove it from the SAD and reword AC-F-011 |
| D-07 | Scope | SRS TB-F-007 and TB-SR-005 (High / Medium): only the project owner can delete a project; others get 403. SAD §4.3.3 | **No `DELETE /api/projects/{id}`** endpoint (returns 404) | A Sprint 1 requirement and a security requirement are not met. Not caught in Sprint 1 because no test case in the test plan covered it (TC-Prj-05/06 had no TC-xx) | Open: BUG-16. xfail tests added |
| D-08 | Scope | SRS TB-F-013 (Sprint 1): filter issues by status, type, assignee and sprint (incl. backlog). SAD §4.3.4 query parameters | `GET /api/projects/{id}/issues` **ignores every query parameter** | No filter works through the API. The board's sprint filter is broken as a result (BUG-12 [TB-47]) | Open: BUG-17 (status, type, assignee) and BUG-12 [TB-47] (sprint). xfail tests added |
| D-09 | Design | SAD §4.3.4 issue object: `description`, `reporter_id`, `created_at`, `updated_at`; register returns `role` | The Issue model has none of these four fields; register returns `id`, `name`, `email` only | The SRS does not require them, so no requirement fails. `description` sent in a PATCH is silently ignored | Accepted for this release. Update the SAD issue object |
| D-10 | Scope | SRS TB-SR-008 and SAD §3.9: the secret key comes from an environment variable, not a default | Read from `SECRET_KEY`, but **falls back to `"dev"`** when it is not set (`app/__init__.py:16`) | Anyone who knows the default can forge a session on a shared deployment. Fine on localhost | Open: BUG-10 [TB-45] |
| D-11 | Scope | SAD §3.4 (CI/CD pipeline component), ADR-5 and §4.1 (repo layout): `Dockerfile` and `cd.yml` publishing a Docker image; SRS TB-NF-003 "and as a Docker image" | **No Dockerfile, no docker-compose, no CD workflow**; only `ci.yml` | TB-NF-003 (High) can only be partly met. Windows and Linux work without Docker | Open: [TB-51]. If the team drops Docker, record that here and in the SRS |
| D-12 | Process | SRS TB-NF-003: Windows, macOS and Linux; TB-NF-006: current browsers | Tested on Windows 11 (Python 3.11 and 3.13), Linux through CI (pytest only), Chromium only | macOS and Firefox/Safari are untested | Open: ask a teammate with a Mac; run TC-01..TC-14 in Firefox before the final regression |
| D-13 | Process | Test Plan §7 schedule | See the table below | The sprint plan slipped by about a week because the blocking Sprint 1 bugs were fixed only on 03-Nov and Sprint 2 code was pushed on 05–09 Nov | Recorded. Burndown and the final report use the real dates |
| D-14 | Scope | SRS TB-F-016..018, 020: "the system shall let a user" create, start and complete sprints and put issues into them | Only the API exists; the page has **no sprint controls** | Sprint planning is not possible for a normal user | Open: BUG-13 [TB-48] |
| D-15 | Doc | SRS TB-F-010 comment: "The UI edits status; other fields through the API" | The UI edit dialog (TB-18) edits title, type, priority, points and assignee | Positive deviation | SRS comment to be updated in the next revision |
| D-16 | Doc | Test Plan §13.1 RTM names 8 automated tests that do not exist, and marks FR-13 as "UI only" | The real test names differ; FR-13 now has API tests | Traceability was wrong, not the testing | Fixed in `docs/testing/Test_Plan_v1.1_Changes.md` (T-02) |
| D-17 | Doc | SRS uses test IDs TC-Auth-01, TC-Iss-03, …; the Test Plan uses TC-01..TC-27 | Two numbering schemes for the same cases | Hard to trace one to the other | Mapping table in `docs/testing/Test_Plan_v1.1_Changes.md` (T-03) |

## D-13 schedule: planned vs actual

| Activity | Planned (Test Plan §7) | Actual |
|---|---|---|
| Sprint 1 manual pass, bug tickets | 29-Oct | 01-Nov (BUG-01..BUG-11 filed) |
| Sprint 1 regression and summary | 30-Oct to 31-Oct | Report 01-Nov; retest of fixes 09-Nov |
| Sprint 2 test cases written (FR-10..FR-13) | 02-Nov | 09-Nov (`tests/test_sprints_extra.py`, PR #17) |
| Full regression, bugs raised | 03-Nov to 04-Nov | Sprint 2 bugs raised 09-Nov (BUG-12..BUG-17); full regression after PRs #14–#18 merge |
| NFR checks (TC-26, TC-27, flake8) | not dated | 09-Nov (PR #18) |
| Sprint 2 test summary | 07-Nov | Pending: final report after the regression |

## Bugs referenced

| Our ID | Jira | Title | Severity |
|---|---|---|---|
| BUG-10 | TB-45 | Secret key falls back to "dev" | Minor (Major if deployed) |
| BUG-12 | TB-47 | Board filter and sprint summary ignore the selected sprint | Major |
| BUG-13 | TB-48 | No UI to create, start or complete a sprint | Major |
| BUG-14 | TB-49 | Sprint filter never marks the active or completed sprint | Minor |
| BUG-16 | — | No endpoint to delete a project (owner only) | Major |
| BUG-17 | — | Issue list ignores status, type and assignee filters | Major |
| — | TB-51 | No Dockerfile: app cannot run as a Docker image | Major |
