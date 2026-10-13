# Meeting Input Contract

Use one UTF-8 JSON object as meeting truth. See `examples/meeting.example.json` for a complete anonymous example.

## Required top-level fields

- `club_name`: `Super AI Lab头马俱乐部` for new meetings; preserve the confirmed Mingyuan / 明源云 name for historical meetings
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

Reuse the current meeting's already-approved agenda. An explicit user correction confirms that specific change: update `meeting.json`, rerun validation, and regenerate the HTML without asking for the same confirmation again. The JSON remains the truth source.

If the correction creates a new conflict or requires another decision, ask about that issue before proceeding with the affected part. Do not infer another person's role, change the declared meeting window, or silently compress other segments to accommodate a correction.
