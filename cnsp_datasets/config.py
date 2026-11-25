"""
Secrets (tokens, passwords) and local paths (corpora that cannot be downloaded automatically).

Both are looked up by name, first in the environment, then in a JSON file:

- secrets: `get_secret("HF_TOKEN")` reads $HF_TOKEN, else the key "HF_TOKEN" of the secrets file
  ($CNSP_SECRETS, else ~/.config/cnsp_datasets/secrets.json, else secrets.json at the repository root);
- paths: `get_path("CNSP_IFADV_DIR")` reads $CNSP_IFADV_DIR, else the key of the paths file ($CNSP_PATHS, else
  ~/.config/cnsp_datasets/paths.json, else paths.json at the repository root).

Never pass secrets on the command line (they end up in the shell history and the process list). Values are never
logged. Older secrets files used other key names; they are still read (LEGACY_KEYS).
"""
from __future__ import annotations

import getpass
import json
import logging
import os
import stat
import sys
from pathlib import Path

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
USER_DIR = Path.home() / ".config" / "cnsp_datasets"

# secrets.json keys used before the names were unified with the environment variables
LEGACY_KEYS = {
    "HF_TOKEN": ["hf"],
    "DRYAD_CLIENT_ID": ["dryad-client-id"],
    "DRYAD_CLIENT_SECRET": ["dryad-client-secret"],
    "DRYAD_TOKEN": ["dryad"],
    "RADBOUD_USERNAME": ["ru-rdr-usr"],
    "RADBOUD_PASSWORD": ["ru-rdr-pwd"],
}


def _candidates(env_var: str, fname: str) -> list[Path]:
    if os.environ.get(env_var):
        return [Path(os.environ[env_var]).expanduser()]
    return [USER_DIR / fname, REPO_ROOT / fname]


def _read_json(path: Path, warn_permissions: bool) -> dict:
    if warn_permissions and os.name == "posix" and path.stat().st_mode & (stat.S_IRGRP | stat.S_IROTH):
        log.warning("%s is readable by other users; consider `chmod 600 %s`", path, path)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _lookup(name: str, env_var: str, fname: str, secret: bool) -> str | None:
    value = os.environ.get(name)
    if value:
        return value
    for path in _candidates(env_var, fname):
        if path.is_file():
            entries = _read_json(path, warn_permissions=secret)
            for key in [name, *LEGACY_KEYS.get(name, [])]:
                if entries.get(key):
                    return str(entries[key])
            return None  # only the first existing file is used
    return None


def get_secret(name: str, prompt: bool = False) -> str | None:
    """
    The secret `name` (an environment-variable name, e.g. "HF_TOKEN") or None if not configured. prompt: ask on the
    terminal (hidden input) when nothing is configured and stdin is interactive.
    """
    value = _lookup(name, "CNSP_SECRETS", "secrets.json", secret=True)
    if value is None and prompt and sys.stdin.isatty():
        value = getpass.getpass(f"{name}: ") or None
    return value


def get_path(name: str, required: bool = False) -> Path | None:
    """
    The local directory `name` (e.g. "CNSP_IFADV_DIR"), or None if not configured. required: raise with set-up
    instructions if it is not configured or does not exist.
    """
    value = _lookup(name, "CNSP_PATHS", "paths.json", secret=False)
    path = Path(value).expanduser() if value else None
    if required and (path is None or not path.exists()):
        where = f"{path} does not exist" if path else "it is not set"
        raise FileNotFoundError(
            f"{name}: {where}. Export {name}=<directory>, or add {{\"{name}\": \"<directory>\"}} to "
            f"{USER_DIR / 'paths.json'} (or the file named by $CNSP_PATHS).")
    return path
