# Non-functional test results (TB-31)

Tester: Member 3 (Harsh). Date: 2026-11-09. Build: develop @ fd11327 unless stated.

| TC | Req | Result | Summary |
|---|---|---|---|
| TC-26 | NFR-02 / TB-NF-001 performance | **Pass** | 1000 issues: 200 of 200 list calls under 500 ms; p95 = 28.5 ms |
| — | NFR-04 / TB-NF-004 maintainability | **Partly** | `tests/` and `tools/` are flake8-clean after this PR. `app/` has 5 style findings left (owner: backend). Every endpoint has a test and CI is green |
| TC-27 | NFR-05 / TB-NF-003 portability | **Partly** | Windows clean clone: pytest 92 passed on Python 3.13 and 3.11, the app starts and TC-01..TC-11 pass. Linux: CI (ubuntu-latest, Python 3.11) green. macOS and Docker not tested; there is no Dockerfile |
| — | TB-NF-005 reliability | **Pass** | Data still there after a server restart; bad input returns 4xx (API tests) |
| TC-25 | NFR-01 / TB-NF-002 usability | **Not run yet** | Needs 3 observers and a new user. Sheet: `docs/testing/TC-25_Usability_Sheet.md` |

## TC-26 performance (TB-NF-001)

Script: `tools/perf_check.py` (the "performance seed script" from the test plan).
It starts the real app on a temporary SQLite file, seeds the issues through `POST /api/projects/{id}/issues`,
then times `GET /api/projects/{id}/issues` over real HTTP.

```
python tools/perf_check.py --issues 1000 --calls 200 --limit-ms 500
```

```
Machine: Windows-11-10.0.26300-SP0, Python 3.13.7
POST issue (seeding)         n=1000  p50=   11.4 ms  p95=   15.5 ms  max=  226.5 ms
GET issue list (1000 issues) n=200   p50=   14.6 ms  p95=   28.5 ms  max=   43.6 ms
List calls under 500 ms: 200 of 200 (100.0%), need 95%
TC-26 result: PASS
```

Three runs gave p95 between 24 and 30 ms for the list call. Laptop: Windows 11 Home, run with the debug server
(`threaded=True`), so a production server would be at least as fast.

## NFR-04 flake8 (PEP 8)

flake8 7.5.0 with default settings (79-character lines).

| Location | Before | After this PR | Notes |
|---|---|---|---|
| `tests/test_api_extra.py` | 40 | 0 | Long lines wrapped; no test changed what it checks (92 still pass) |
| `tests/test_api.py` | 1 | 0 | Missing newline at end of file |
| `tools/perf_check.py` | new | 0 | |
| `app/__init__.py` | 1 | 1 | W292 no newline at end of file |
| `app/models.py` | 3 | 3 | E501 lines 21, 28, 29 |
| `app/routes.py` | 1 | 1 | W292 no newline at end of file |

App code was not changed (tester PR). Sprint 2 branches add more: `app/sprints.py` 2,
`app/models.py` 7 (on `TB-23-24-sprints`), `tests/test_sprints.py` 9. Suggested follow-up: add a
`flake8 app tests tools` step to `.github/workflows/ci.yml` so CI enforces NFR-04.

## TC-27 portability (TB-NF-003)

| Check | Windows 11, Python 3.13.7 | Windows 11, Python 3.11.9 | Linux (CI ubuntu-latest, Python 3.11) |
|---|---|---|---|
| Fresh `git clone` of develop, `pip install -r requirements.txt` | Pass | Pass | Pass |
| `pytest` | 92 passed | 92 passed | Green (every develop push and PR) |
| `python run.py` starts, `GET /` serves the page | Pass | not run | not run |
| TC-01..TC-11 over HTTP against the running app | 11/11 Pass | not run | covered by API tests only |
| Data kept after restart | Pass | not run | not run |

Not covered: macOS (no team member has checked yet), Docker (no Dockerfile in the repo, although TB-NF-003
says "and as a Docker image"), and a manual browser run on Linux. These go in `docs/deviations.md` unless a
teammate runs them before the final regression.
