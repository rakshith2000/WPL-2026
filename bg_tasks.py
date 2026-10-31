"""The scheduled refreshes, run from outside the web app.

create_app() registers both of these with APScheduler, which is fine while a
web process is up but does nothing while the host has the service asleep. The
GitHub Actions workflow in .github/workflows/main.yml calls this every fifteen
minutes against the same database so the leaderboards and the qualification
percentages keep moving either way.

Both are run even if the first one fails: a feed being down should not stop the
simulation, which reads nothing but our own tables. The exit code is non-zero
when either failed, so a run that quietly did nothing is visible in Actions.
"""
import sys
import warnings

warnings.filterwarnings("ignore")

from WPL import create_app
from WPL.main import refresh_qualification, update_toppers

TASKS = (
    ('toppers', update_toppers),
    ('qualification', refresh_qualification),
)


def main():
    app = create_app()
    failed = []
    with app.app_context():
        for name, fn in TASKS:
            try:
                fn()
                print(f'{name}: ok')
            except Exception as exc:                 # noqa: BLE001 - reported, not swallowed
                failed.append(name)
                print(f'{name}: failed - {exc}', file=sys.stderr)
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
