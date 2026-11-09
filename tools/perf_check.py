"""Performance seed and timing script (TC-26, TB-NF-001 / NFR-02).

What it does:
1. Starts the real TaskBoard app on a free local port, using a throw-away
   SQLite file in a temp folder (instance/taskboard.db is not touched).
2. Registers a user, creates project PERF and seeds N issues (default 1000)
   through the normal API, timing every POST as well.
3. Calls GET /api/projects/{id}/issues M times (default 200), timing each.
4. Prints p50 / p95 / max and PASS if at least 95% of list calls finish
   under the limit (default 500 ms). Exit code 0 = pass, 1 = fail.

Run from the repo root:
    python tools/perf_check.py
    python tools/perf_check.py --issues 1000 --calls 200 --limit-ms 500
"""
import argparse
import http.cookiejar
import json
import logging
import platform
import statistics
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from werkzeug.serving import make_server  # noqa: E402

from app import create_app, db  # noqa: E402


def percentile(values, pct):
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round(pct / 100 * len(ordered)) - 1))
    return ordered[index]


def summary(name, times_ms):
    return '%-28s n=%-5d p50=%7.1f ms  p95=%7.1f ms  max=%7.1f ms' % (
        name, len(times_ms), statistics.median(times_ms),
        percentile(times_ms, 95), max(times_ms))


class Client:
    def __init__(self, base):
        self.base = base
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def call(self, method, path, payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            self.base + path, data=data, method=method,
            headers={'Content-Type': 'application/json'})
        start = time.perf_counter()
        with self.opener.open(request) as response:
            body = response.read()
        elapsed_ms = (time.perf_counter() - start) * 1000
        return json.loads(body), elapsed_ms


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--issues', type=int, default=1000)
    parser.add_argument('--calls', type=int, default=200)
    parser.add_argument('--limit-ms', type=float, default=500)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
        db_file = Path(folder) / 'perf.db'
        app = create_app(
            {'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + db_file.as_posix()})
        # No log line for every request.
        logging.getLogger('werkzeug').setLevel(logging.ERROR)
        server = make_server('127.0.0.1', 0, app, threaded=True)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        client = Client('http://127.0.0.1:%d/api' % server.server_port)

        try:
            client.call('POST', '/register', {'name': 'Perf',
                                              'email': 'perf@test.com',
                                              'password': 'secret1'})
            project, _ = client.call('POST', '/projects',
                                     {'key': 'PERF', 'name': 'Perf'})
            issues_url = '/projects/%d/issues' % project['id']

            print('Seeding %d issues through POST /api/projects/%d/issues ...'
                  % (args.issues, project['id']))
            create_ms = []
            for n in range(1, args.issues + 1):
                _, ms = client.call('POST', issues_url, {
                    'title': 'Perf issue %d' % n,
                    'type': ['Story', 'Task', 'Bug', 'Epic'][n % 4],
                    'priority': ['High', 'Medium', 'Low'][n % 3],
                    'story_points': [1, 2, 3, 5, 8, 13][n % 6]})
                create_ms.append(ms)

            print('Timing %d calls to GET /api/projects/%d/issues ...'
                  % (args.calls, project['id']))
            list_ms = []
            for _ in range(args.calls):
                issues, ms = client.call('GET', issues_url)
                list_ms.append(ms)
            assert len(issues) == args.issues, 'expected %d issues, got %d' % (
                args.issues, len(issues))
        finally:
            server.shutdown()
            server.server_close()
            with app.app_context():
                # Windows: release the db file so the temp folder can go.
                db.engine.dispose()

    under = sum(ms < args.limit_ms for ms in list_ms)
    share = 100 * under / len(list_ms)
    passed = share >= 95

    print()
    print('Machine: %s, Python %s'
          % (platform.platform(), platform.python_version()))
    print(summary('POST issue (seeding)', create_ms))
    print(summary('GET issue list (%d issues)' % args.issues, list_ms))
    print('List calls under %.0f ms: %d of %d (%.1f%%), need 95%%'
          % (args.limit_ms, under, len(list_ms), share))
    print('TC-26 result: %s' % ('PASS' if passed else 'FAIL'))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
