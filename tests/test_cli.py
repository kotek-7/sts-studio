"""CLI contracts: real process entry, service reuse, errors, and connection cleanup."""

import json
import os
import pty
import subprocess
import sys
from pathlib import Path

import pytest

from sts_studio import cli
from sts_studio.cli.commands import execute
from sts_studio.cli.parser import build_parser
from sts_studio.service import Service
from sts_studio.simulator import VirtualLink
from sts_studio.wire import Timeout

ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "sts_studio", "cli", *args],
        cwd=ROOT,
        env=dict(os.environ, PYTHONPATH=str(ROOT / "src")),
        text=True,
        capture_output=True,
        timeout=5,
    )


def test_cli_headless_entry_and_scan():
    result = run_cli("--demo", "scan", "--first", "1", "--last", "3")
    assert result.returncode == 0, result.stderr
    assert [s["id"] for s in json.loads(result.stdout)["servos"]] == [1, 2]
    assert not result.stderr
    check = subprocess.run(
        [
            sys.executable,
            "-c",
            'import sys; from sts_studio.cli import main; main(["--demo","info","--id","1"]); assert not any(k.startswith("PyQt5") for k in sys.modules)',
        ],
        env=dict(os.environ, PYTHONPATH=str(ROOT / "src")),
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert check.returncode == 0, check.stderr


@pytest.mark.parametrize(
    "arguments",
    [
        ["scan"],
        ["--demo", "scan", "--first", "3", "--last", "1"],
        ["--demo", "move", "--ids", "1,1", "--position", "10"],
        ["--demo", "pwm", "pulse", "2"],
        ["--demo", "write", "--id", "1", "--address", "256", "--value", "0"],
        ["--demo", "watch", "--id", "1", "--interval-ms", "0"],
    ],
)
def test_invalid_cli_arguments_do_not_open_port(arguments, monkeypatch, capsys):
    monkeypatch.setattr(cli, "SerialLink", lambda *a: pytest.fail("opened serial"))
    monkeypatch.setattr(cli, "VirtualLink", lambda *a: pytest.fail("opened demo"))
    with pytest.raises(SystemExit) as error:
        cli.main(arguments)
    assert error.value.code == 2


def test_read_write_baud_and_id_use_service_verification():
    service = Service(VirtualLink())
    out = []
    parser = build_parser()

    def call(*args):
        return execute(parser.parse_args(["--demo", *args]), service, out.append)

    call("write", "--id", "1", "--address", "21", "--value", "44")
    assert out[-1]["confirmed"] and service.link.mem[1][21] == 44
    call("write", "--id", "1", "--address", "6", "--value", "1")
    assert out[-1]["baud"] == 500000
    call("write", "--id", "1", "--address", "5", "--value", "3")
    call("read", "--id", "3", "--address", "21")
    assert out[-1]["value"] == 44 and 3 in service.link.mem


def test_move_does_not_enable_torque_and_action_is_explicit():
    service = Service(VirtualLink())
    out = []
    parser = build_parser()
    execute(
        parser.parse_args(
            ["--demo", "move", "--ids", "1,2", "--position", "1200", "--method", "registered"]
        ),
        service,
        out.append,
    )
    assert service.link.mem[1][40] == 0 and service.link.mem[2][40] == 0
    assert set(service.link.pending) == {1, 2}
    execute(parser.parse_args(["--demo", "action"]), service, out.append)
    assert not service.link.pending
    assert out[-1]["scope"] == "broadcast" and not out[-1]["confirmed"]


def test_stop_attempts_remaining_ids_after_missing_device():
    service = Service(VirtualLink())
    service.link.mem[2][40] = 1
    out = []
    code = execute(
        build_parser().parse_args(["--demo", "stop", "--ids", "99,2"]), service, out.append
    )
    assert code == 1 and service.link.mem[2][40] == 0
    assert [r["confirmed"] for r in out[0]["results"]] == [False, True]


def test_watch_produces_requested_json_lines_and_trace_separate():
    result = run_cli(
        "--demo", "--trace", "watch", "--id", "1", "--count", "3", "--interval-ms", "20"
    )
    assert result.returncode == 0
    assert len(result.stdout.splitlines()) == 3
    assert all(json.loads(line)["id"] == 1 for line in result.stdout.splitlines())
    assert "TX " in result.stderr


def test_backup_restore_preview_then_apply(tmp_path):
    service = Service(VirtualLink())
    parser = build_parser()
    out = []
    file = tmp_path / "backup.xdat"
    execute(parser.parse_args(["--demo", "backup", "--id", "1", str(file)]), service, out.append)
    assert len(file.read_bytes()) == 44
    service.link.mem[1][21] = 44
    execute(parser.parse_args(["--demo", "restore", "--id", "1", str(file)]), service, out.append)
    assert not out[-1]["applied"] and service.link.mem[1][21] == 44
    execute(
        parser.parse_args(["--demo", "restore", "--id", "1", str(file), "--apply"]),
        service,
        out.append,
    )
    assert out[-1]["applied"] and service.link.mem[1][21] == 32


def test_unknown_firmware_is_readonly(monkeypatch, capsys):
    link = VirtualLink()
    link.mem[1][0] = 99
    monkeypatch.setattr(cli, "VirtualLink", lambda *a: link)
    assert cli.main(["--demo", "write", "--id", "1", "--address", "21", "--value", "44"]) == 1
    captured = capsys.readouterr()
    assert not captured.out
    assert json.loads(captured.err)["command"] == "write"
    assert link.mem[1][21] == 32


@pytest.mark.parametrize("failure", [Timeout("timeout"), KeyboardInterrupt()])
def test_connection_closed_on_failure_and_interrupt(monkeypatch, capsys, failure):
    class FailingLink(VirtualLink):
        closed = False

        def exchange(self, *a, **kw):
            raise failure

        def close(self):
            self.closed = True

    link = FailingLink()
    monkeypatch.setattr(cli, "VirtualLink", lambda *a: link)
    code = cli.main(["--demo", "info", "--id", "1"])
    assert code == (130 if isinstance(failure, KeyboardInterrupt) else 1)
    assert link.closed


def test_cli_real_serial_pty_read(monkeypatch, capsys):
    import threading

    from sts_studio.wire import Parser, frame

    master, slave = pty.openpty()
    stop = threading.Event()
    parser = Parser()

    def peer():
        import select

        while not stop.is_set():
            if not select.select([master], [], [], 0.05)[0]:
                continue
            for request in parser.feed(os.read(master, 1024)):
                if request[4] == 2 and request[5:7] == bytes([0, 9]):
                    os.write(master, frame(request[2], 0, bytes([3, 6, 0, 9, 3, 1, 0, 0, 1])))

    worker = threading.Thread(target=peer)
    worker.start()
    try:
        assert cli.main(["--port", os.ttyname(slave), "info", "--id", "1"]) == 0
        assert json.loads(capsys.readouterr().out)["model"] == "STS3215"
    finally:
        stop.set()
        worker.join(1)
        os.close(master)
        os.close(slave)


@pytest.mark.parametrize("command", ["reset", "restore"])
def test_unknown_firmware_cannot_reset_or_restore(command, monkeypatch, capsys):
    link = VirtualLink()
    link.mem[1][0] = 99
    monkeypatch.setattr(cli, "VirtualLink", lambda *a: link)
    args = ["--demo", command, "--id", "1"]
    if command == "restore":
        args += ["unused.xdat", "--apply"]
    assert cli.main(args) == 1
    assert all(frame[4] == 2 for frame in link.history)
