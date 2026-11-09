# Test Plan v1.1: changes to v1.0 (TB-32)

The submitted test plan is `TaskBoard_Test_Plan.pdf` (v1.0). This file lists every correction for v1.1.
When the PDF is regenerated from its source, apply these changes and add a revision row:
`1.1 | 09-11-2026 | Member 3 | TC-21/22/24 wording, RTM test names, SRS test-ID mapping, schedule`.

## T-01 Reworded manual cases (§13.2)

| ID | v1.0 steps | v1.1 steps | Why |
|---|---|---|---|
| TC-14 | Create an issue assigned to a teammate | Create an issue with a teammate chosen in the Assignee box, or use **Edit** on a card and change the assignee | Both paths exist since TB-18/TB-39 |
| TC-21 | Open an issue and add a comment | Add a comment through the API: `POST /api/issues/{id}/comments` with `{"body": "Looks good"}` while logged in | The UI has no issue view or comment panel (SRS TB-F-015, SAD §4.5) |
| TC-22 | Submit an empty comment | Send `POST /api/issues/{id}/comments` with `{"body": "  "}` | As TC-21 |
| TC-24 | Edit an issue's title, priority and story points | Click **Edit** on a card, change the title, priority and story points, click **Save changes**, then reload the page | There is no "open issue" page; editing is a dialog |
| TC-15 | Create a sprint, add an issue while it is selected | Create a sprint and put an issue into it (API until BUG-13 [TB-48] is fixed), then choose that sprint in the **Show** filter | The page has no sprint controls yet |
| TC-16, TC-17 | (unchanged) | Add: "Through the API until BUG-13 [TB-48] is fixed" | As TC-15 |

Expected results do not change.

## T-02 Corrected RTM test names (§13.1)

v1.0 names 8 tests that do not exist. Real names, as of the branches on 09-11-2026:

| Req | Test cases | v1.0 automated test | Real automated test(s) | File |
|---|---|---|---|---|
| FR-01 Register | TC-01..TC-03 | test_register_and_me, test_duplicate_email_rejected, test_short_password_rejected | same (exist) | test_api.py |
| FR-02 Login / logout | TC-04..TC-06 | test_login_wrong_password, test_login_success_after_logout, test_requires_login | **test_login_success_and_generic_error**, **test_logout_then_protected_call_returns_401**, test_requires_login | test_api_extra.py, test_api.py |
| FR-03 Projects | TC-07, TC-08 | test_project_key_validation, test_duplicate_project_key | same, plus test_list_projects, test_duplicate_project_key_returns_409 | test_api.py, test_api_extra.py |
| FR-04 Create issue | TC-09..TC-11 | test_issue_keys_increment, test_issue_requires_title, test_invalid_story_points | same, plus test_invalid_issue_fields_rejected_and_nothing_created | test_api.py, test_api_extra.py |
| FR-05 Kanban board | TC-09, TC-12, TC-23 | (UI only) | test_list_issues (API side) | test_api_extra.py |
| FR-06 Change status | TC-12 | test_status_update, test_invalid_status_rejected | **test_change_status_and_edit**, test_invalid_status_rejected | test_api_extra.py |
| FR-07 Edit / delete | TC-13, TC-24 | test_delete_issue | test_delete_issue, **test_change_status_and_edit** | test_api_extra.py |
| FR-08 Assign | TC-14 | test_assign_issue | test_assign_issue, test_edit_can_assign_and_unassign | test_api.py, test_api_extra.py |
| FR-09 Comments | TC-21, TC-22 | test_comment_and_empty_comment | same | test_api.py |
| FR-10 Create sprint | TC-15 | test_invalid_sprint_dates | **test_invalid_sprint_rejected**, test_reversed_dates_give_error_message, test_add_issue_to_sprint | test_sprints.py, test_sprints_extra.py |
| FR-11 Start / complete | TC-16, TC-17 | test_only_one_active_sprint, test_complete_sprint_returns_unfinished_to_backlog | **test_only_one_active_sprint_per_project**, **test_complete_moves_unfinished_issues_to_backlog**, test_complete_returns_every_unfinished_status_to_backlog | test_sprints.py, test_sprints_extra.py |
| FR-12 Sprint summary | TC-18 | test_sprint_summary_points | same (xfail until BUG-12 [TB-47] is fixed) | test_sprints_extra.py |
| FR-13 Sprint / backlog filter | TC-15, TC-19 | (UI only) | **test_filter_by_sprint_shows_only_its_issues**, **test_filter_backlog_shows_only_issues_without_sprint** (xfail, BUG-12 [TB-47]) | test_sprints_extra.py |
| NFR-02 Performance | TC-26 | - | **tools/perf_check.py** | tools/ |
| NFR-03 Security | TC-20, TC-06 | test_requires_login | test_requires_login, test_every_protected_endpoint_requires_login, test_script_title_is_stored_as_plain_text | test_api.py, test_api_extra.py |
| NFR-04 Maintainability | flake8 | CI runs pytest | CI runs pytest; flake8 run by hand (see NFR_Test_Results.md) | |

Bold = name changed from v1.0. Test files on branches not yet merged: `test_sprints.py` (PR #16),
`test_sprints_extra.py` (PR #17), `tools/perf_check.py` (PR #18).

## T-03 SRS test IDs ↔ test plan cases

The SRS (column "Acceptance criteria / Test case ref") uses different IDs. Mapping:

| SRS test ID | Requirement | Test plan case / automated test |
|---|---|---|
| TC-Auth-01, TC-Auth-03 | TB-F-001 | TC-01, TC-03 |
| TC-Auth-02 | TB-F-002 | TC-02 |
| TC-Auth-04, TC-Auth-05 | TB-F-003 | TC-04, TC-05 |
| TC-Auth-06 | TB-F-004 | TC-06 |
| TC-Prj-01..03 | TB-F-005 | TC-07, TC-08, test_project_key_validation |
| TC-Prj-04 | TB-F-006 | TC-07 |
| TC-Prj-05, TC-Prj-06 | TB-F-007, TB-SR-005 | **No case in v1.0.** New: TC-28 (below); test_owner_can_delete_project, test_non_owner_delete_gets_403 (xfail, BUG-16) |
| TC-Iss-01, TC-Iss-02 | TB-F-008 | TC-09, TC-11 |
| TC-Iss-03, TC-Iss-04 | TB-F-009 | TC-10, test_invalid_issue_fields_rejected_and_nothing_created |
| TC-Iss-05, TC-Iss-06 | TB-F-010 | TC-12, TC-24 |
| TC-Iss-07 | TB-F-011 | TC-13 |
| TC-Iss-08 | TB-F-012 | TC-14 |
| TC-Iss-09 | TB-F-013 | **No case in v1.0.** New: test_filter_issues_by_* (xfail, BUG-17) |
| TC-Iss-10 | TB-F-014 | TC-23 |
| TC-Cmt-01, TC-Cmt-02 | TB-F-015 | TC-21, TC-22 |
| TC-Spr-01, TC-Spr-02 | TB-F-016 | TC-15, test_reversed_dates_give_error_message |
| TC-Spr-03, TC-Spr-04 | TB-F-017 | TC-16 |
| TC-Spr-05 | TB-F-018 | TC-17 |
| TC-Spr-06 | TB-F-019 | TC-18 |
| TC-Spr-07 | TB-F-020 | TC-15, TC-19 |
| TC-Perf-01 | TB-NF-001 | TC-26 |
| TC-Use-01 | TB-NF-002 | TC-25 |
| TC-Port-01 | TB-NF-003 | TC-27 |
| TC-Mnt-01 | TB-NF-004 | flake8 + CI |
| TC-Rel-01 | TB-NF-005 | Restart check in NFR_Test_Results.md; API 4xx tests |
| TC-Cmp-01 | TB-NF-006 | **No case in v1.0.** New: TC-29 (below) |
| TC-Sec-01 | TB-SR-001 | test_password_stored_only_as_hash |
| TC-Sec-02 | TB-SR-002 | test_every_protected_endpoint_requires_login |
| TC-Sec-03 | TB-SR-003 | API validation tests |
| TC-Sec-04 | TB-SR-004 | TC-20 |
| TC-Sec-06 | TB-SR-006 | test_sql_injection_text_is_stored_as_plain_data |
| TC-Sec-07 | TB-SR-007 | test_login_success_and_generic_error |
| TC-Sec-08 | TB-SR-008 | Deployment checklist (open, BUG-10 [TB-45]) |

## T-04 New manual cases

| ID | Req | Steps | Expected result |
|---|---|---|---|
| TC-28 | TB-F-007, TB-SR-005 | User A creates project XY; user B sends `DELETE /api/projects/{id}`; then user A sends it | B gets 403 and the project stays; A gets 200 and the project, its issues and sprints are gone |
| TC-29 | TB-NF-006 | Run TC-01 to TC-14 in Firefox and Edge | Same results as in Chrome |

## T-05 Schedule (§7)

Replace the dates with the actuals in `docs/deviations.md` (D-13).
