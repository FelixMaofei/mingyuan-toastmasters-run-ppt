#!/usr/bin/env python3
"""Validate portable Super AI Lab Toastmasters meeting JSON for a live run deck."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


UNRESOLVED_VALUES = {
    "",
    "?",
    "？",
    "pending",
    "tbd",
    "todo",
    "unknown",
    "待定",
    "待确认",
    "招募中",
    "🌺",
}

UNRESOLVED_MARKERS = ("{{", "}}", "<待", "TBD", "TODO", "待确认", "🌺")

WEEKDAYS = {
    "mon": 0,
    "monday": 0,
    "周一": 0,
    "星期一": 0,
    "礼拜一": 0,
    "tue": 1,
    "tues": 1,
    "tuesday": 1,
    "周二": 1,
    "星期二": 1,
    "礼拜二": 1,
    "wed": 2,
    "wednesday": 2,
    "周三": 2,
    "星期三": 2,
    "礼拜三": 2,
    "thu": 3,
    "thur": 3,
    "thurs": 3,
    "thursday": 3,
    "周四": 3,
    "星期四": 3,
    "礼拜四": 3,
    "fri": 4,
    "friday": 4,
    "周五": 4,
    "星期五": 4,
    "礼拜五": 4,
    "sat": 5,
    "saturday": 5,
    "周六": 5,
    "星期六": 5,
    "礼拜六": 5,
    "sun": 6,
    "sunday": 6,
    "周日": 6,
    "星期日": 6,
    "礼拜日": 6,
    "周天": 6,
    "星期天": 6,
}

WEEKDAY_LABELS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("JSON root must be an object")
    return value


def is_unresolved(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    lowered = text.casefold()
    return lowered in UNRESOLVED_VALUES or text in UNRESOLVED_VALUES


def find_placeholder_paths(value: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            hits.extend(find_placeholder_paths(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(find_placeholder_paths(child, f"{path}[{index}]"))
    elif isinstance(value, str) and value.strip():
        if any(marker.casefold() in value.casefold() for marker in UNRESOLVED_MARKERS):
            hits.append(path)
    return hits


def parse_clock(value: str) -> datetime:
    match = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", value)
    if not match:
        raise ValueError(f"invalid clock time {value!r}; use HH:MM")
    hour, minute = map(int, match.groups())
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"invalid clock time {value!r}")
    return datetime(2000, 1, 1, hour, minute)


def parse_window(value: str) -> tuple[datetime, datetime]:
    parts = re.split(r"\s*[-–—]\s*", value.strip())
    if len(parts) != 2:
        raise ValueError(f"invalid meeting_time {value!r}; use HH:MM-HH:MM")
    start, end = parse_clock(parts[0]), parse_clock(parts[1])
    if end <= start:
        raise ValueError("meeting window must end after it starts on the same day")
    return start, end


def normalize_weekday(value: str) -> int | None:
    compact = re.sub(r"[\s.]", "", value).casefold()
    return WEEKDAYS.get(compact)


def validate(data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    result = deepcopy(data)
    errors: list[str] = []

    required = (
        "club_name",
        "meeting_label",
        "meeting_format",
        "date",
        "weekday",
        "meeting_time",
        "topic",
        "location",
        "meeting_manager",
    )
    for field in required:
        if field not in result or is_unresolved(result.get(field)):
            errors.append(f"missing or unresolved required field: {field}")

    club_name = str(result.get("club_name", "")).strip()
    normalized_club = re.sub(r"\s+", "", club_name).casefold()
    known_club = "superailab" in normalized_club or "明源" in club_name or "mingyuan" in normalized_club
    is_toastmasters = "头马" in club_name or "toastmasters" in normalized_club
    if club_name and not (known_club and is_toastmasters):
        errors.append("club_name must identify Super AI Lab Toastmasters or its historical Mingyuan name")

    include_rules = result.get("include_standard_rules", False)
    if not isinstance(include_rules, bool):
        errors.append("include_standard_rules must be a boolean")

    placeholder_paths = find_placeholder_paths(result)
    if placeholder_paths:
        errors.append("unresolved placeholder marker(s) found at: " + ", ".join(placeholder_paths))

    parsed_date: datetime | None = None
    if not is_unresolved(result.get("date")):
        try:
            parsed_date = datetime.strptime(str(result["date"]), "%Y-%m-%d")
        except ValueError:
            errors.append(f"date must use YYYY-MM-DD: {result.get('date')!r}")

    if parsed_date and not is_unresolved(result.get("weekday")):
        supplied_weekday = normalize_weekday(str(result["weekday"]))
        if supplied_weekday is None:
            errors.append(f"unrecognized weekday: {result['weekday']!r}")
        elif supplied_weekday != parsed_date.weekday():
            errors.append(
                f"date/weekday mismatch: {result['date']} is "
                f"{WEEKDAY_LABELS[parsed_date.weekday()]}, not {result['weekday']}"
            )
        result["weekday"] = WEEKDAY_LABELS[parsed_date.weekday()]

    start: datetime | None = None
    declared_end: datetime | None = None
    if not is_unresolved(result.get("meeting_time")):
        try:
            start, declared_end = parse_window(str(result["meeting_time"]))
        except ValueError as exc:
            errors.append(str(exc))

    sections = result.get("sections")
    if not isinstance(sections, list) or not sections:
        errors.append("sections must be a non-empty array")
        sections = []

    cursor = start
    row_count = 0
    visible_count = 0
    hidden_count = 0
    role_owners: dict[str, str] = {}
    speech_indexes: list[int] = []
    required_evaluation_indexes: list[int] = []
    evaluation_indexes: list[int] = []
    seen_sections: set[str] = set()

    for section_number, section in enumerate(sections, start=1):
        if not isinstance(section, dict):
            errors.append(f"section {section_number} must be an object")
            continue

        title = str(section.get("title", "")).strip()
        if is_unresolved(title):
            errors.append(f"section {section_number} has an unresolved title")
        elif title.casefold() in seen_sections:
            errors.append(f"duplicate section title: {title!r}")
        seen_sections.add(title.casefold())

        rows = section.get("rows")
        if not isinstance(rows, list) or not rows:
            errors.append(f"section {title or section_number!r} must contain rows")
            continue

        for row_number, row in enumerate(rows, start=1):
            row_count += 1
            label = f"section {section_number} row {row_number}"
            if not isinstance(row, dict):
                errors.append(f"{label} must be an object")
                continue

            visible = row.get("visible_on_slide", True)
            owner_required = row.get("owner_required", True)
            if not isinstance(visible, bool):
                errors.append(f"{label} visible_on_slide must be a boolean")
            if not isinstance(owner_required, bool):
                errors.append(f"{label} owner_required must be a boolean")
                owner_required = True
            if visible is True:
                visible_count += 1
            elif visible is False:
                hidden_count += 1

            for field in ("start", "activity", "duration"):
                if field not in row or is_unresolved(row.get(field)):
                    errors.append(f"{label} missing or unresolved field: {field}")
            if owner_required and is_unresolved(row.get("role_taker")):
                errors.append(f"{label} missing or unresolved role_taker")

            row_start: datetime | None = None
            try:
                row_start = parse_clock(str(row.get("start", "")))
            except ValueError as exc:
                errors.append(f"{label}: {exc}")

            duration = row.get("duration")
            if isinstance(duration, bool) or not isinstance(duration, int) or duration <= 0:
                errors.append(f"{label} duration must be a positive integer number of minutes")
                duration = None

            if cursor and row_start and row_start != cursor:
                errors.append(
                    f"{label} starts at {row.get('start')} but should start at "
                    f"{cursor.strftime('%H:%M')}"
                )
            if cursor and duration:
                cursor += timedelta(minutes=duration)

            role_key = str(row.get("role_key", "")).strip()
            owner = str(row.get("role_taker", "")).strip()
            if role_key and owner and not is_unresolved(owner):
                prior_owner = role_owners.get(role_key)
                if prior_owner and prior_owner != owner:
                    errors.append(
                        f"role_key {role_key!r} has conflicting owners: "
                        f"{prior_owner!r} and {owner!r}"
                    )
                role_owners[role_key] = owner

            kind = str(row.get("kind", "")).strip()
            if kind == "internal_handoff":
                if visible is not False:
                    errors.append(f"{label} internal_handoff must set visible_on_slide to false")
                if owner_required is not False:
                    errors.append(f"{label} internal_handoff must set owner_required to false")

            if kind in {"prepared_speech", "prepared_speech_evaluation"}:
                speech_index = row.get("speech_index")
                if not isinstance(speech_index, int) or isinstance(speech_index, bool) or speech_index <= 0:
                    errors.append(f"{label} requires a positive integer speech_index")
                elif kind == "prepared_speech":
                    speech_indexes.append(speech_index)
                    if row.get("requires_evaluation", True):
                        required_evaluation_indexes.append(speech_index)
                    details = row.get("details")
                    if not isinstance(details, dict) or is_unresolved(details.get("title")):
                        errors.append(f"{label} prepared speech requires details.title")
                else:
                    evaluation_indexes.append(speech_index)

    for speech_index, count in Counter(speech_indexes).items():
        if count != 1:
            errors.append(f"prepared speech index {speech_index} appears {count} times")
    for speech_index, count in Counter(evaluation_indexes).items():
        if count != 1:
            errors.append(f"prepared speech evaluation index {speech_index} appears {count} times")
    evaluation_counts = Counter(evaluation_indexes)
    for speech_index in sorted(set(required_evaluation_indexes)):
        if evaluation_counts[speech_index] != 1:
            errors.append(f"prepared speech {speech_index} requires exactly one matching evaluation")
    for speech_index in sorted(set(evaluation_indexes) - set(speech_indexes)):
        errors.append(f"evaluation {speech_index} has no matching prepared speech")

    computed = result.setdefault("computed", {})
    computed["row_count"] = row_count
    computed["visible_row_count"] = visible_count
    computed["hidden_row_count"] = hidden_count
    if visible_count == 0:
        errors.append("meeting must contain at least one visible row")

    if start and cursor:
        computed["total_minutes"] = round((cursor - start).total_seconds() / 60)
        computed["final_end"] = cursor.strftime("%H:%M")
    if declared_end and cursor and cursor != declared_end:
        delta = round((cursor - declared_end).total_seconds() / 60)
        direction = "overruns" if delta > 0 else "underruns"
        errors.append(
            f"timeline {direction} declared end {declared_end.strftime('%H:%M')} "
            f"by {abs(delta)} minutes; computed end is {cursor.strftime('%H:%M')}"
        )

    expected_minutes = result.get("expected_minutes")
    if expected_minutes is not None:
        if isinstance(expected_minutes, bool) or not isinstance(expected_minutes, int) or expected_minutes <= 0:
            errors.append("expected_minutes must be a positive integer")
        elif start and declared_end:
            actual = round((declared_end - start).total_seconds() / 60)
            if expected_minutes != actual:
                errors.append(
                    f"declared window is {actual} minutes but expected_minutes is {expected_minutes}"
                )

    return result, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("meeting_json", type=Path)
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    try:
        source = load_json(args.meeting_json)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {"ok": False, "path": str(args.meeting_json), "errors": [str(exc)]}
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"[FAIL] {args.meeting_json}")
            print(f"error: {exc}")
        return 1

    normalized, errors = validate(source)
    result = {
        "ok": not errors,
        "path": str(args.meeting_json.resolve()),
        "errors": errors,
        "computed": normalized.get("computed", {}),
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"[{'OK' if not errors else 'FAIL'}] {result['path']}")
        computed = result["computed"]
        if computed:
            print(
                "rows: "
                f"{computed.get('row_count', 0)} "
                f"(visible={computed.get('visible_row_count', 0)}, "
                f"hidden={computed.get('hidden_row_count', 0)})"
            )
            print(
                f"timeline: {computed.get('total_minutes', 0)} min, "
                f"ends {computed.get('final_end', 'unknown')}"
            )
        for error in errors:
            print(f"error: {error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
