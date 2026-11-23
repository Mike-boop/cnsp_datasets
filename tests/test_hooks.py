"""The PreToolUse hooks in .claude/hooks, run as Claude Code runs them (JSON on stdin, exit 2 = blocked)."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[1] / ".claude" / "hooks"


def run(hook, command, env=None):
    event = {"tool_name": "Bash", "tool_input": {"command": command}}
    return subprocess.run([sys.executable, str(HOOKS / hook)], input=json.dumps(event), text=True,
                          capture_output=True, env=env)


@pytest.mark.parametrize("cmd", [
    "pkill -f standardise",
    "pgrep -f 'pilot.py 1 4' >/dev/null",
    "until ! pgrep -af coherence_batch; do sleep 60; done",
    "git add -A",
    "git -C /x add --all",
    "git add . && git commit -m x",
])
def test_command_guard_blocks(cmd):
    assert run("command_guard.py", cmd).returncode == 2


@pytest.mark.parametrize("cmd", [
    "ps -eo pid,args | awk '/[p]attern/'",
    "pgrep -x cron",
    "git add -- cnsp_datasets/datasets/x/adaptor.py",
    "git add cnsp_datasets/x.py tests/y.py",
    "echo done",
    "git commit -m 'Hooks: command_guard (pkill/pgrep -f, git add -A)'",
    "echo \"never use pkill -f or git add -A\" >> notes.md",
])
def test_command_guard_allows(cmd):
    assert run("command_guard.py", cmd).returncode == 0


def test_zenodo_flag(tmp_path, monkeypatch):
    sys.path.insert(0, str(HOOKS))
    import command_guard
    flag = tmp_path / "ZENODO_BLOCKED"
    monkeypatch.setattr(command_guard, "ZENODO_FLAG", str(flag))
    monkeypatch.setattr(command_guard, "zenodo_datasets", lambda: {"peng2026"})
    command_guard.check("curl https://zenodo.org/api/records/1")  # no flag: allowed
    flag.write_text("blocked\n")
    for cmd in ("curl -sI https://zenodo.org/api/records/1",
                "python -c \"download_dataset('peng2026', '/x')\""):
        with pytest.raises(SystemExit) as e:
            command_guard.check(cmd)
        assert e.value.code == 2
    command_guard.check("python -c \"download_dataset('hassan2026', '/x')\"")  # not a Zenodo dataset
    command_guard.check("cat /home/x/peng2026/notes.md")  # no download
    command_guard.check("git commit -m 'PLAN: Zenodo blocks; see https://zenodo.org/records/1'")  # text only
    command_guard.check("cat >> PLAN.md <<'EOF'\nzenodo.org download notes for peng2026\nEOF")  # doc edit


def test_storage_limit_override(tmp_path, monkeypatch):
    sys.path.insert(0, str(HOOKS))
    import storage_guard
    monkeypatch.delenv("CNSP_TMP_LIMIT_GB", raising=False)
    monkeypatch.setattr(storage_guard, "read_limit_file", lambda: None)
    assert storage_guard.tmp_limit_gb() == 1000
    monkeypatch.setattr(storage_guard, "read_limit_file", lambda: "2000")
    assert storage_guard.tmp_limit_gb() == 2000
    monkeypatch.setenv("CNSP_TMP_LIMIT_GB", "1500")
    assert storage_guard.tmp_limit_gb() == 1500
