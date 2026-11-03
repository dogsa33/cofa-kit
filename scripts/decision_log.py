#!/usr/bin/env python3
"""Local, append-only decision event log for AI-assisted projects.

Requires Python >=3.10. Does not authenticate a human response or validate tests;
its entries must be compared with the real conversation and execution evidence.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import sys

LOG_NAME = ".cofa-decisions.jsonl"
DECISION_ID = re.compile(r"^D-[0-9]{3,8}$")
CHOICE_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,19}$")


def fail(message: str) -> None:
    raise ValueError(message)


def decode_pair(s: str) -> tuple[str, str]:
    key, delim, value = s.partition("::")
    if not delim or not CHOICE_ID.fullmatch(key) or not value.strip():
        fail(f"옵션은 ID::내용 형식이어야 합니다: {s!r}")
    return key, value.strip()


def load_events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    if not path.is_file():
        fail(f"기록 경로가 파일이 아닙니다: {path}")
    events: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle, 1):
            if not line.strip():
                fail(f"기존 기록에 빈 줄이 있습니다: {index}; 파일을 덮어쓰지 않았습니다")
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                fail(f"기존 JSONL이 손상됐습니다: {index}; 파일을 덮어쓰지 않았습니다")
            if not isinstance(obj, dict) or not all(k in obj for k in ("decision_id", "event", "time_utc")):
                fail(f"다른 형식의 기록입니다: {index}; 파일을 덮어쓰지 않았습니다")
            events.append(obj)
    return events


def write_event(path: Path, event: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"
    # No rewrite of existing entries. Single-writer only; not a cross-process lock.
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def history_for(events: list[dict], decision_id: str) -> list[dict]:
    return [event for event in events if event.get("decision_id") == decision_id]


def state(history: list[dict]) -> dict:
    if not history or history[0]["event"] != "PROPOSED":
        fail("제안(PROPOSED) 기록을 찾지 못했습니다")
    options = history[0]["options"]
    selected = None
    rejected: dict[str, str] = {}
    implemented: list[dict] = []
    verified: list[dict] = []
    decision_history: list[dict] = []
    for item in history[1:]:
        if item["event"] == "SELECTED":
            selected = item["selected"]
            rejected = dict(item.get("rejected", {}))
            decision_history.append(item)
        elif item["event"] == "IMPLEMENTED":
            implemented.append(item)
        elif item["event"] == "VERIFIED":
            verified.append(item)
    return {
        "id": history[0]["decision_id"], "topic": history[0]["topic"],
        "options": options, "recommended": history[0].get("recommended"),
        "basis": history[0].get("basis", ""), "selected": selected,
        "rejected": rejected,
        "not_selected": [k for k in options if k != selected and k not in rejected],
        "selection_history": decision_history,
        "implementation_events": implemented, "verification_events": verified,
    }


def build_report(events: list[dict]) -> str:
    ids = list(dict.fromkeys(e["decision_id"] for e in events if e["event"] == "PROPOSED"))
    lines = ["# 의사결정 이력 (AI 사용 허용 단계에서 작성)", "", "실제 사용자 발언·작업 파일·검증 실행과 대조하세요. 이 문서는 시험 정답이나 검증 완료의 증거가 아닙니다.", ""]
    if not ids:
        lines.extend(["아직 기록된 결정이 없습니다.", ""])
    for id_ in ids:
        x = state(history_for(events, id_))
        lines.extend([f"## {x['id']} — {x['topic']}", f"- AI 추천: {x['recommended'] or '없음'} (사용자 승인과 다름)", f"- 제안 근거: {x['basis'] or '없음'}"])
        for opt, desc in x["options"].items():
            label = "선택" if opt == x["selected"] else "명시적 거절" if opt in x["rejected"] else "미선택/미결정"
            lines.append(f"- 대안 {opt}: **{label}** — {desc}" + (f" / 거절 이유: {x['rejected'][opt]}" if opt in x["rejected"] else ""))
        if x["selection_history"]:
            for i, e in enumerate(x["selection_history"], 1):
                lines.append(f"- 사용자 응답 {i} ({e['time_utc']}): {e['user_reply']} / 선택 {e['selected']} / 이유: {e.get('reason') or '미기록'}")
        else:
            lines.append("- 사용자 결정: **아직 없음 (AI가 임의 승인 불가)**")
        if x["implementation_events"]:
            for e in x["implementation_events"]:
                rev = e.get("selection_revision", 1)
                obsolete = " (이전 결정 판본; 현재 선택 검증 아님)" if rev < len(x["selection_history"]) else ""
                lines.append(f"- 구현 (결정 v{rev}, {e['time_utc']}): {', '.join(e['files'])} / {e.get('note') or '설명 없음'}{obsolete}")
        else:
            lines.append("- 구현: 기록 없음")
        if x["verification_events"]:
            for e in x["verification_events"]:
                rev = e.get("selection_revision", 1)
                obsolete = " (이전 결정 판본; 현재 선택 검증 아님)" if rev < len(x["selection_history"]) else ""
                lines.append(f"- 검증 (결정 v{rev}, {e['time_utc']}): {e['status']} / 근거: {e.get('evidence') or '없음'} / {e.get('note') or ''}{obsolete}")
        else:
            lines.append("- 검증: 기록 없음 (성공으로 취급하지 않음)")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def run(args: argparse.Namespace) -> None:
    root = Path(args.workspace).expanduser().resolve()
    if not root.is_dir():
        fail(f"작업 공간이 존재하지 않습니다: {root}")
    path = root / LOG_NAME
    events = load_events(path)
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    if args.command in {"propose", "select", "implement", "verify"}:
        if not DECISION_ID.fullmatch(args.id):
            fail("결정 ID는 D-001 또는 D-0001 형태여야 합니다")
        history = history_for(events, args.id)

    if args.command == "propose":
        if history:
            fail(f"이미 존재하는 결정 ID입니다: {args.id}")
        options = dict(decode_pair(s) for s in args.option)
        if len(options) < 2 or len(options) > 5 or len(options) != len(args.option):
            fail("중복 없는 대안 2~5개가 필요합니다")
        if args.recommend and args.recommend not in options:
            fail("AI 추천은 존재하는 옵션 ID여야 합니다")
        event = {"decision_id": args.id, "event": "PROPOSED", "actor": "AI", "time_utc": now,
                 "topic": args.topic, "options": options, "recommended": args.recommend, "basis": args.basis}
    elif args.command == "select":
        if not history:
            fail("제안 기록이 없습니다. 먼저 propose를 실행하세요")
        x = state(history)
        if args.choice not in x["options"]:
            fail("제안되지 않은 옵션은 선택할 수 없습니다")
        if x["selected"] is not None and not args.revise:
            fail("이미 선택한 결정입니다. 변경 시 --revise를 명시해야 합니다")
        rejected = dict(decode_pair(s) for s in args.reject)
        if len(rejected) != len(args.reject) or any(k not in x["options"] or k == args.choice for k in rejected):
            fail("거절 대상은 선택 옵션을 제외한 기존 옵션이어야 하며 중복되면 안 됩니다")
        raw_reply = args.user_reply.strip()
        compact_reply = "".join(raw_reply.lower().split()).replace("_", "").replace("-", "")
        if not raw_reply or compact_reply in {"알아서", "알아서해", "네가정해", "네가결정해", "편한대로", "추천대로", "그냥해", "youdecide", "pass", "fail", "notrun", "blocked", "통과", "실패"}:
            fail("사용자가 선택을 확정한 실제 응답이 필요합니다. 무응답/위임은 승인 아님")
        event = {"decision_id": args.id, "event": "SELECTED", "actor": "USER_REPORTED",
                 "time_utc": now, "selected": args.choice, "rejected": rejected,
                 "user_reply": args.user_reply, "reason": args.reason, "revises_previous": bool(x["selected"])}
    elif args.command == "implement":
        if not history or state(history)["selected"] is None:
            fail("사용자 선택 기록이 없어 구현 완료를 연결할 수 없습니다")
        event = {"decision_id": args.id, "event": "IMPLEMENTED", "actor": "AI_REPORTED", "time_utc": now,
                 "files": args.file, "note": args.note, "selection_revision": len(state(history)["selection_history"])}
    elif args.command == "verify":
        if not history or state(history)["selected"] is None:
            fail("사용자 선택 기록이 없어 검증을 연결할 수 없습니다")
        if args.status in {"PASS", "HUMAN_CHECK"} and not args.evidence.strip():
            fail("PASS를 기록하려면 실제 명령/로그 등 근거(--evidence)를 지정해야 합니다")
        event = {"decision_id": args.id, "event": "VERIFIED", "actor": "AI_REPORTED", "time_utc": now,
                 "status": args.status, "evidence": args.evidence, "note": args.note,
                 "selection_revision": len(state(history)["selection_history"])}
    elif args.command == "report":
        report = build_report(events)
        if args.output:
            dest = Path(args.output).expanduser()
            if not dest.is_absolute():
                dest = root / dest
            dest = dest.resolve()
            if not dest.is_relative_to(root):
                fail("보고서 출력은 작업 폴더 안에만 허용됩니다")
            if dest.exists():
                fail("기존 보고서를 덮어쓰지 않습니다. 다른 이름을 지정하세요")
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("x", encoding="utf-8") as handle:
                handle.write(report)
            print(f"보고서 생성: {dest}")
        else:
            print(report, end="")
        return
    else:
        fail("지원하지 않는 명령입니다")
    write_event(path, event)
    print(f"기록 추가: {path.name} | {event['decision_id']} | {event['event']}")


def cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Append-only human decision log (local, optional)")
    parser.add_argument("--workspace", default=".", help="실제 작업 폴더 (기본값: 현재 위치)")
    sub = parser.add_subparsers(dest="command", required=True)
    a = sub.add_parser("propose", help="중요한 설계 대안 제안 기록")
    a.add_argument("--id", required=True)
    a.add_argument("--topic", required=True)
    a.add_argument("--option", action="append", required=True, help="A::대안 설명, 여러 번 지정")
    a.add_argument("--recommend", default="", help="AI 추천 옵션 ID")
    a.add_argument("--basis", default="", help="추천 또는 제안의 근거")
    a = sub.add_parser("select", help="실제 사용자 응답을 받은 후 선택 기록")
    a.add_argument("--id", required=True)
    a.add_argument("--choice", required=True)
    a.add_argument("--user-reply", required=True, help="사용자 발언 원문")
    a.add_argument("--reason", default="", help="사용자가 명시한 선택 이유")
    a.add_argument("--reject", action="append", default=[], help="B::명시적 거절 이유. 미지정 대안은 단순 미선택")
    a.add_argument("--revise", action="store_true", help="기존 선택을 보존한 채 새 결정 추가")
    a = sub.add_parser("implement", help="결정에 따라 실제 구현한 파일 기록")
    a.add_argument("--id", required=True)
    a.add_argument("--file", action="append", required=True, help="실제 구현 파일, 여러 번 지정 가능")
    a.add_argument("--note", default="")
    a = sub.add_parser("verify", help="검증 상태와 실제 근거 기록")
    a.add_argument("--id", required=True)
    a.add_argument("--status", required=True, choices=["PASS", "FAIL", "NOT_RUN", "HUMAN_CHECK"])
    a.add_argument("--evidence", default="", help="실제 실행 명령·로그·경로")
    a.add_argument("--note", default="")
    a = sub.add_parser("report", help="기록에서 인간이 읽는 요약 생성")
    a.add_argument("--output", default="", help="새 MD 파일 경로, 미지정 시 화면에 출력")
    return parser


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    try:
        run(cli().parse_args())
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
