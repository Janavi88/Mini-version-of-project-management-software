# TaskBoard Final Test Summary Report

| | |
|---|---|
| Ticket | TB-31 (Member 3, QA) |
| Build tested | `develop` at `28b58d1` (after PRs #14 to #29 were merged) |
| Date | 12-11-2026 |
| Tester | Member 3 (Harsh) |
| Plan | TaskBoard Software Test Plan v1.0, with the v1.1 changes in `docs/testing/Test_Plan_v1.1_Changes.md` |

## 1. Summary

The Sprint 2 build works. Every bug filed in Sprint 1 and Sprint 2 is fixed and was retested. The full regression from a clean clone passed; one known gap is left (D-06).

| Count | Number |
|---|---|
| Manual test cases planned (TC-01 to TC-29) | 29 |
| Executed | 28 |
| Passed | 28 |
| Not run | 1 (TC-25, usability trial with 3 observers) |
| Automated tests | 171 passed, 0 failed, 2 expected failures (xfail) |
| Open bugs | 0 Critical, 0 Major, 0 Minor |
| Open deviations | D-06 (`GET /api/issues/{id}` missing) |

**Exit criteria (from the Test Plan)**

| Criterion | Met? |
|---|---|
| 100% of planned test cases executed | **No**: TC-25 (usability trial) not run yet |
| All automated tests pass in CI | Yes: CI is green on every merged PR |
| 0 Critical and 0 Major defects open | Yes |
| All Must-priority requirements verified | Yes, except the D-06 part of TB-F-011 (see §5) |
| Final test report produced | Yes (this document) |

**Verdict:** ready for the sprint review, with two things left before final sign-off: run TC-25, and merge `develop` into `main` (see §7).

## 2. Environment

| Item | Details |
|---|---|
| Clean clone | `git clone -b develop`, new virtual environment, `pip install -r requirements.txt` |
| Python | 3.11.9 (same as CI) for the clean-clone run; 3.13 on the developer copy |
| OS | Windows 11; Linux via GitHub Actions CI (ubuntu-latest) |
| Browsers | Chromium (the built-in browser pane, 800×600). For TC-29: Microsoft Edge 157, Firefox 150 and WebKit 26.4 (the Safari engine), driven by Playwright at 1280×800 |
| Docker | Docker Desktop, server 29.9.2 |
| Secret key | `SECRET_KEY` set to a test value (the app refuses to start without it, by design: TB-45) |

The manual regression and Docker check ran on `4b0252d`. PR #29 (TB-50) was merged afterwards; it only changes sprint date checks, so on `28b58d1` the automated tests were run again (on Python 3.11 and 3.13) and TB-50 was retested over the API.

## 3. Automated checks

| Check | Command | Result |
|---|---|---|
| Unit and API tests | `pytest -v` | **171 passed, 2 xfailed** (24 s) |
| Style | `flake8 app tests tools` | 19 findings: 10 in `app/`, 9 in `tests/test_sprints.py`. The extra blank lines in `tests/test_sprints_extra.py` and `tests/test_requirement_gaps.py` were fixed on this branch. |
| Performance, TC-26 | `python tools/perf_check.py` | **Pass**: 1000 issues, 200 of 200 list calls under 500 ms, p95 = 34.6 ms |

The 2 expected failures are a known gap that is not fixed yet:

| Test | Reason |
|---|---|
| `test_get_issue_with_comments` | D-06: `GET /api/issues/{id}` is not implemented |
| `test_deleted_issue_url_returns_404` | D-06: so a deleted issue's URL gives 405, not 404 (AC-F-011) |

## 4. Bug retest

Each fix was retested in the browser or over HTTP against the clean-clone build.

| Jira | Our ID | Bug | Severity | Retest on 12-Nov | Result |
|---|---|---|---|---|---|
| TB-45 | BUG-10 | Secret key falls back to "dev" | Minor | Without `SECRET_KEY` the app stops with "SECRET_KEY environment variable is not set" (also in Docker). With it, logins survive a restart. | **Fixed** |
| TB-46 | BUG-11 | README saved as UTF-16 | Minor | README is now plain UTF-8. The full README text is in PR #30, still open. | **Fixed** |
| TB-47 | BUG-12 | Filter and summary ignore the sprint | Major | Sprint with 3 points Done and 5 open shows "3 / 8 points done". Backlog shows only issues with no sprint. | **Fixed** |
| TB-48 | BUG-13 | No sprint UI | Major | **+ New sprint**, the Sprint box in **Edit**, **Start sprint** and **Complete sprint** all work. The buttons are disabled when the action is not allowed. | **Fixed** |
| TB-49 | BUG-14 | No active or completed label | Minor | The filter shows "Sprint 1 (active)", then "Sprint 1 (completed)". | **Fixed** |
| TB-50 | BUG-15 | Non YYYY-MM-DD dates accepted | Minor | Retested on `28b58d1` (PR #29): `20261110` and `2026-W46-1` give 400 "dates must be YYYY-MM-DD"; `2026-11-10` gives 201 | **Fixed** |
| TB-51 | — | No Dockerfile | Major | `docker build` works. `docker run -e SECRET_KEY=… -p 5077:5000` serves the page (200) and register works (201). | **Fixed** |
| TB-52 | BUG-16 | No project delete | Major | Owner gets 200 and the project and its issues are gone (404). Another user gets 403, logged out gets 401, and a second delete gives 404. API only, no UI button. | **Fixed** |
| TB-53 | BUG-17 | Status, type and assignee filters ignored | Major | `?status=`, `?type=`, `?assignee_id=` (also `none`) and combined filters return the right issues. A bad value gives 400. | **Fixed** |

## 5. Manual regression, TC-01 to TC-29

Run on a fresh database in the clean-clone build.

| TC | Area | Result | Notes |
|---|---|---|---|
| TC-01 | Register | Pass | Opens the board as Alice |
| TC-02 | Duplicate email | Pass | "email already registered" |
| TC-03 | Short password | Pass | "Password must be at least 6 characters." |
| TC-04 | Login | Pass | |
| TC-05 | Wrong password | Pass | "invalid email or password" |
| TC-06 | Logout | Pass | Login screen shown; `/api/me` gives 401 |
| TC-07 | Create project | Pass | "TB - TaskBoard" in the selector |
| TC-08 | Bad project key | Pass | "Project key must contain 2-10 letters."; nothing created |
| TC-09 | Create issue | Pass | TB-1 in To Do |
| TC-10 | Empty title | Pass | "Enter an issue title."; nothing created |
| TC-11 | Next key | Pass | TB-2 |
| TC-12 | Change status | Pass | Card moves to In Progress |
| TC-13 | Delete issue | Pass | Card gone after confirm |
| TC-14 | Assign teammate | Pass | Created with Bob as assignee |
| TC-15 | Sprint and filter | Pass | Created in the UI; issues added through **Edit**; only sprint issues shown (was Fail) |
| TC-16 | Start sprint | Pass | **Start sprint** button (was API only) |
| TC-17 | Complete sprint | Pass | **Complete sprint** button. The open issue went back to the backlog and the Done issue stayed. |
| TC-18 | Sprint summary | Pass | "3 / 8 points done" (was "3 / 16") |
| TC-19 | Backlog filter | Pass | Only issues not in a sprint (was Fail) |
| TC-20 | Script in title | Pass | Shown as plain text; script did not run |
| TC-21 | Add comment | Pass (API) | 201. No comment panel in the UI (D-03, allowed). |
| TC-22 | Empty comment | Pass (API) | 400 "comment cannot be empty" |
| TC-23 | Board columns | Pass | To Do, In Progress, In Review, Done |
| TC-24 | Edit issue | Pass | Title, priority and points saved and still shown after reload |
| TC-25 | Usability | **Not run** | Needs one new user and 3 observers; sheet in `docs/testing/TC-25_Usability_Sheet.md` |
| TC-26 | Performance | Pass | p95 34.6 ms (see §3) |
| TC-27 | Portability | Pass | Windows clean clone on Python 3.11, Linux CI, and Docker image all work. macOS not tested. |
| TC-28 | Delete project (owner only) | Pass | See TB-52 in §4 |
| TC-29 | Other browsers | Pass | TC-01 to TC-14, TC-20, TC-23 and TC-24 run through the UI in Edge 157, Firefox 150 and WebKit 26.4: 17 of 17 pass in each |

Reliability (TB-NF-005): after a server restart the user is still logged in and all 3 issues are still there.

## 6. New observations (not filed as bugs)

| # | Observation | Suggestion |
|---|---|---|
| O-1 | Without `SECRET_KEY` in the shell, `pytest` gives 168 errors (CI sets the key itself). The README in PR #30 should ask for the key before running the tests. | Optional: set a test key in a `tests/conftest.py` |
| O-2 | `.dockerignore` does not exclude `instance/`, so a local `taskboard.db` gets copied into the image when one exists. | Add `instance/` to `.dockerignore` |
| O-3 | The Docker container keeps its database inside the container, so data is lost when the container is removed. | README note, or `-v` volume for `instance/` |
| O-4 | The sprint name prompt and the project prompts use the browser's `prompt()` box, so there is no field for sprint dates in the UI. Dates can be set through the API. | Fine for this version; a form later |
| O-5 | After a page reload the board opens the first project in the list, not the one the user was last working in. | Remember the last project (for example in `localStorage`) |

## 7. Still to do before sign-off

| # | Item | Owner |
|---|---|---|
| 1 | Run TC-25, the usability trial | Member 3 with a new user and 3 observers |
| 2 | Build D-06 (`GET /api/issues/{id}`), or record it as a known limit | Backend (Member 1) |
| 3 | Merge PR #30 (README) | Janavi |
| 4 | Merge `develop` into `main` for the final release | Janavi |
| 5 | Clear the 19 remaining flake8 findings in `app/` and `tests/test_sprints.py` | Their authors |
| 6 | Regenerate the test plan PDF v1.1 and update SAD §4.3.4 and §4.3.5 | Member 4 |
