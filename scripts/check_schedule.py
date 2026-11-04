"""Verify formal-slide timing in rendered markup, optionally against meeting truth.

Does not prove visual visibility: browser QA must still inspect CSS, overlap and clipping.
"""
import json
import re
import shutil
import subprocess
from datetime import timedelta
from html.parser import HTMLParser
from pathlib import Path

from validate_meeting import load_json, parse_clock, validate


class TextContent(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, value):
        self.parts.append(value)


def check_schedule(html, meeting_path=None):
    issues = []
    checked = 0
    try:
        node = shutil.which('node')
        if not node:
            raise ValueError('Node.js required: formal-slide schedule display was not checked')
        scripts = re.findall(r'<script\b[^>]*>(.*?)</script>', html, re.S | re.I)
        scripts = [s for s in scripts if re.search(r'\b(?:const|let|var)\s+slides\s*=', s)]
        if len(scripts) != 1:
            raise ValueError('Cannot identify one slide renderer; schedule check incomplete')
        result = subprocess.run([node, str(Path(__file__).with_name('render_schedule.cjs'))],
                                input=scripts[0], text=True, encoding='utf-8',
                                capture_output=True, timeout=10)
        if result.returncode:
            raise ValueError('Schedule renderer failed: ' + result.stderr[:500])
        rendered = json.loads(result.stdout)
        if rendered.get('show_schedule') is False:
            issues.append('Formal schedule labels disabled: show_schedule=false')
        rows = rendered['rows']
        if not rows:
            issues.append('No formal agenda slides found')
        expected = None
        if meeting_path:
            meeting, errors = validate(load_json(meeting_path))
            if errors:
                raise ValueError('Meeting validation failed: ' + '; '.join(errors))
            expected = []
            for section in meeting['sections']:
                for row in section['rows']:
                    if row.get('visible_on_slide', True) is False:
                        continue
                    title = (row['details']['title'] if row.get('kind') == 'prepared_speech'
                             else row['activity'])
                    start = parse_clock(row['start'])
                    end = start + timedelta(minutes=row['duration'])
                    timing = f"{start:%H:%M} - {end:%H:%M}（{row['duration']}分钟）"
                    expected.append((title, timing))
            if len(rows) != len(expected):
                issues.append(f'Formal slide count {len(rows)} != meeting rows {len(expected)}')
        for i, row in enumerate(rows):
            label = f"formal slide {i + 1} ({row.get('title')})"
            timing = row.get('time') or ''
            match = re.fullmatch(r'(\d{2}:\d{2}) - (\d{2}:\d{2})（([1-9]\d*)分钟）', timing)
            if not match:
                issues.append(label + ': missing start/end/duration')
                continue
            if parse_clock(match[2]) - parse_clock(match[1]) != timedelta(minutes=int(match[3])):
                issues.append(label + ': end/start/duration inconsistent')
            if expected is not None and i < len(expected):
                if (row.get('title'), timing) != expected[i]:
                    issues.append(label + ': title/order/time differs from meeting JSON')
            parser = TextContent()
            parser.feed(row['html'])
            text = ''.join(parser.parts)
            if text.count(timing) != 1:
                issues.append(label + ': rendered timing text must occur exactly once')
            checked += 1
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        issues.append(str(exc))
    return {'ok': not issues, 'checked': checked, 'issues': issues,
            'compared_to_meeting': meeting_path is not None,
            'scope': 'rendered text markup; visual layout requires separate browser QA'}
