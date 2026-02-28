import signal
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent.parent

    django_cmd = [sys.executable, "manage.py", "runserver"]
    mcp_cmd = [sys.executable, "scripts/run_mcp_server.py"]

    print("Starting Django:", " ".join(django_cmd))
    django_proc = subprocess.Popen(django_cmd, cwd=root)

    print("Starting MCP stdio server:", " ".join(mcp_cmd))
    mcp_proc = subprocess.Popen(mcp_cmd, cwd=root)

    procs = [django_proc, mcp_proc]

    def _shutdown(_sig=None, _frame=None):
        for p in procs:
            if p.poll() is None:
                p.terminate()
        for p in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        while True:
            for p in procs:
                code = p.poll()
                if code is not None:
                    _shutdown()
                    return code
    except KeyboardInterrupt:
        _shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
