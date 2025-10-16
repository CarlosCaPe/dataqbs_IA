import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
CFG = ROOT / "arbitraje.yaml"


def run(cmd: list[str], cwd: Path | None = None) -> int:
    # Print the command to help debugging; keep line length modest
    print("> " + " ".join(cmd))
    return subprocess.call(cmd, cwd=str(cwd) if cwd else None)


def clone_or_update(repo: str, dest: Path, force: bool = False) -> None:
    if dest.exists() and (dest / ".git").exists():
        # update
        run(["git", "remote", "-v"], cwd=dest)
        run(["git", "pull", "--ff-only"], cwd=dest)
        return
    if dest.exists() and any(dest.iterdir()):
        if force:
            print(f"[force] removing existing non-git directory: {dest}")
            shutil.rmtree(dest, ignore_errors=True)
        else:
            print(
                f"[skip] {dest} exists and is not empty (not a git repo). Use --force to replace."
            )
            return
    dest.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "clone", repo, str(dest)])


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Bootstrap official SDKs into ./sdk/* from arbitraje.yaml"
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="Delete existing non-git directories before cloning",
    )
    ap.add_argument(
        "--only",
        type=str,
        default="",
        help=(
            "Comma-separated list of SDK names to process "
            "(e.g., binance,mexc,bitget)"
        ),
    )
    args = ap.parse_args()
    if not CFG.exists():
        print(f"Config not found: {CFG}", file=sys.stderr)
        return 1
    with open(CFG, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}
    sdks = cfg.get("sdk") or {}
    only_set = (
        {x.strip().lower() for x in args.only.split(",") if x.strip()}
        if args.only
        else None
    )
    for name, meta in sdks.items():
        if only_set and name.lower() not in only_set:
            continue
        repo = meta.get("repo")
        path = meta.get("path")
        if not repo or not path:
            print(f"[skip] {name}: missing repo or path in config")
            continue
        dest = (ROOT / path).resolve()
        print(f"[sdk] {name}: {repo} -> {dest}")
        clone_or_update(repo, dest, force=args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
