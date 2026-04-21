"""Cognito hook daemon (v2.0) — long-lived worker that eliminates the ~200 ms
Python cold-start for each hook invocation.

Protocol
--------
Line-delimited JSON over a local socket. Each request is one JSON object on
its own line; each response is one JSON object on its own line.

Request:
    {"hook": "<name>", "cognito_dir": "<abs>", "stdin": "<raw json>"}

Response:
    {"stdout": "<str>", "stderr": "<str>", "rc": <int>}

Transport
---------
- AF_UNIX socket at `$COGNITO_DIR/runtime/hook.sock` on Linux/macOS.
- AF_INET (127.0.0.1) on Windows because AF_UNIX lacks cpython support on
  older Windows releases; a token file at `$COGNITO_DIR/runtime/hook.token`
  protects the TCP port from other local processes.

Lifecycle
---------
- `start`: spawns the daemon detached, writes `runtime/hook.pid`.
- `stop`:  reads pid, SIGTERMs, waits, cleans up.
- `status`: reports running / stale / down + socket path + addr.

Fall-back
---------
If the daemon is not reachable the client (the `hooks/*.sh` wrappers) falls
back to `exec python3 hooks/python/<name>.py`, preserving v1.2 behaviour.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import socket
import sys
import threading
import time
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).parent))
    import _common  # type: ignore[no-redef]
    import phase_detector  # type: ignore[no-redef]
    import mode_injector  # type: ignore[no-redef]
    import gate_validator  # type: ignore[no-redef]
    import session_closer  # type: ignore[no-redef]
else:
    from . import _common, phase_detector, mode_injector, gate_validator, session_closer


HANDLERS = {
    "phase-detector": phase_detector.main,
    "mode-injector": mode_injector.main,
    "gate-validator": gate_validator.main,
    "session-closer": session_closer.main,
}

IS_WINDOWS = sys.platform.startswith("win")


def _runtime_dir(cognito_dir: Path) -> Path:
    return cognito_dir / "runtime"


def _socket_path(cognito_dir: Path) -> Path:
    return _runtime_dir(cognito_dir) / "hook.sock"


def _pid_path(cognito_dir: Path) -> Path:
    return _runtime_dir(cognito_dir) / "hook.pid"


def _addr_path(cognito_dir: Path) -> Path:
    # Written only on Windows where we fall back to TCP localhost and the
    # port is not known in advance.
    return _runtime_dir(cognito_dir) / "hook.addr"


def _token_path(cognito_dir: Path) -> Path:
    return _runtime_dir(cognito_dir) / "hook.token"


# ---------------------------------------------------------------------- #
# Server
# ---------------------------------------------------------------------- #
def _handle_request(raw_line: str) -> str:
    """Dispatch one request. Returns response line terminated by \n."""
    try:
        req = json.loads(raw_line)
    except (json.JSONDecodeError, ValueError):
        return json.dumps({"stdout": "", "stderr": "invalid JSON", "rc": 2}) + "\n"

    hook = req.get("hook")
    if hook not in HANDLERS:
        return json.dumps({"stdout": "", "stderr": f"unknown hook: {hook}", "rc": 2}) + "\n"

    cognito_dir = req.get("cognito_dir")
    if isinstance(cognito_dir, str) and cognito_dir:
        os.environ["COGNITO_DIR_RESOLVED"] = cognito_dir
    os.environ["INPUT_JSON"] = req.get("stdin") or "{}"

    out_buf = io.StringIO()
    err_buf = io.StringIO()
    rc = 0
    try:
        with redirect_stdout(out_buf), redirect_stderr(err_buf):
            rc = HANDLERS[hook]() or 0
    except SystemExit as e:  # hooks call sys.exit in CLI mode; tolerate it
        rc = int(e.code) if isinstance(e.code, int) else 1
    except Exception as e:  # noqa: BLE001
        err_buf.write(f"daemon handler crash: {e}\n")
        rc = 2

    return json.dumps({
        "stdout": out_buf.getvalue(),
        "stderr": err_buf.getvalue(),
        "rc": int(rc),
    }) + "\n"


def _serve_forever(server: socket.socket, token: str | None) -> None:
    server.settimeout(1.0)  # allow clean shutdown on SIGTERM
    while True:
        try:
            conn, _ = server.accept()
        except socket.timeout:
            continue
        except OSError:
            break

        threading.Thread(target=_handle_conn, args=(conn, token), daemon=True).start()


def _handle_conn(conn: socket.socket, token: str | None) -> None:
    try:
        conn.settimeout(10.0)
        with conn.makefile("r", encoding="utf-8") as reader, conn.makefile(
            "w", encoding="utf-8"
        ) as writer:
            line = reader.readline()
            if not line:
                return
            if token is not None:
                # Windows TCP mode: first line must be the token.
                if line.strip() != token:
                    writer.write(json.dumps({"stdout": "", "stderr": "bad token", "rc": 2}) + "\n")
                    writer.flush()
                    return
                line = reader.readline()
                if not line:
                    return
            writer.write(_handle_request(line))
            writer.flush()
    except Exception:  # noqa: BLE001
        pass
    finally:
        try:
            conn.close()
        except OSError:
            pass


def cmd_serve(cognito_dir: Path) -> int:
    """Start the daemon in the foreground (blocks). Used by `cognito-daemon.sh`.

    The shell launcher is responsible for backgrounding; we keep this function
    simple so the process can be inspected under the debugger.
    """
    runtime = _runtime_dir(cognito_dir)
    runtime.mkdir(parents=True, exist_ok=True)
    pid_file = _pid_path(cognito_dir)
    pid_file.write_text(str(os.getpid()), encoding="utf-8")

    if IS_WINDOWS:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", 0))
        server.listen(16)
        host, port = server.getsockname()[:2]
        _addr_path(cognito_dir).write_text(f"{host}:{port}", encoding="utf-8")
        token = os.urandom(16).hex()
        tp = _token_path(cognito_dir)
        tp.write_text(token, encoding="utf-8")
        try:
            os.chmod(tp, 0o600)
        except OSError:
            pass
    else:
        sock_path = _socket_path(cognito_dir)
        if sock_path.exists():
            try:
                sock_path.unlink()
            except OSError:
                pass
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(sock_path))
        try:
            os.chmod(sock_path, 0o600)
        except OSError:
            pass
        server.listen(16)
        token = None

    try:
        _serve_forever(server, token)
    finally:
        try:
            server.close()
        finally:
            if not IS_WINDOWS:
                try:
                    _socket_path(cognito_dir).unlink(missing_ok=True)
                except TypeError:  # Python <3.8 compat (not reachable here)
                    pass
            for p in (_addr_path(cognito_dir), _token_path(cognito_dir), _pid_path(cognito_dir)):
                try:
                    if p.exists():
                        p.unlink()
                except OSError:
                    pass
    return 0


# ---------------------------------------------------------------------- #
# Client
# ---------------------------------------------------------------------- #
def _connect(cognito_dir: Path) -> tuple[socket.socket | None, str | None]:
    """Try to reach the daemon. Returns (sock, token) or (None, None)."""
    try:
        if IS_WINDOWS:
            addr_file = _addr_path(cognito_dir)
            token_file = _token_path(cognito_dir)
            if not addr_file.is_file() or not token_file.is_file():
                return None, None
            host, port = addr_file.read_text(encoding="utf-8").strip().split(":")
            token = token_file.read_text(encoding="utf-8").strip()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect((host, int(port)))
            return s, token
        sock_path = _socket_path(cognito_dir)
        if not sock_path.exists():
            return None, None
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(0.5)
        s.connect(str(sock_path))
        return s, None
    except (OSError, ValueError):
        return None, None


def cmd_client(hook: str, cognito_dir: Path) -> int:
    """Send one request to the daemon. Stdin is forwarded as-is.

    Returns the server-reported rc, or 127 if the daemon is unreachable so the
    bash wrapper can fall back to the stand-alone Python invocation.
    """
    stdin_raw = os.environ.get("INPUT_JSON", "")
    if not stdin_raw:
        try:
            stdin_raw = sys.stdin.read()
        except OSError:
            stdin_raw = ""

    sock, token = _connect(cognito_dir)
    if sock is None:
        return 127  # conventional "not found" — signals wrapper to fall back

    try:
        with sock.makefile("r", encoding="utf-8") as reader, sock.makefile(
            "w", encoding="utf-8"
        ) as writer:
            if token is not None:
                writer.write(token + "\n")
            payload = {"hook": hook, "cognito_dir": str(cognito_dir), "stdin": stdin_raw}
            writer.write(json.dumps(payload) + "\n")
            writer.flush()
            resp_line = reader.readline()
            if not resp_line:
                return 127
            resp = json.loads(resp_line)
            if resp.get("stdout"):
                sys.stdout.write(resp["stdout"])
            if resp.get("stderr"):
                sys.stderr.write(resp["stderr"])
            return int(resp.get("rc", 0))
    except (OSError, ValueError, json.JSONDecodeError):
        return 127
    finally:
        try:
            sock.close()
        except OSError:
            pass


def cmd_status(cognito_dir: Path) -> int:
    pid_file = _pid_path(cognito_dir)
    if not pid_file.is_file():
        print(f"down: no pid file at {pid_file}")
        return 1
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        print(f"stale: pid file unreadable: {pid_file}")
        return 2

    alive = False
    try:
        if IS_WINDOWS:
            import subprocess
            out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True)
            alive = str(pid) in out.stdout
        else:
            os.kill(pid, 0)
            alive = True
    except Exception:  # noqa: BLE001
        alive = False

    if not alive:
        print(f"stale: pid {pid} not running; removing pid file")
        try:
            pid_file.unlink()
        except OSError:
            pass
        return 2

    if IS_WINDOWS:
        addr = _addr_path(cognito_dir)
        loc = addr.read_text(encoding="utf-8").strip() if addr.is_file() else "<unknown>"
        print(f"running: pid {pid}  addr {loc}  (token at {_token_path(cognito_dir)})")
    else:
        print(f"running: pid {pid}  socket {_socket_path(cognito_dir)}")
    return 0


def cmd_stop(cognito_dir: Path) -> int:
    pid_file = _pid_path(cognito_dir)
    if not pid_file.is_file():
        print("down: no pid file")
        return 0
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        print("stale: pid file unreadable — removing")
        try:
            pid_file.unlink()
        except OSError:
            pass
        return 0

    try:
        if IS_WINDOWS:
            import subprocess
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
        else:
            os.kill(pid, 15)  # SIGTERM
    except Exception as e:  # noqa: BLE001
        print(f"stop failed: {e}")
        return 1

    for _ in range(20):  # up to 2s
        time.sleep(0.1)
        if not pid_file.is_file():
            break
    try:
        pid_file.unlink()
    except OSError:
        pass
    print(f"stopped pid {pid}")
    return 0


# ---------------------------------------------------------------------- #
# CLI entry
# ---------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cognito-hook-daemon")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("serve", help="Run the daemon in the foreground")
    sub.add_parser("status", help="Show daemon status")
    sub.add_parser("stop", help="Stop a running daemon")

    client = sub.add_parser("client", help="Send one hook request (used by wrappers)")
    client.add_argument("hook", choices=list(HANDLERS.keys()))

    args = parser.parse_args(argv)

    cognito_dir = _common.resolve_cognito_dir()

    if args.cmd == "serve":
        return cmd_serve(cognito_dir)
    if args.cmd == "status":
        return cmd_status(cognito_dir)
    if args.cmd == "stop":
        return cmd_stop(cognito_dir)
    if args.cmd == "client":
        return cmd_client(args.hook, cognito_dir)
    return 2


if __name__ == "__main__":
    sys.exit(main())
