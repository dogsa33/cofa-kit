#!/usr/bin/env python3
"""Explicit, local-only SHA-256 snapshot/check for input documents and data.

No changes are made to source files. Snapshot must be explicitly requested and
is never overwritten silently. This is not a proof of access permissions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

MANIFEST = ".cofa-source-guard.json"
IGNORE_PARTS = {".git", ".venv", "node_modules", ".cofa-kit", "__pycache__"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(1 << 20):
            h.update(block)
    return h.hexdigest()


def inside(root: Path, relative: str) -> Path:
    root = Path(root).expanduser().resolve()
    if Path(relative).is_absolute():
        raise ValueError("절대 경로는 포함할 수 없습니다")
    result = (root / relative).resolve()
    if not result.is_relative_to(root):
        raise ValueError("작업 영역 밖 경로는 포함할 수 없습니다")
    return result


def list_included(root: Path, inputs: list[str]) -> list[str]:
    root = Path(root).expanduser().resolve()
    result: set[str] = set()
    if not inputs:
        raise ValueError("snapshot에는 --include 파일/폴더가 하나 이상 필요합니다")
    for value in inputs:
        p = inside(root, value)
        if not p.exists():
            raise ValueError(f"입력 경로 없음: {value}")
        files = p.rglob("*") if p.is_dir() else [p]
        for f in files:
            if f.is_file() and not f.is_symlink() and not (IGNORE_PARTS & set(f.relative_to(root).parts)):
                result.add(f.relative_to(root).as_posix())
    if not result:
        raise ValueError("보호할 실제 파일이 없습니다")
    return sorted(result)


def snapshot(root: Path, include: list[str]) -> int:
    root = Path(root).expanduser().resolve()
    dest = root / MANIFEST
    if dest.exists():
        raise ValueError("기존 지문이 있습니다. 임의 갱신 금지; 별도 승인 후만 기록 재작성")
    items = list_included(root, include)
    payload = {"format": "cofa-source-guard-v1", "files": {name: sha256(inside(root, name)) for name in items}}
    with dest.open("x", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"SNAPSHOT: {len(items)}개 입력 파일 기록. 원본은 변경하지 않음")
    return 0


def check(root: Path) -> int:
    root = Path(root).expanduser().resolve()
    manifest = root / MANIFEST
    if not manifest.is_file():
        print("NOT_RUN: 지문 파일 없음", file=sys.stderr)
        return 2
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        items = data["files"]
        if data["format"] != "cofa-source-guard-v1" or not isinstance(items, dict) or not items:
            raise ValueError("지문이 손상됐거나 검사 파일이 0개입니다")
        changed = []
        for name, digest in items.items():
            f = inside(root, name)
            if not f.is_file() or sha256(f) != digest:
                changed.append(name)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, ValueError) as exc:
        print("INPUT_ERROR", exc, file=sys.stderr)
        return 2
    for name in changed:
        print("CHANGED", name)
    if changed:
        print(f"FAIL: 보호 파일 {len(changed)}개 변경·삭제됨")
        return 1
    print(f"PASS: 보호 파일 {len(items)}개 변경 없음")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Check explicit input file integrity (local-only, stdlib)")
    p.add_argument("command", choices=["snapshot", "check"])
    p.add_argument("--root", default=".")
    p.add_argument("--include", action="append", default=[], help="snapshot용 입력/형식 파일 또는 폴더, 반복 가능")
    args = p.parse_args()
    root = Path(args.root).expanduser().resolve()
    try:
        if not root.is_dir():
            raise ValueError("root는 기존 디렉터리여야 합니다")
        return snapshot(root, args.include) if args.command == "snapshot" else check(root)
    except (OSError, ValueError) as exc:
        print("INPUT_ERROR", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
