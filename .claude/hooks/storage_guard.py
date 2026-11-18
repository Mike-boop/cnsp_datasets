"""PreToolUse guard for the dataset storage area (see PLAN.md section 7).

- Downloaded datasets under ROOT are read-only; only ROOT/tmp may be written.
- Download/standardise commands are blocked while ROOT/tmp exceeds TMP_LIMIT_GB.

Exit code 2 blocks the tool call and shows stderr to Claude. The Bash checks are heuristic.
"""
import json
import re
import shlex
import subprocess
import sys

ROOT = "/data_storage/gu08wuvu/datasets"
TMP = f"{ROOT}/tmp"
TMP_LIMIT_GB = 500

WRITE_VERBS = {"rm", "mv", "touch", "chmod", "chown", "truncate", "mkdir", "rmdir", "unlink"}
COPY_VERBS = {"cp", "rsync", "ln"}
HEAVY = re.compile(r"download|format_dataset|standardis|wget|curl|datalad|openneuro|aws s3")


def protected(path):
    path = path.rstrip("/")
    return (path == ROOT or path.startswith(ROOT + "/")) and not (path == TMP or path.startswith(TMP + "/"))


def block(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)


def check_bash(cmd):
    for part in re.split(r"&&|\|\||;|\|", cmd):
        for target in re.findall(r">>?\s*(\S+)", part):
            if protected(target):
                block(f"Blocked: {target} is read-only (only {TMP} may be written).")
        try:
            tokens = shlex.split(part)
        except ValueError:
            tokens = part.split()
        if not tokens:
            continue
        verb, args = tokens[0].split("/")[-1], [t for t in tokens[1:] if not t.startswith("-")]
        targets = args if verb in WRITE_VERBS | {"tee", "sed"} and (verb != "sed" or "-i" in part) else []
        if verb in COPY_VERBS and args:
            targets = args[-1:]
        for t in targets:
            if protected(t):
                block(f"Blocked: {t} is read-only (only {TMP} may be written).")
    if HEAVY.search(cmd):
        out = subprocess.run(["du", "-s", "--block-size=1G", TMP], capture_output=True, text=True)
        used = int(out.stdout.split()[0]) if out.returncode == 0 and out.stdout else 0
        if used > TMP_LIMIT_GB:
            block(f"Blocked: {TMP} uses {used} GB (> {TMP_LIMIT_GB} GB). Clean up before downloading/standardising.")


def main():
    event = json.load(sys.stdin)
    tool, inp = event.get("tool_name"), event.get("tool_input", {})
    if tool in ("Write", "Edit", "NotebookEdit"):
        path = inp.get("file_path") or inp.get("notebook_path") or ""
        if protected(path):
            block(f"Blocked: {path} is read-only (only {TMP} may be written).")
    elif tool == "Bash":
        check_bash(inp.get("command", ""))


if __name__ == "__main__":
    main()
