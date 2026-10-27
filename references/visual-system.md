# Visual System for Super AI Lab Run Decks

## Style selection

The default is the approved **舒文深蓝金机器人版**. Read [shuwen-robot.md](shuwen-robot.md) for its backgrounds, left-text/right-character layout, colors, and schedule visibility. The rules below describe the previous **classic** style (`--style classic`); do not apply its light cards, AI lattice, or serif headline to the robot template. Fixed-stage and QA requirements apply to both.

## Visual thesis

Combine Toastmasters-informed blue and maroon anchors with warm paper, precise geometry, and restrained AI/circuit details. The deck should feel professional, welcoming, and current—not like a generic neon dashboard.

## Palette

- Loyal blue: `#004165`
- Secondary blue: `#006094`
- Maroon: `#772432`
- Deep maroon: `#3b0104`
- Warm yellow: `#f2df74`
- Cool gray: `#a9b2b1`
- Warm paper: `#fffaf0`
- Ink: `#06233a`

Alternate dark transition slides with light content slides when density rises.

## Fixed stage

- Author every slide at `1920px x 1080px` and scale the whole stage uniformly.
- Switch slides with `.active` or `.visible` using visibility, opacity, and pointer events.
- Do not reflow slide geometry for phones.
- Keep CSS and JavaScript inline; use no build step.
- Keep navigation chrome outside the authored stage.

## Typography and density

- Prefer a strong Chinese serif or display face for major titles and a readable Chinese sans for body text.
- Provide offline-safe local fallbacks; do not make a remote font a functional dependency.
- Keep text large enough for projection. Split dense material instead of shrinking it.
- Use one idea per transition slide and no more than four rule/content cards per page.

## Slide patterns

- Cover: topic, Word of the Day, meeting label/date/time/location, one strong graphic cue.
- Role: section, large activity/role title, speaker, one clear time range.
- Rules/cards: large label, short subtitle, three or four equal items.
- Speech: title in quotation marks, speaker, project label when confirmed, time range.
- Section: one strong beat between major meeting blocks.
- Break: direct return time or duration.
- Closing: approved slogan and minimal wrap-up.

## QA checklist

- File opens from `file://` without a build step.
- All assets are embedded or relative, exist, and stay inside the deck folder. Generated robot decks embed the three backgrounds.
- Slide count matches the rendered `.slide` count.
- Every current correction appears and no old meeting residue remains.
- No unresolved placeholder is visible.
- No text overflows or panels overlap at `1280x720`.
- Cover, densest slide, one speech slide, one role slide, and closing are visually checked.
- Keyboard, click, touch, fullscreen, page count, and progress work.
