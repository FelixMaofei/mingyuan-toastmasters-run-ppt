"""Regression checks: run python -B scripts/test_schedule.py."""
import json
import tempfile
import unittest
from pathlib import Path

from build_deck import build_html, replace_block, STARTERS
from check_schedule import check_schedule
from validate_meeting import validate


class ScheduleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(__file__).resolve().parents[1]
        self.meeting = json.loads((root / 'examples/meeting.example.json').read_text(encoding='utf-8'))
        self.meeting.pop('show_schedule', None)
        self.path = Path(self.temp.name) / 'meeting.json'
        self.path.write_text(json.dumps(self.meeting, ensure_ascii=False), encoding='utf-8')
        self.starter = STARTERS['shuwen'].read_text(encoding='utf-8')

    def test_default_both_styles_show_all_formal_times(self):
        for style, path in STARTERS.items():
            with self.subTest(style=style):
                html, _ = build_html(self.meeting, path.read_text(encoding='utf-8'), 1)
                report = check_schedule(html, self.path)
                self.assertTrue(report['ok'], report)
                self.assertGreater(report['checked'], 0)

    def test_legacy_false_rejected(self):
        self.meeting['show_schedule'] = False
        self.assertTrue(validate(self.meeting)[1])
        with self.assertRaises(ValueError):
            build_html(self.meeting, self.starter, 1)

    def test_missing_rendered_times_fail(self):
        # Simulates a custom renderer forgetting the time token despite valid data.
        broken = self.starter.replace(' + timeToken(slide)', '')
        html, _ = build_html(self.meeting, broken, 1)
        self.assertFalse(check_schedule(html, self.path)['ok'])

    def test_bad_timing_and_missing_or_reordered_slide_fail(self):
        import re
        html, _ = build_html(self.meeting, self.starter, 1)
        data = json.loads(re.search(r'const slides = (\[.*?\]);\s*/\* BUILD:SLIDES:END', html, re.S)[1])
        indexes = [i for i, s in enumerate(data) if s.get('time')]
        for mutation in ('wrong_time', 'missing', 'reordered'):
            with self.subTest(mutation=mutation):
                slides = json.loads(json.dumps(data))
                a, b = indexes[:2]
                if mutation == 'wrong_time':
                    slides[a]['time'] = '00:00 - 00:01（1分钟）'
                elif mutation == 'missing':
                    del slides[a]
                else:
                    slides[a], slides[b] = slides[b], slides[a]
                changed = replace_block(html, 'SLIDES', 'const slides = ' + json.dumps(slides, ensure_ascii=False) + ';')
                self.assertFalse(check_schedule(changed, self.path)['ok'])

    def test_break_renderer_cannot_drop_time(self):
        self.assertTrue(any(r.get('kind') == 'break' for s in self.meeting['sections'] for r in s['rows']))
        begin = self.starter.index('if (slide.type === "break") {')
        end = self.starter.index('const speechProject', begin)
        broken = self.starter[:begin] + self.starter[begin:end].replace(' + timeToken(slide)', '') + self.starter[end:]
        html, _ = build_html(self.meeting, broken, 1)
        self.assertFalse(check_schedule(html, self.path)['ok'])


if __name__ == '__main__':
    unittest.main()
