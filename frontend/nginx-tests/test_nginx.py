"""Behaviour of the public nginx (frontend/nginx/default.conf.template), tested in containers.

Run with: python3 -m unittest discover -s frontend/nginx-tests   (needs Docker; no Bedrock, no database)

Two containers share a throwaway network: the nginx under test, rendered from the real template
like the production image, and a fake "backend" that answers 200 to everything and logs each
request, so a test can tell whether a request reached the backend (design D7).
"""

from __future__ import annotations

import http.client
import json
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import uuid
from pathlib import Path

IMAGE = "nginx:1.27-alpine"
FRONTEND = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = FRONTEND / "nginx"
LIMIT_VARS = ("ASK_RATE_PER_MINUTE", "ASK_RATE_BURST", "MAX_CONNECTIONS_PER_IP")


def image_defaults() -> dict[str, str]:
    """The rate-limit defaults from the production Dockerfile's ENV lines (one source of truth)."""
    defaults = {}
    for line in (FRONTEND / "Dockerfile").read_text().splitlines():
        if line.startswith("ENV "):
            for pair in line[4:].split():
                key, _, value = pair.partition("=")
                defaults[key] = value
    return {key: defaults[key] for key in LIMIT_VARS if key in defaults}

FAKE_BACKEND_CONF = """
server {
    listen 8000;
    location / {
        default_type application/json;
        return 200 '{"status":"ok","from":"backend"}';
    }
}
"""
INDEX_HTML = "<!doctype html><title>BrewQL test page</title>"


def docker(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True, check=check)


class NginxHarness:
    """Starts the fake backend once; the nginx under test is (re)started per test to reset limits."""

    def __init__(self) -> None:
        self.tag = f"brewql-nginx-test-{uuid.uuid4().hex[:8]}"
        self.network = self.tag
        self.backend = f"{self.tag}-backend"
        self.nginx = f"{self.tag}-nginx"
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        (tmp / "backend.conf").write_text(FAKE_BACKEND_CONF)
        (tmp / "html").mkdir()
        (tmp / "html" / "index.html").write_text(INDEX_HTML)
        self.tmp = tmp
        self.port: int | None = None

    def start(self) -> None:
        docker("network", "create", self.network)
        docker(
            "run", "-d", "--name", self.backend, "--network", self.network, "--network-alias", "backend",
            "-v", f"{self.tmp / 'backend.conf'}:/etc/nginx/conf.d/default.conf:ro", IMAGE,
        )

    def start_nginx(self, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
        """Start the nginx under test; returns the docker result so a test can expect a failed start."""
        docker("rm", "-f", self.nginx, check=False)
        merged = {**image_defaults(), **(env or {})}
        env_args = [arg for key, value in merged.items() for arg in ("-e", f"{key}={value}")]
        docker(
            "run", "-d", "--name", self.nginx, "--network", self.network, "-p", "127.0.0.1::80", *env_args,
            "-v", f"{TEMPLATE_DIR}:/etc/nginx/templates:ro",
            "-v", f"{self.tmp / 'html'}:/usr/share/nginx/html:ro", IMAGE,
        )
        for _ in range(50):
            state = docker("inspect", "-f", "{{.State.Running}}", self.nginx).stdout.strip()
            if state != "true":
                return docker("logs", self.nginx, check=False)
            port = docker("port", self.nginx, "80/tcp", check=False).stdout.strip()
            if port:
                self.port = int(port.splitlines()[0].rsplit(":", 1)[1])
                try:
                    urllib.request.urlopen(f"http://127.0.0.1:{self.port}/", timeout=1)
                    return docker("logs", self.nginx, check=False)
                except (urllib.error.URLError, ConnectionError):
                    pass
            time.sleep(0.1)
        raise RuntimeError(f"nginx did not start: {docker('logs', self.nginx, check=False).stderr}")

    def nginx_running(self) -> bool:
        return docker("inspect", "-f", "{{.State.Running}}", self.nginx).stdout.strip() == "true"

    def request(self, method: str, path: str, body: bytes | None = None) -> tuple[int, dict[str, str], bytes]:
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=body, method=method)
        if body is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, dict(resp.headers), resp.read()
        except urllib.error.HTTPError as err:
            return err.code, dict(err.headers), err.read()

    def ask(self) -> int:
        return self.request("POST", "/api/ask", json.dumps({"question": "q"}).encode())[0]

    def ask_from_another_ip(self) -> int:
        """POST /api/ask from inside the backend container: a different source address on the network."""
        result = docker(
            "exec", self.backend, "wget", "-q", "-O", "/dev/null", "--header", "Content-Type: application/json",
            "--post-data", '{"question":"q"}', f"http://{self.nginx}/api/ask", check=False,
        )
        return 200 if result.returncode == 0 else -1

    def backend_hits(self, path: str) -> int:
        """Requests for exactly this path that reached the fake backend."""
        logs = docker("logs", self.backend).stdout
        return sum(1 for line in logs.splitlines() if f" {path} HTTP/" in line)

    def stop(self) -> None:
        docker("rm", "-f", self.nginx, self.backend, check=False)
        docker("network", "rm", self.network, check=False)
        self._tmp.cleanup()


harness = NginxHarness()


def setUpModule() -> None:
    harness.start()


def tearDownModule() -> None:
    harness.stop()


class NginxTestCase(unittest.TestCase):
    env: dict[str, str] = {}

    def setUp(self) -> None:
        harness.start_nginx(self.env)


class WhitelistTest(NginxTestCase):
    # Spec (limit-public-traffic): only listed public APIs reach the backend (design D6).

    def test_ask_is_forwarded_to_the_backend(self):
        before = harness.backend_hits("/api/ask")
        status, _, body = harness.request("POST", "/api/ask", json.dumps({"question": "q"}).encode())
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["from"], "backend")
        self.assertEqual(harness.backend_hits("/api/ask"), before + 1)

    def test_frontend_pages_are_served_by_nginx(self):
        for path in ("/", "/some/client/route"):
            with self.subTest(path=path):
                status, _, body = harness.request("GET", path)
                self.assertEqual(status, 200)
                self.assertIn(b"BrewQL test page", body)

    def test_internal_and_unlisted_paths_are_404_and_never_reach_the_backend(self):
        for method, path in (
            ("GET", "/metrics"),
            ("GET", "/health"),
            ("GET", "/docs"),
            ("GET", "/openapi.json"),
            ("GET", "/redoc"),
            ("GET", "/api/audit"),
            ("POST", "/api/anything-new"),
            ("GET", "/api/"),
        ):
            with self.subTest(path=path):
                before = harness.backend_hits(path)
                status, _, body = harness.request(method, path, b"{}" if method == "POST" else None)
                self.assertEqual(status, 404, body[:200])
                self.assertNotIn(b"BrewQL test page", body)
                self.assertEqual(harness.backend_hits(path), before)


def ask_n_times(n: int) -> list[int]:
    return [harness.ask() for _ in range(n)]


class RateLimitTest(NginxTestCase):
    # Spec: /api/ask defaults to 10 per minute per IP with a burst of 5, nodelay (design D1).

    def test_defaults_come_from_the_image(self):
        self.assertEqual(
            image_defaults(), {"ASK_RATE_PER_MINUTE": "10", "ASK_RATE_BURST": "5", "MAX_CONNECTIONS_PER_IP": "20"}
        )

    def test_twenty_rapid_questions_let_six_through(self):
        before = harness.backend_hits("/api/ask")
        statuses = ask_n_times(20)
        self.assertEqual(statuses, [200] * 6 + [429] * 14)
        self.assertEqual(harness.backend_hits("/api/ask"), before + 6)

    def test_429_has_the_answer_shape_and_retry_after(self):
        ask_n_times(6)
        status, headers, body = harness.request("POST", "/api/ask", b'{"question":"q"}')
        self.assertEqual(status, 429)
        self.assertEqual(headers.get("Content-Type"), "application/json")
        self.assertEqual(headers.get("Retry-After"), "60")
        self.assertEqual(
            json.loads(body),
            {
                "status": "error",
                "sql": None,
                "columns": [],
                "rows": [],
                "message": "請求太頻繁，請稍後再試",
                "error_kind": None,
                "refusal_source": None,
                "attempts": 0,
                "chart": None,
            },
        )

    def test_another_ip_is_not_limited(self):
        ask_n_times(7)
        self.assertEqual(harness.ask(), 429)
        self.assertEqual(harness.ask_from_another_ip(), 200)

    def test_pages_are_not_rate_limited(self):
        ask_n_times(7)
        self.assertEqual([harness.request("GET", "/")[0] for _ in range(20)], [200] * 20)


class ConfiguredRateLimitTest(NginxTestCase):
    # Spec: the limits come from environment variables (design D8).
    env = {"ASK_RATE_BURST": "2"}

    def test_a_smaller_burst_lets_three_through(self):
        self.assertEqual(ask_n_times(10), [200] * 3 + [429] * 7)


class InvalidLimitTest(unittest.TestCase):
    # Spec: a bad value must stop nginx, never run it without a limit (design D8).

    def test_bad_values_stop_nginx(self):
        # A burst of 0 is valid (no burst); a rate or connection limit of 0 is not.
        bad = {
            "ASK_RATE_PER_MINUTE": ("0", "abc", ""),
            "ASK_RATE_BURST": ("-1", "abc", ""),
            "MAX_CONNECTIONS_PER_IP": ("0", "abc", ""),
        }
        for key, values in bad.items():
            for value in values:
                with self.subTest(key=key, value=value):
                    harness.start_nginx({key: value})
                    self.assertFalse(harness.nginx_running(), f"nginx started with {key}={value!r}")


class RequestSizeAndTimeoutTest(NginxTestCase):
    # Spec: bodies over 16 KB are 413; a client that stalls for 10 s is cut off (design D5).

    def post_raw(self, body: bytes) -> int:
        conn = http.client.HTTPConnection("127.0.0.1", harness.port, timeout=10)
        try:
            conn.request("POST", "/api/ask", body=body, headers={"Content-Type": "application/json"})
        except (BrokenPipeError, ConnectionResetError):
            pass  # nginx may answer before the whole body is sent
        try:
            return conn.getresponse().status
        finally:
            conn.close()

    def test_a_one_megabyte_body_is_413_and_never_reaches_the_backend(self):
        before = harness.backend_hits("/api/ask")
        self.assertEqual(self.post_raw(b"x" * 1024 * 1024), 413)
        self.assertEqual(harness.backend_hits("/api/ask"), before)

    def test_a_body_under_16_kb_still_goes_through(self):
        body = json.dumps({"question": "q", "pad": "x" * 15_000}).encode()
        self.assertEqual(self.post_raw(body), 200)

    def test_a_stalled_header_is_cut_off_within_about_ten_seconds(self):
        with socket.create_connection(("127.0.0.1", harness.port), timeout=30) as sock:
            sock.sendall(b"POST /api/ask HTTP/1.1\r\nHost: test\r\n")  # never finish the headers
            start = time.monotonic()
            while sock.recv(1024):
                pass  # nginx may send a 408 before closing; wait for the close itself
            elapsed = time.monotonic() - start
        self.assertLess(elapsed, 13)
        self.assertGreater(elapsed, 8)


if __name__ == "__main__":
    unittest.main()
