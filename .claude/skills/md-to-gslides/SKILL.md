---
name: md-to-gslides
description: >-
  Convert Markdown or Marp slides into editable, well-designed Google Slides
  via the Google Slides API. Use when the user wants to turn .md decks into
  editable Google Slides (not image-based PPTX), preserve a custom design
  (e.g., Marp theme), or programmatically generate themed presentations.
  Trigger on "md to google slides", "markdown → google slides", "marp to
  google slides", "슬라이드 편집 가능하게", "구글 슬라이드로 변환", "md→gslides",
  "gslides API", or any request to author/edit Google Slides programmatically.
---

# md-to-gslides

Convert structured markdown (Marp / CommonMark) into **editable** Google Slides with a custom theme, using the Google Slides API directly. Not image-based — every text box, table, and bullet is a native, editable Slides element.

## When to use

- User has Marp/markdown slides and wants Google Slides version that collaborators can edit
- PPTX export from Marp (image-based) isn't acceptable
- Need to preserve a custom theme (colors/fonts/layout classes) programmatically
- Building any tooling that produces Google Slides from structured input

## When NOT to use

- User just wants PDF or PPTX → use `marp --pdf` / `marp --pptx` directly
- User wants pixel-perfect Marp reproduction → impossible in native Slides; recommend Marp PDF/HTML for presentation + this skill for "editable companion"
- One-off slide creation → UI is faster than API

---

## Key architectural decisions (research-backed)

### Auth — OAuth with installed app flow

Scopes required:
```python
SCOPES = [
    "https://www.googleapis.com/auth/drive.file",         # create files
    "https://www.googleapis.com/auth/presentations",      # edit slides
]
```

OAuth client setup in GCP Console (Desktop app type), download JSON, use `google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(...).run_local_server(port=0)`. Cache token to reuse.

**Gotchas**:
- Project must enable **both** Drive API and Slides API (different APIs, separate enables)
- App in "Testing" mode → add every Google account that will authenticate as Test Users in OAuth consent screen, else `403 access_denied`
- Token file is per-scope — changing scopes requires deleting old token

### Direct API path vs PPTX-upload path

| Path | Editability | Visual fidelity to source | Effort |
|---|---|---|---|
| **A: Marp → PPTX → Drive copy (convert)** | Low — each slide becomes a fixed image | ⭐⭐⭐⭐⭐ | Minimal |
| **B: MD → Slides API direct** | High — native text/tables/bullets | ⭐⭐⭐ (approximation) | Significant script |

**Rule**: Use Path A when visuals matter more than editing; Path B when users must modify content. Document both in the output README.

### Template vs blank presentation

You **cannot create a theme via the API**. Best practice from `md2googleslides`:

1. User manually builds a themed template presentation in Google Slides UI
2. Script calls `drive.files().copy()` with that template ID → inherits all masters/layouts
3. `presentations().get()` to discover layout objectIds
4. `createSlide` references `slideLayoutReference.layoutId` + `placeholderIdMappings`

Only fall back to blank `presentations.create()` if no template exists.

---

## Request shapes (copy-paste ready)

### Units

- 1 inch = 914400 EMU = 72 PT
- Default 16:9 slide = 10" × 5.625" = 9144000 × 5143500 EMU = 720 × 405 PT
- **Use PT for layout magnitudes** (matches Slides editor ruler); EMU only when inheriting from Drive/Docs APIs

### Text box + styled text (one batch, predeclared objectId)

```python
# 1. Create shape
{"createShape": {
    "objectId": "box_1",
    "shapeType": "TEXT_BOX",
    "elementProperties": {
        "pageObjectId": slide_id,
        "size": {"width": {"magnitude": W, "unit": "EMU"}, "height": {"magnitude": H, "unit": "EMU"}},
        "transform": {"scaleX": 1, "scaleY": 1, "translateX": X, "translateY": Y, "unit": "EMU"},
    }
}}
# 2. Insert all text at once (single call per shape)
{"insertText": {"objectId": "box_1", "text": full_text, "insertionIndex": 0}}
# 3. Apply base style to everything
{"updateTextStyle": {
    "objectId": "box_1",
    "textRange": {"type": "ALL"},
    "style": {"fontFamily": "Noto Sans KR", "fontSize": {"magnitude": 16, "unit": "PT"}},
    "fields": "fontFamily,fontSize"
}}
# 4. Apply per-range styles (bold/italic/link) — iterate in REVERSE index order
{"updateTextStyle": {
    "objectId": "box_1",
    "textRange": {"type": "FIXED_RANGE", "startIndex": 10, "endIndex": 20},
    "style": {"bold": True, "foregroundColor": {"opaqueColor": {"rgbColor": accent}}},
    "fields": "bold,foregroundColor"
}}
```

**Critical**: every `update*` request MUST include `fields` mask. Omit a field from the mask and the server silently ignores it.

### Native bullets

```python
{"createParagraphBullets": {
    "objectId": "list_box",
    "textRange": {"type": "FIXED_RANGE", "startIndex": 0, "endIndex": len(text)+1},
    "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",  # or NUMBERED_DIGIT_ALPHA_ROMAN
}}
```

Nesting via leading `\t` characters in inserted text — `createParagraphBullets` strips them and uses the count as indent level. **Recompute text indices afterward** because `\t` strip shifts them.

### Tables with header styling

```python
# 1. Create table
{"createTable": {
    "objectId": "tbl",
    "elementProperties": {...},
    "rows": nrows, "columns": ncols,
}}
# 2. Insert per cell via cellLocation (NOT textRange)
{"insertText": {
    "objectId": "tbl",
    "cellLocation": {"rowIndex": 0, "columnIndex": 0},
    "text": "Header", "insertionIndex": 0,
}}
# 3. Style per cell
{"updateTextStyle": {
    "objectId": "tbl",
    "cellLocation": {"rowIndex": 0, "columnIndex": 0},  # distinct from tableRange
    "textRange": {"type": "ALL"},
    "style": {"bold": True, "foregroundColor": {"opaqueColor": {"rgbColor": paper}}},
    "fields": "bold,foregroundColor"
}}
# 4. Header row background (tableRange for multi-cell)
{"updateTableCellProperties": {
    "objectId": "tbl",
    "tableRange": {"location": {"rowIndex": 0, "columnIndex": 0},
                   "rowSpan": 1, "columnSpan": ncols},
    "tableCellProperties": {"tableCellBackgroundFill": {"solidFill": {"color": {"rgbColor": ink}}}},
    "fields": "tableCellBackgroundFill.solidFill.color"
}}
```

### Page background

```python
{"updatePageProperties": {
    "objectId": slide_id,
    "pageProperties": {"pageBackgroundFill": {"solidFill": {"color": {"rgbColor": paper}}}},
    "fields": "pageBackgroundFill"
}}
```

### Batching strategy

- **One `batchUpdate` per slide** — failures localize, stays under 500-request soft limit
- Keep chunk size ≤ 80 when many style updates involved
- `insertText` + `updateTextStyle` in the **same batch** after `createShape` — Slides API resolves ordering

---

## Parsing patterns (MD → structured slides)

### Slide separation

Marp/CommonMark: split on `^---$` (own line). First block is YAML frontmatter (skip). Each subsequent is one slide.

```python
content = re.sub(r"^---\s*\n.*?\n---\s*\n", "", content, flags=re.DOTALL)  # strip frontmatter
raw_slides = re.split(r"\n---\s*\n", content)
```

### Class hints

Marp: `<!-- _class: cover -->` (or `divider`, `bigpoint`, `activity`). Extract before stripping HTML:

```python
m = re.search(r"<!--\s*_class:\s*(\w+)\s*-->", raw)
class_hint = m.group(1) if m else None
```

### Inline formatting → runs

Parse `**bold**`, `*italic*`, `` `code` ``, `[text](url)` in a single pass, returning:
- Plain text (with all markers removed)
- List of `Run(start, end, kind, url?)` structs

Apply as `updateTextStyle` per range. **Key signature of paper-ink style**: `strong { color: var(--accent) }` → bold text becomes ORANGE, not just bold.

### Strip Marp-only HTML

```python
text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
text = re.sub(r"<br\s*/?>", "\n", text)
text = re.sub(r"</?div[^>]*>", "", text)
text = re.sub(r"<[^>]+>", "", text)  # strip anything else
```

Preserve the inner text.

---

## Fonts — Korean paper-ink aesthetic

**Pretendard is NOT in Google Fonts.** Use fallback:
- Primary: `"Noto Sans KR"` (always available, clean sans-serif close to Pretendard)
- Serif alt: `"Nanum Myeongjo"` or `"Gowun Batang"`
- Monospace: `"JetBrains Mono"` or `"Roboto Mono"` (Google Fonts)

Set `fontFamily` on every `updateTextStyle` — no document-level default exists.

---

## Class-specific layouts (Marp → Slides)

| Marp class | Slides rendering |
|---|---|
| `cover` | Paper bg + left-border rectangle (12px accent) + huge title + muted subtitle |
| `divider` | Ink bg, white centered title (72pt+), accent-orange subtitle |
| `bigpoint` | Paper bg, huge centered title (68pt+), muted body |
| `activity` | Standard layout + "⏱ 실습" badge shape top-right |
| (default) | Paper bg, H2 title with underline line, body blocks below |

Implement as separate builder functions (`build_cover`, `build_divider`, etc.) dispatched on `class_hint`.

---

## Reference implementation

Full working script at `/Users/jb_ai/workspace/credential/marp_to_slides.py`. Uses:
- `google-auth-oauthlib` for OAuth (InstalledAppFlow.run_local_server)
- `googleapiclient.discovery.build("slides", "v1")` for Slides API
- Paper-ink theme colors + Pretendard→Noto Sans KR font substitution
- Dispatch on class_hint for cover/divider/bigpoint/standard layouts
- Native bullets, inline-formatted runs, styled tables, code blocks with PAPER_2 background

### Run

```bash
# Assumes venv with google-api-python-client + google-auth-oauthlib
python marp_to_slides.py deck.md \
    --title "My Deck" \
    --limit 10   # optional: prototype first N slides before full run
```

First run opens browser for OAuth (once); subsequent runs reuse `token_slides.json`.

---

## Gotchas checklist

- [ ] Both Drive API and Slides API enabled in GCP project
- [ ] OAuth consent screen has test users added (if Testing mode)
- [ ] Every `update*` request has `fields` mask
- [ ] Style requests emitted in reverse text-index order (avoids shift issues)
- [ ] `createParagraphBullets` consumes `\t` — recompute indices after
- [ ] `tableRange` (multi-cell) vs `cellLocation` (single-cell) — not interchangeable
- [ ] Autofit auto-resets on text changes → set `TEXT_AUTOFIT` last if wanted
- [ ] Pretendard → Noto Sans KR substitution in every `fontFamily` write
- [ ] One `batchUpdate` per slide for locality + quota headroom
- [ ] Don't `presentations.create()` if you want theming — `drive.files.copy()` a themed template instead

---

## Primary sources

- [googleworkspace/md2googleslides](https://github.com/googleworkspace/md2googleslides) — archived 2025-11, canonical reference (read source for techniques)
- [Om3rr/markdown-to-googleslides](https://github.com/Om3rr/markdown-to-googleslides) — active fork with MCP server
- [Slides API batchUpdate reference](https://developers.google.com/slides/api/reference/rest/v1/presentations/batchUpdate)
- [Slides API: Styling text](https://developers.google.com/workspace/slides/api/guides/styling)
- [Slides API: Table operations](https://developers.google.com/workspace/slides/api/samples/tables)
- [Batch requests guide](https://developers.google.com/slides/api/guides/batch)
- [Noam Lerner — md2googleslides pitfalls](https://noamlerner.com/posts/md2googleslides/)

---

## Output checklist (end-of-task)

Before declaring done, verify:
- [ ] All slides created without `HttpError` in chunks
- [ ] User opened the URL, confirmed editability (click into text box → cursor appears)
- [ ] Bold text renders in accent color (not just bold black)
- [ ] Native bullets appear (not manually-prepended `•`)
- [ ] Tables have styled header row with dark fill
- [ ] Class-specific layouts differentiated (cover ≠ divider ≠ standard)
- [ ] Saved token cached for reuse
