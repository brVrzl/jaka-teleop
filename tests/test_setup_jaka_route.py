"""Exercise the route helper with fake ip/sudo, without changing host networking."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/setup_jaka_lan2_route.sh"


def run_script(tmp_path, *, route="", address="192.0.2.19", ssh_server="10.0.0.2", execute=True, robot="192.0.2.50"):
    tmp_path.mkdir(parents=True, exist_ok=True)
    log = tmp_path / "calls.jsonl"
    fake = tmp_path / "ip"
    fake.write_text(f"#!{sys.executable}\n" + '''import json, os, sys
from pathlib import Path
args = sys.argv[1:]
with open(os.environ["CALLS"], "a") as stream: stream.write(json.dumps([Path(sys.argv[0]).name, *args]) + "\\n")
if args[:3] == ["-4", "route", "get"]: print(os.environ["ROBOT_ROUTE"])
elif args[:2] == ["route", "get"]: print("10.0.0.1 dev wifi src 10.0.0.2")
elif "addr" in args and "show" in args: print("2: robot inet " + os.environ["ADDRESS"] + "/24 scope global robot")
''')
    fake.chmod(0o755)
    (tmp_path / "sudo").symlink_to(fake)
    env = dict(os.environ, PATH=f"{tmp_path}:{os.environ['PATH']}", IFACE="robot", PC_IP="192.0.2.19",
               JAKA_IP=robot, SSH_CONNECTION=f"10.0.0.1 12345 {ssh_server} 22", CALLS=str(log),
               ROBOT_ROUTE=route, ADDRESS=address)
    result = subprocess.run(["bash", str(SCRIPT), *(["--execute"] if execute else [])],
                            env=env, capture_output=True, text=True)
    return result, [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []


def test_correct_route_is_strict_noop(tmp_path):
    result, calls = run_script(tmp_path, route="192.0.2.50 dev robot src 192.0.2.19")
    assert result.returncode == 0
    assert not any(call[0] == "sudo" for call in calls)


@pytest.mark.parametrize("ssh_server", ["192.0.2.19", "192.0.2.20"])
def test_ssh_bound_address_blocks_even_when_return_route_uses_another_interface(tmp_path, ssh_server):
    result, calls = run_script(tmp_path, address="192.0.2.20", ssh_server=ssh_server)
    assert result.returncode == 2 and "SSH" in result.stderr
    assert not any(call[0] == "sudo" for call in calls)


def test_existing_address_is_preserved_and_only_missing_route_is_added(tmp_path):
    result, calls = run_script(tmp_path)
    assert result.returncode == 0
    mutations = [call[1:] for call in calls if call[0] == "sudo"]
    assert mutations == [["ip", "link", "set", "robot", "up"],
                         ["ip", "route", "add", "192.0.2.50/32", "dev", "robot", "src", "192.0.2.19"]]


def test_new_address_is_added_without_flushing_other_addresses(tmp_path):
    result, calls = run_script(tmp_path, address="192.0.2.20")
    assert result.returncode == 0
    mutations = [call[1:] for call in calls if call[0] == "sudo"]
    assert mutations[0] == ["ip", "addr", "add", "192.0.2.19/32", "dev", "robot"]
    assert not any("flush" in call or "replace" in call or "del" in call for call in mutations)


def test_invalid_address_and_dry_run_never_mutate(tmp_path):
    result, calls = run_script(tmp_path / "invalid", robot="192.0.2.50.")
    assert result.returncode == 2 and not calls
    result, calls = run_script(tmp_path / "dry", execute=False)
    assert result.returncode == 0 and "Dry run" in result.stdout
    assert not any(call[0] == "sudo" for call in calls)
