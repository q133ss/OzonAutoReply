import os
import sys
from pathlib import Path

from ozon_ai.main import main


def _ensure_frozen_env() -> None:
    if getattr(sys, 'frozen', False):
        base_dir = Path(getattr(sys, '_MEIPASS', Path(sys.executable).resolve().parent))
        os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', str(base_dir / 'playwright-browsers'))


def _run_playwright_runner() -> None:
    from ozon_ai.playwright_runner import main as runner_main
    idx = sys.argv.index('--run-playwright-runner')
    sys.argv = [sys.argv[0]] + sys.argv[idx + 1 :]
    raise SystemExit(runner_main())


if __name__ == '__main__':
    _ensure_frozen_env()
    if '--run-playwright-runner' in sys.argv:
        _run_playwright_runner()
    else:
        main()
