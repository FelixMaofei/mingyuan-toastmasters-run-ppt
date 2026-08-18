#!/usr/bin/env python3
"""Build a usable Mingyuan Toastmasters HTML run deck from validated meeting JSON."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any

from validate_meeting import load_json, parse_clock, validate


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_STARTER = SKILL_DIR / "assets" / "run-deck-starter.html"


def time_label(start: str, duration: int) -> str:
    start_dt = parse_clock(start)
    end_dt = start_dt + timedelta(minutes=duration)
    return f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}（{duration}分钟）"


def slugify(value: str, fallback: str) -> str:
    ascii_slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return ascii_slug or fallback


def standard_rule_slides() -> list[dict[str, Any]]:
    return [
        {
            "type": "cards",
            "eyebrow": "会议规则",
            "title": "3个提醒",
            "lead": "让每一位伙伴都能安心投入",
            "items": ["手机调为震动或者静音模式", "不要在会场来回走动", "不要私下交谈"],
        },
        {
            "type": "cards",
            "eyebrow": "会议规则",
            "title": "3个提倡",
            "lead": "让舞台交接更顺畅，也让现场更有能量",
            "items": [
                "上台及发言结束，请与主持人握手交接",
                "演讲精彩的、卡顿的，掌声鼓励",
                "与主持人、演讲者多多互动",
            ],
        },
        {
            "type": "cards",
            "eyebrow": "会议规则",
            "title": "4个禁忌",
            "lead": "请会议期间不要提及",
            "items": ["政治", "宗教", "性", "传销"],
        },
    ]


def build_slides(meeting: dict[str, Any]) -> list[dict[str, Any]]:
    chips = [
        meeting["meeting_label"],
        f"{meeting['date']} · {meeting['weekday']}",
        f"{meeting['meeting_time']} · {meeting['location']}",
    ]
    if meeting.get("word_of_day"):
        chips.append(f"今日一词 · {meeting['word_of_day']}")

    slides: list[dict[str, Any]] = [
        {
            "type": "cover",
            "eyebrow": meeting["club_name"],
            "title": meeting["topic"],
            "lead": meeting.get("quote") or "练好表达，用好 AI，在真实舞台上持续成长。",
            "chips": chips,
        }
    ]

    for section_index, section in enumerate(meeting["sections"]):
        if section_index > 0:
            slides.append(
                {
                    "type": "section",
                    "eyebrow": f"环节 {section_index + 1:02d}",
                    "title": section["title"],
                    "lead": "跟随真实流程进入下一段现场。",
                }
            )

        for row in section["rows"]:
            if row.get("visible_on_slide", True) is False:
                continue

            duration = int(row["duration"])
            timing = time_label(str(row["start"]), duration)
            kind = str(row.get("kind", "")).strip()
            details = row.get("details") if isinstance(row.get("details"), dict) else {}

            if kind == "prepared_speech":
                slides.append(
                    {
                        "type": "speech",
                        "eyebrow": section["title"],
                        "title": details["title"],
                        "speaker": row["role_taker"],
                        "project": details.get("project", "备稿演讲"),
                        "time": timing,
                        "index": f"备稿演讲 {int(row['speech_index']):02d}",
                    }
                )
                continue

            if kind == "break":
                slides.append(
                    {
                        "type": "break",
                        "eyebrow": section["title"],
                        "title": row["activity"],
                        "lead": f"短暂休息，{timing.split(' - ')[1].split('（')[0]} 准时回来。",
                        "time": timing,
                    }
                )
                continue

            slides.append(
                {
                    "type": "role",
                    "eyebrow": section["title"],
                    "title": row["activity"],
                    "speaker": row.get("role_taker") or "全体伙伴",
                    "time": timing,
                }
            )

            if kind == "rules" and meeting.get("include_standard_rules", False):
                slides.extend(standard_rule_slides())

    slides.append(
        {
            "type": "closing",
            "eyebrow": meeting["club_name"],
            "title": meeting.get("slogan") or "感谢每一次真诚表达",
            "lead": f"{meeting['meeting_label']} · {meeting['topic']}",
        }
    )
    return slides


def replace_block(text: str, name: str, replacement: str) -> str:
    pattern = re.compile(
        rf"(?P<indent>^[ \t]*)/\* BUILD:{re.escape(name)}:START \*/.*?"
        rf"^[ \t]*/\* BUILD:{re.escape(name)}:END \*/",
        flags=re.M | re.S,
    )
    match = pattern.search(text)
    if not match:
        raise ValueError(f"starter marker block not found: {name}")
    indent = match.group("indent")
    body = "\n".join(indent + line if line else line for line in replacement.splitlines())
    wrapped = (
        f"{indent}/* BUILD:{name}:START */\n"
        f"{body}\n"
        f"{indent}/* BUILD:{name}:END */"
    )
    return text[: match.start()] + wrapped + text[match.end() :]


def build_html(meeting: dict[str, Any], starter: str, version: int) -> tuple[str, int]:
    slides = build_slides(meeting)
    date_slug = str(meeting["date"]).replace("-", "")
    meeting_slug = slugify(str(meeting["meeting_label"]), "meeting")
    storage_key = f"mingyuan-{date_slug}-{meeting_slug}-v{version}"

    meeting_payload = {
        "club": meeting["club_name"],
        "label": meeting["meeting_label"],
        "topic": meeting["topic"],
        "word": meeting.get("word_of_day", ""),
        "date": f"{meeting['date']} · {meeting['weekday']}",
        "time": meeting["meeting_time"],
        "location": meeting["location"],
        "manager": meeting["meeting_manager"],
    }

    result = starter
    result = replace_block(
        result,
        "STORAGE_KEY",
        f'const storageKey = {json.dumps(storage_key, ensure_ascii=False)};',
    )
    result = replace_block(
        result,
        "MEETING",
        "const meeting = " + json.dumps(meeting_payload, ensure_ascii=False, indent=2) + ";",
    )
    result = replace_block(
        result,
        "SLIDES",
        "const slides = " + json.dumps(slides, ensure_ascii=False, indent=2) + ";",
    )
    result = re.sub(
        r"<title>.*?</title>",
        f"<title>{html.escape(str(meeting['meeting_label']))} | {html.escape(str(meeting['topic']))}</title>",
        result,
        count=1,
        flags=re.S,
    )
    return result, len(slides)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("meeting_json", type=Path)
    parser.add_argument("output_html", type=Path)
    parser.add_argument("--starter", type=Path, default=DEFAULT_STARTER)
    parser.add_argument("--version", type=int, default=1)
    parser.add_argument("--force", action="store_true", help="Overwrite an existing output file.")
    args = parser.parse_args()

    if args.version <= 0:
        parser.error("--version must be a positive integer")
    if args.output_html.exists() and not args.force:
        print(f"[FAIL] output already exists: {args.output_html}; use --force to replace it")
        return 1
    if args.output_html.suffix.casefold() != ".html":
        print("[FAIL] output_html must end with .html")
        return 1

    try:
        source = load_json(args.meeting_json)
        normalized, errors = validate(source)
        if errors:
            print(f"[FAIL] meeting validation failed: {args.meeting_json}")
            for error in errors:
                print(f"error: {error}")
            return 1
        starter = args.starter.read_text(encoding="utf-8")
        output, slide_count = build_html(normalized, starter, args.version)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[FAIL] {exc}")
        return 1

    args.output_html.parent.mkdir(parents=True, exist_ok=True)
    args.output_html.write_text(output, encoding="utf-8")
    print(f"[OK] {args.output_html.resolve()}")
    print(f"slides: {slide_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
