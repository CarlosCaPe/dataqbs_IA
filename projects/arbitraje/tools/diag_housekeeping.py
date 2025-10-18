"""Small housekeeping utility to rotate/truncate diag_paths.jsonl and diagnostics.log.

Usage:
  python diag_housekeeping.py rotate --path <path-to-artifacts-dir> --keep 1000
  python diag_housekeeping.py truncate --path <path-to-artifacts-dir> --max-lines 10000
"""
import argparse
from pathlib import Path
import shutil
import time


def rotate(path: Path, keep: int = 1000):
    pd = path / "diag_paths.jsonl"
    if not pd.exists():
        print(f"No diag_paths.jsonl at {pd}")
        return
    ts = int(time.time())
    archive = path / f"diag_paths.{ts}.jsonl"
    shutil.move(str(pd), str(archive))
    print(f"Archived {pd} -> {archive}")


def truncate(path: Path, max_lines: int = 10000):
    pd = path / "diag_paths.jsonl"
    if not pd.exists():
        print(f"No diag_paths.jsonl at {pd}")
        return
    with pd.open('r', encoding='utf-8') as f:
        lines = f.readlines()
    if len(lines) <= max_lines:
        print("No truncation needed")
        return
    # keep last max_lines
    with pd.open('w', encoding='utf-8') as f:
        f.writelines(lines[-max_lines:])
    print(f"Truncated {pd} to last {max_lines} lines")


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['rotate', 'truncate'])
    p.add_argument('--path', default='artifacts/arbitraje')
    p.add_argument('--keep', type=int, default=1000)
    p.add_argument('--max-lines', type=int, default=10000)
    args = p.parse_args()
    path = Path(args.path)
    path.mkdir(parents=True, exist_ok=True)
    if args.action == 'rotate':
        rotate(path, args.keep)
    else:
        truncate(path, args.max_lines)
