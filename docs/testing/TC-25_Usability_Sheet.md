# TC-25 usability trial sheet (NFR-01 / TB-NF-002)

**Requirement:** a new user can register, create a project and add a first issue within
**2 minutes without help**. Timed trial with **3 observers** (SRS TB-NF-002).

Print one copy per participant. Run each trial separately so participants don't watch each other.

## Before the trial (tester)

1. Start the app on a clean database: stop the server, delete the `instance` folder, run `python run.py`.
2. Open http://127.0.0.1:5000 in Chrome or Edge. Make sure the login page shows.
3. Pick a participant who has **never used TaskBoard** (not one of the 4 developers if possible).
4. Have a stopwatch ready (phone is fine). Each of the 3 observers times independently.

## Read this to the participant (word for word)

> "Please create an account, then create a project with any key and name, then add one issue
> to it. Talk out loud while you work if you can. We can't help you during the task. Tell us
> when you think you're done."

Start the stopwatch when you finish reading. Stop it when the first issue card appears on the board.

## Participant ___ (name or P1 / P2 / P3)

| Item | Observer 1 | Observer 2 | Observer 3 |
|---|---|---|---|
| Observer name | | | |
| Time to register (mm:ss) | | | |
| Time to create project (mm:ss) | | | |
| Time to first issue on board (mm:ss) — **total** | | | |
| Asked for help? (Y/N) | | | |
| Errors seen on screen (write them) | | | |
| Where did they hesitate or get stuck? | | | |

**Result for this participant:** total time = average of the 3 observers' totals = ______

- **Pass** if the average total is **under 2:00** and they did not need help.
- **Fail** otherwise. Write down the step that took longest.

## After the trial: 3 quick questions to the participant

1. What was the most confusing step? ____________________________________________
2. Was anything on the screen hard to read or find? ______________________________
3. On a scale of 1 (very hard) to 5 (very easy), how easy was it? ______

## Known things that may slow people down (watch for these)

- "New project" asks for the key and name in two browser pop-up boxes, one after the other.
- The key must be 2 to 10 letters; "1" or "TB1" gives an error.
- The password must be at least 6 characters.

## Summary for the test report

| Participant | Avg total time | Help needed | Pass / Fail |
|---|---|---|---|
| P1 | | | |
| P2 | | | |
| P3 | | | |

TC-25 passes if every participant passes. Date: ________ Tester: Member 3 (Harsh). Build: develop @ ________
