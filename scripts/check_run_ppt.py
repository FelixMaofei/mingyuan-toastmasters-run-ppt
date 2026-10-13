#!/usr/bin/env python3
"""Static checks for portable Super AI Lab Toastmasters fixed-stage HTML run decks."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


UNRESOLVED_MARKERS = ["TODO", "TBD", "待替换", "待定", "待确认", "🌺", "{{", "}}"]


def _css_urls(value: str) -> list[str]:
    return [
        match.strip().strip("\"'")
        for match in re.findall(r"url\(\s*([^)]*?)\s*\)", value, flags=re.I)
        if match.strip()
    ]


def _literal_asset_refs(text: str) -> list[str]:
    return [
        match.group(2).strip()
        for match in re.finditer(
            r"\b(?:src|href|poster|data)\s*=\s*([\"'])(.*?)\1",
            text,
            flags=re.I | re.S,
        )
        if match.group(2).strip()
    ]


class _DeckParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: set[str] = set()
        self.html_lang: str | None = None
        self.asset_refs: list[str] = []
        self.static_slide_count = 0
        self.stage_markers: set[str] = set()
        self.control_text: list[str] = []
        self._button_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        self.tags.add(tag)
        attr = {key.lower(): value or "" for key, value in attrs}
        if tag == "html":
            self.html_lang = attr.get("lang") or None

        classes = set(attr.get("class", "").split())
        element_id = attr.get("id", "")
        if "slide" in classes:
            self.static_slide_count += 1
        for marker in classes | ({element_id} if element_id else set()):
            if marker == "stage" or "deck-stage" in marker:
                self.stage_markers.add(marker)

        if tag in {"img", "script", "iframe", "source", "audio", "video", "track", "embed"}:
            if attr.get("src"):
                self.asset_refs.append(attr["src"])
        if tag in {"video", "object"}:
            for name in ("poster", "data"):
                if attr.get(name):
                    self.asset_refs.append(attr[name])
        if tag == "link":
            rel = set(attr.get("rel", "").casefold().split())
            if rel & {"stylesheet", "icon", "preload", "modulepreload"} and attr.get("href"):
                self.asset_refs.append(attr["href"])
        if attr.get("style"):
            self.asset_refs.extend(_css_urls(attr["style"]))

        if tag == "button":
            self._button_depth += 1
            for name in ("aria-label", "title"):
                if attr.get(name):
                    self.control_text.append(attr[name])

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "button" and self._button_depth:
            self._button_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._button_depth and data.strip():
            self.control_text.append(data.strip())


def _extract_inline_scripts(text: str) -> list[tuple[str, bool]]:
    scripts: list[tuple[str, bool]] = []
    pattern = re.compile(r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>", re.S | re.I)
    for match in pattern.finditer(text):
        attrs = match.group("attrs")
        if re.search(r"\bsrc\s*=", attrs, flags=re.I):
            continue
        type_match = re.search(r"\btype\s*=\s*([\"'])(.*?)\1", attrs, flags=re.I | re.S)
        script_type = type_match.group(2).strip().casefold() if type_match else ""
        if script_type and not any(token in script_type for token in ("javascript", "ecmascript", "module")):
            continue
        body = match.group("body").strip()
        if body:
            scripts.append((body, script_type == "module"))
    return scripts


def _node_check(scripts: list[tuple[str, bool]]) -> dict:
    node = shutil.which("node")
    if not node:
        return {"available": False, "ok": None, "messages": ["node not found"]}
    if not scripts:
        return {"available": True, "ok": None, "messages": ["no inline JavaScript"]}

    messages: list[str] = []
    ok = True
    for index, (script, is_module) in enumerate(scripts, start=1):
        suffix = ".mjs" if is_module else ".js"
        with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, encoding="utf-8") as handle:
            handle.write(script)
            temp_path = Path(handle.name)
        try:
            result = subprocess.run(
                [node, "--check", str(temp_path)],
                text=True,
                capture_output=True,
                timeout=15,
            )
            if result.returncode != 0:
                ok = False
                messages.append(f"inline script {index}: {(result.stderr or result.stdout).strip()}")
        finally:
            temp_path.unlink(missing_ok=True)
    return {"available": True, "ok": ok, "messages": messages}


def _count_slides_array(text: str) -> int | None:
    match = re.search(r"(?:const|let|var)\s+(?:slides|SLIDES)\s*=\s*\[", text)
    if not match:
        return None

    index = match.end()
    bracket_depth = 1
    brace_depth = 0
    count = 0
    quote: str | None = None
    escaped = False
    line_comment = False
    block_comment = False

    while index < len(text):
        char = text[index]
        nxt = text[index + 1] if index + 1 < len(text) else ""
        if line_comment:
            if char in "\r\n":
                line_comment = False
            index += 1
            continue
        if block_comment:
            if char == "*" and nxt == "/":
                block_comment = False
                index += 2
            else:
                index += 1
            continue
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            index += 1
            continue
        if char == "/" and nxt == "/":
            line_comment = True
            index += 2
            continue
        if char == "/" and nxt == "*":
            block_comment = True
            index += 2
            continue
        if char in {"'", '"', "`"}:
            quote = char
            index += 1
            continue
        if char == "[":
            bracket_depth += 1
        elif char == "]":
            bracket_depth -= 1
            if bracket_depth == 0:
                return count
        elif char == "{" and bracket_depth == 1:
            if brace_depth == 0:
                count += 1
            brace_depth += 1
        elif char == "}" and bracket_depth == 1 and brace_depth:
            brace_depth -= 1
        index += 1
    return None


def _storage_keys(text: str) -> tuple[list[str], list[str]]:
    definitions = [
        match.group(2)
        for match in re.finditer(
            r"(?:const|let|var)\s+(?:storageKey|STORAGE_KEY)\s*=\s*([\"'])(.*?)\1",
            text,
            flags=re.S,
        )
    ]
    literals = [
        match.group(2)
        for match in re.finditer(
            r"localStorage\.(?:getItem|setItem|removeItem)\(\s*([\"'])(.*?)\1",
            text,
            flags=re.S,
        )
    ]
    return definitions, literals


def _is_ignored_asset(ref: str) -> bool:
    lowered = ref.casefold()
    return not ref or ref.startswith("#") or lowered.startswith(
        ("data:", "blob:", "mailto:", "tel:", "javascript:")
    )


def _asset_status(html_path: Path, refs: list[str]) -> tuple[list[str], list[str], list[str], list[str]]:
    non_relative: list[str] = []
    missing: list[str] = []
    relative: list[str] = []
    escaping: list[str] = []
    package_root = html_path.parent.resolve()

    for raw_ref in sorted(set(refs)):
        ref = raw_ref.strip().strip("\"'")
        if _is_ignored_asset(ref):
            continue
        parsed = urlsplit(ref)
        if parsed.scheme or parsed.netloc or ref.startswith(("/", "~")):
            non_relative.append(ref)
            continue
        relative.append(ref)
        clean = unquote(parsed.path)
        if clean and not any(token in clean for token in ("${", "{{", "<%")):
            candidate = (html_path.parent / clean).resolve()
            try:
                candidate.relative_to(package_root)
            except ValueError:
                escaping.append(ref)
                continue
            if not candidate.exists():
                missing.append(ref)
    return relative, non_relative, missing, escaping


def check(path: Path) -> dict:
    issues: list[str] = []
    warnings: list[str] = []
    if not path.is_file():
        return {"path": str(path), "ok": False, "issues": ["HTML file not found"], "warnings": []}

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return {"path": str(path), "ok": False, "issues": [f"HTML is not valid UTF-8: {exc}"], "warnings": []}

    parser = _DeckParser()
    try:
        parser.feed(text)
        parser.close()
    except Exception as exc:
        issues.append(f"HTML parse failed: {exc}")

    for required_tag in ("html", "body", "script"):
        if required_tag not in parser.tags:
            issues.append(f"Required <{required_tag}> element not found")
    if not re.search(r"<!doctype\s+html", text, flags=re.I):
        issues.append("HTML5 doctype not found")
    if not parser.html_lang or not parser.html_lang.casefold().startswith("zh"):
        issues.append('Chinese document language not detected; use <html lang="zh-CN">')

    scripts = _extract_inline_scripts(text)
    if not scripts:
        issues.append("No inline JavaScript found")
    node = _node_check(scripts)
    if node["available"] and node["ok"] is False:
        issues.append("JavaScript syntax check failed")
    elif not node["available"]:
        warnings.append("Node.js not found; JavaScript syntax was not checked")

    data_slide_count = _count_slides_array(text)
    static_slide_count = parser.static_slide_count
    slide_count = data_slide_count if data_slide_count is not None else static_slide_count
    if slide_count <= 0:
        issues.append("No slides counted from a slides array or static .slide elements")

    fixed_width = bool(re.search(r"width\s*:\s*1920px\b", text, flags=re.I))
    fixed_height = bool(re.search(r"height\s*:\s*1080px\b", text, flags=re.I))
    fixed_stage = fixed_width and fixed_height and bool(parser.stage_markers)
    if not fixed_stage:
        issues.append("Fixed 1920x1080 stage element not detected")

    definitions, literal_keys = _storage_keys(text)
    storage_key = definitions[0] if len(definitions) == 1 else None
    if len(definitions) != 1:
        issues.append(f"Expected exactly one storageKey definition; found {len(definitions)}")
    if storage_key and "mingyuan" not in storage_key.casefold():
        issues.append("storageKey must retain the stable mingyuan Skill namespace")
    all_storage_values = set(definitions + literal_keys)
    if len(all_storage_values) > 1:
        issues.append("Multiple localStorage key values found: " + ", ".join(sorted(all_storage_values)))
    if storage_key and "localStorage." not in text:
        warnings.append("storageKey is defined but no localStorage call was detected")

    refs = parser.asset_refs + _css_urls(text) + _literal_asset_refs(text)
    relative_assets, non_relative_assets, missing_assets, escaping_assets = _asset_status(path, refs)
    if non_relative_assets:
        issues.append("Non-relative asset reference(s): " + ", ".join(non_relative_assets))
    if escaping_assets:
        issues.append("Asset reference(s) escape the deck package: " + ", ".join(escaping_assets))
    if missing_assets:
        issues.append("Missing relative asset(s): " + ", ".join(missing_assets))

    lowered_text = text.casefold()
    compact_text = re.sub(r"\s+", "", lowered_text)
    known_club = "superailab" in compact_text or "明源" in text or bool(re.search(r"mingyuan\s+.*?toastmasters", lowered_text))
    if not known_club or not ("头马" in text or "toastmasters" in lowered_text):
        issues.append("Super AI Lab Toastmasters or historical Mingyuan club identity not found")
    unresolved_hits = [marker for marker in UNRESOLVED_MARKERS if marker in text]
    if unresolved_hits:
        issues.append("Unresolved marker(s) found: " + ", ".join(unresolved_hits))

    feature_checks = {
        "previous/next navigation": bool(
            re.search(r"\b(?:previous|prev)\b", text, flags=re.I)
            and re.search(r"\bnext\b", text, flags=re.I)
        ),
        "Home/End navigation": bool(
            re.search(r"(?:event|e)\.key\s*===?\s*['\"]Home['\"]", text)
            and re.search(r"(?:event|e)\.key\s*===?\s*['\"]End['\"]", text)
        ),
        "fullscreen control": bool(
            re.search(r"requestFullscreen\s*\(", text)
            and re.search(r"exitFullscreen\s*\(", text)
        ),
        "slide counter": bool(re.search(r"slideCount|slide-count|slideStatus", text, flags=re.I)),
        "progress indicator": bool(re.search(r"progressFill|progress-fill", text, flags=re.I)),
        "touch navigation": bool(re.search(r"touchstart", text, flags=re.I) and re.search(r"touchend", text, flags=re.I)),
    }
    for feature, present in feature_checks.items():
        if not present:
            issues.append(f"Required live-control feature not detected: {feature}")

    return {
        "path": str(path.resolve()),
        "ok": not issues,
        "issues": issues,
        "warnings": warnings,
        "slide_count": slide_count,
        "data_slide_count": data_slide_count,
        "static_slide_count": static_slide_count,
        "fixed_stage": fixed_stage,
        "storage_key": storage_key,
        "relative_assets": relative_assets,
        "non_relative_assets": non_relative_assets,
        "missing_assets": missing_assets,
        "escaping_assets": escaping_assets,
        "live_controls": feature_checks,
        "node_check": node,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path)
    parser.add_argument("--json", action="store_true", help="Print JSON only.")
    args = parser.parse_args()

    result = check(args.html)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        status = "OK" if result["ok"] else "FAIL"
        print(f"[{status}] {result['path']}")
        if "slide_count" in result:
            print(
                "slides: "
                f"{result['slide_count']} "
                f"(data={result['data_slide_count']}, static={result['static_slide_count']})"
            )
            print(f"fixed stage: {result['fixed_stage']}")
            print(f"storageKey: {result['storage_key']}")
            node = result["node_check"]
            print(f"node check: available={node['available']} ok={node['ok']}")
            print(f"relative assets: {len(result['relative_assets'])}")
            print(f"live controls: {sum(result['live_controls'].values())}/{len(result['live_controls'])}")
        for warning in result.get("warnings", []):
            print(f"warning: {warning}")
        for issue in result.get("issues", []):
            print(f"issue: {issue}")
        for message in result.get("node_check", {}).get("messages", []):
            if message:
                print(f"node: {message}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
