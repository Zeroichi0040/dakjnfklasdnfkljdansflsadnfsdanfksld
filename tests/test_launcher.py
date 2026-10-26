"""Exercise the actual local server, including immediate same-port restart."""

import os
import socket
import subprocess
import sys
import time
import urllib.request

from backend.config import ROOT


def test_local_server_can_restart_immediately_on_the_same_port(app, tmp_path):
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    env = {
        **os.environ,
        "APP_ENV": "testing",
        "SECRET_KEY": "launcher-test-only-persistent-secret",
        "DATABASE_URL": app.config["SQLALCHEMY_DATABASE_URI"],
        "PUBLIC_BASE_URL": url,
        "TRUSTED_HOSTS": "localhost,127.0.0.1",
        "PROXY_FIX_HOPS": "0",
        "MAIL_TRANSPORT": "disabled",
        "SESSION_COOKIE_SECURE": "false",
    }
    env.pop("RENDER", None)
    log = tmp_path / "launcher.log"
    with log.open("w") as output:
        for _ in range(2):
            server = subprocess.Popen(
                [sys.executable, str(ROOT / "run.py"), "--port", str(port), "--no-browser"],
                cwd=tmp_path,
                env=env,
                stdout=output,
                stderr=output,
            )
            try:
                for attempt in range(80):
                    if server.poll() is not None:
                        raise AssertionError(log.read_text())
                    try:
                        with urllib.request.urlopen(url + "/health/ready", timeout=0.3) as response:
                            assert response.status == 200
                        break
                    except OSError:
                        time.sleep(0.1)
                else:
                    raise AssertionError(log.read_text())
            finally:
                server.terminate()
                server.wait(timeout=10)
