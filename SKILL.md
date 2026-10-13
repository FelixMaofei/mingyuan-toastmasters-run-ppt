---
name: mingyuan-toastmasters-run-ppt
description: Create polished, fixed-stage Chinese HTML run decks for Super AI Lab Toastmasters meetings from confirmed agendas, role relays, screenshots, PDFs, or PPTX files. Use for Super AI Lab 串场PPT、明源云串场PPT、开场PPT、例会投屏 or 会单转HTML演示.
---

# Super AI Lab Toastmasters Run PPT

Use `Super AI Lab头马俱乐部` for new materials. Recognize `明源云` / `Mingyuan` as the former name and preserve the name used in historical meetings, source quotations, and existing deliverables. A name change does not establish the venue, membership terms, fees, or meeting number; use the current confirmed facts. Keep the Skill identifier `mingyuan-toastmasters-run-ppt` for existing installations.

## Purpose

Turn verified Super AI Lab Toastmasters meeting facts into a directly usable browser-based transition deck. The core path must work with this Skill alone: normalize facts, validate them, generate from the bundled starter, check the result, and visually inspect the high-risk slides.

## Standalone Contract

1. Resolve the Skill directory as the folder containing this `SKILL.md`; never hard-code an installation path.
2. Do not require another Skill or a private historical deck. Optional PDF, PPTX, OCR, image, or frontend tools may improve extraction or styling when available.
3. Use `assets/run-deck-starter.html` as the tested implementation base. Do not deliver the unchanged starter.
4. Write the meeting truth to `meeting.json`; do not repair conflicting facts only inside HTML.
5. Keep all output under the user's current meeting project, normally `run-ppt/`, with relative assets only.

## Input Gate

Read `references/meeting-input-contract.md` before normalizing source material.

Before generating the final deck, establish the following from user-confirmed sources. Reuse the current meeting's already-approved agenda without asking for the same confirmation again:

- club name, meeting label, format, ISO date, weekday, declared start/end, topic, location, and meeting manager;
- every visible activity, owner, duration, order, prepared-speech title, and evaluation mapping;
- special blocks such as new-member welcome, workshop, officer ceremony, voting, awards, or group photo;
- any source-designed image page that must be preserved as an image.

Current user corrections outrank screenshots, OCR, old decks, and standing defaults. Ask blocking questions together. Never print `TBD`, `TODO`, `待定`, `待确认`, `🌺`, blank names, or invented speech titles in a final deck.

An explicit user correction confirms that specific change: update `meeting.json`, rerun validation, then regenerate the deck. Ask only about new conflicts, unresolved facts, or additional choices; a correction does not authorize inferring other unknowns or changing unrelated segments.

## Workflow

1. **Normalize facts**
   - Convert a complete agenda or role relay into `meeting.json` using the input contract.
   - If the input is an image, PDF, or PPTX and no extractor is available, ask the user for the corresponding text instead of pretending it was read.

2. **Validate meeting truth**
   - Run:

     ```bash
     python3 <skill-dir>/scripts/validate_meeting.py /absolute/path/to/meeting.json
     ```

   - Resolve every error in `meeting.json` before editing visible deck text.

3. **Generate the usable baseline**
   - Run:

     ```bash
     python3 <skill-dir>/scripts/build_deck.py \
       /absolute/path/to/meeting.json \
       /absolute/path/to/run-ppt/<meeting-slug>.html
     ```

   - The generator creates a fixed `1920x1080` HTML deck with cover, real section changes, role slides, prepared-speech slides, standard rule cards when requested, closing, navigation, progress, fullscreen, touch support, and versioned local state.
   - When materially revising an existing deck, increment `--version` and use `--force` to replace the intended output. This refreshes its browser storage key without changing the confirmed meeting facts.

4. **Apply meeting-specific design**
   - Read `references/deck-standards.md` and `references/visual-system.md`.
   - Keep the generated baseline when the user needs a fast usable version. For normal mode, refine its visual cue, section rhythm, supplied images, and special content without changing confirmed facts.
   - Dense brochure pages should normally remain source images; do not manually rebuild them unless editable text is requested.

5. **Verify**
   - Run:

     ```bash
     python3 <skill-dir>/scripts/check_run_ppt.py /absolute/path/to/run-ppt/<meeting-slug>.html
     ```

   - Inspect at `1280x720` and one narrow viewport: cover, densest slide, one speech slide, one role slide, and closing.
   - Check Arrow keys, Space, Page Up/Down, Home/End, click, fullscreen, page count, and progress.

## Fast Live-Use Mode

When the deck is needed immediately, ship the validated generated baseline first. Check the cover, densest page, and one representative role slide. State any skipped polish or source assumption. Do not delay a usable first version for a full visual redesign.

## Super AI Lab Content Boundaries

- Use only the location and names confirmed for the current meeting; do not insert a standing office address.
- Keep operational handoff scripts off visible slides unless presenter notes are explicitly requested.
- Preserve special segments from the agenda; do not flatten them into a generic Toastmasters flow.
- Do not turn a normal run deck into a recruitment brochure.
- Do not distribute or redraw official Logos. If the user supplies an authorized local Logo, keep it as a relative asset inside the output package; otherwise use text-only identity.
- Keep the ordinary visual tone professional, warm, energetic, and AI-aware without becoming a generic neon-tech template.

## Output Contract

Return in Chinese with:

- an absolute clickable path to the final HTML;
- slide count and the main meeting-specific changes;
- meeting validation, static check, and visual-QA results;
- any remaining assumption that can affect live use.
