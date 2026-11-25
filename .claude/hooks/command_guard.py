"""PreToolUse guard for Bash commands that broke things before (see data_campaign/LESSONS.md).

- `pkill -f` / `pgrep -f`: a pattern that also occurs in the tool's own command line kills or matches the tool's
  shell (self-matching waiters ran for days). Use `ps -eo pid,args | awk '/[p]attern/'` and kill by PID.
- `git add -A` / `--all` / `git add .`: stages other agents' work and the `.venv` symlink. Use explicit paths.
- Zenodo while blocked: if REVIEW/ZENODO_BLOCKED exists, block commands that contact zenodo.org or download a
  dataset registered with the Zenodo source. Never work around a block; delete the file only after a human checks.

Exit code 2 blocks the tool call and shows stderr to Claude. The checks are heuristic.
"""
import glob
import json
import os
import re
import sys

REVIEW = "/data_storage/gu08wuvu/datasets/tmp/review"
ZENODO_FLAG = os.path.join(REVIEW, "ZENODO_BLOCKED")
DATASETS_DIR = "/home/gu08wuvu/cnsp_datasets/cnsp_datasets/datasets"  # one dataset.json per dataset folder

# Only where the word starts a command (line start, after ; & | `, `$(`, `!`, or a shell keyword), so commit messages
# and echoed text that merely mention these commands are not blocked.
CMD_START = r"(?:^|[;&|`]|\$\(|!|\b(?:do|then|else|until|while|if|sudo|nohup|setsid|exec)\b)\s*"
KILL = re.compile(CMD_START + r"(?:pkill|pgrep)\b[^|;&\n]*\s-[a-zA-Z]*f\b", re.M)
GIT_ADD_ALL = re.compile(CMD_START + r"git\b(?:\s+-C\s+\S+)?\s+add\b[^|;&\n]*(?:\s-A\b|\s--all\b|\s\.(?:\s|$))", re.M)


def block(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)


def zenodo_datasets():
    names = set()
    for path in glob.glob(os.path.join(DATASETS_DIR, "*", "dataset.json")):
        try:
            with open(path) as fh:
                downloads = json.load(fh).get("downloads") or {}
        except (OSError, ValueError, AttributeError):
            continue
        names |= {k for k, v in downloads.items() if isinstance(v, dict) and v.get("source") == "zenodo"}
    return names


NET_CMD = re.compile(CMD_START + r"(?:curl|wget|http|aria2c|lftp)\b", re.M)
NET_PY = re.compile(r"\b(?:requests\.|urlopen|urllib|httpx|download_dataset|download_retry|DataDownloader)\b")


def contacts_zenodo(cmd):
    """A network tool aimed at zenodo.org, or a downloader run on a Zenodo-registered dataset.

    Text that only mentions Zenodo (commit messages, echo, doc edits) is allowed."""
    low = cmd.lower()
    if "zenodo.org" in low and (NET_CMD.search(cmd) or NET_PY.search(cmd)):
        return True
    return bool(NET_PY.search(cmd)) and any(re.search(r"\b{}\b".format(re.escape(n)), cmd) for n in zenodo_datasets())


def check(cmd):
    if KILL.search(cmd):
        block("Blocked: `pkill -f`/`pgrep -f` can match this tool's own shell. Find the PID with "
              "`ps -eo pid,args | awk '/[p]attern/'` and kill it by PID.")
    if GIT_ADD_ALL.search(cmd):
        block("Blocked: `git add -A`/`--all`/`.` stages other agents' work and .venv. Stage explicit paths "
              "(`git add -- <paths>`).")
    if os.path.exists(ZENODO_FLAG) and contacts_zenodo(cmd):
            block(f"Blocked: Zenodo has blocked this server ({ZENODO_FLAG}). Never work around a block; ask the "
                  "user, and delete the flag only after access has been checked by hand.")


def main():
    event = json.load(sys.stdin)
    if event.get("tool_name") == "Bash":
        check(event.get("tool_input", {}).get("command", ""))


if __name__ == "__main__":
    main()
