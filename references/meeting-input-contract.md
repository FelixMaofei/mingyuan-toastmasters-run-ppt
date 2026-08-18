# Meeting Input Contract

Use one UTF-8 JSON object as meeting truth. See `examples/meeting.example.json` for a complete anonymous example.

## Required top-level fields

- `club_name`: a Mingyuan Toastmasters club name
- `meeting_label`: current issue or meeting label
- `meeting_format`: for example `常规例会`, `演讲马拉松`, `工作坊`, or `比赛`
- `date`: ISO `YYYY-MM-DD`
- `weekday`: Chinese or English weekday agreeing with the ISO date
- `meeting_time`: same-day `HH:MM-HH:MM` window
- `topic`
- `location`
- `meeting_manager`
- `sections`: non-empty ordered array

Optional display fields include `word_of_day`, `slogan`, `timezone`, `quote`, and `include_standard_rules`. Omit an optional module cleanly rather than inserting a placeholder.

## Section and row shape

Each section contains:

```json
{
  "title": "备稿演讲",
  "rows": []
}
```

Each row requires:

- `start`: `HH:MM`, continuous with the prior row
- `activity`: exact visible or operational label
- `duration`: positive integer minutes
- `role_taker`: required unless `owner_required` is `false`

Optional row fields:

- `role_key`: stable role identity used to detect conflicting owners
- `kind`: `rules`, `prepared_speech`, `prepared_speech_evaluation`, `break`, `internal_handoff`, or another explicit module
- `speech_index`: positive integer linking a speech and its evaluation
- `requires_evaluation`: defaults to `true` for prepared speeches
- `visible_on_slide`: defaults to `true`
- `owner_required`: defaults to `true`
- `details`: supplied title, project, evaluator, timing, image, or other approved content

An `internal_handoff` must set both `visible_on_slide: false` and `owner_required: false`. It affects timing but must not become a slide.

## Validation

Run:

```bash
python3 <skill-dir>/scripts/validate_meeting.py /absolute/path/to/meeting.json
```

The validator checks required facts, unresolved markers, ISO date and weekday, row continuity, declared end, role-owner consistency, hidden handoffs, and speech/evaluation mapping.

After a factual correction, update `meeting.json`, rerun validation, and regenerate the HTML. The JSON remains the truth source.
