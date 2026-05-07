"""Convert Marp markdown to editable Google Slides — paper-ink theme faithful port."""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/presentations",
]
CRED_DIR = Path(__file__).parent
CLIENT_SECRETS = CRED_DIR / "client_secret_2_334109913877-evq7s44u0t403puqk4vhhkocnhokhpv5.apps.googleusercontent.com.json"
TOKEN_FILE = CRED_DIR / "token_slides.json"

# === Paper-ink theme colors (from paper-ink.css) ===
INK = {"red": 0.067, "green": 0.067, "blue": 0.067}  # #111111
INK_SUB = {"red": 0.369, "green": 0.353, "blue": 0.333}  # #5E5A55
PAPER = {"red": 0.980, "green": 0.980, "blue": 0.969}  # #FAFAF7
PAPER_2 = {"red": 0.933, "green": 0.922, "blue": 0.890}  # #EEEBE3
ACCENT = {"red": 1.0, "green": 0.353, "blue": 0.122}  # #FF5A1F
LINE = {"red": 0.851, "green": 0.835, "blue": 0.796}  # #D9D5CB
WHITE = {"red": 1.0, "green": 1.0, "blue": 1.0}

# Fonts — Pretendard not in Google Fonts; closest match is Noto Sans KR
TITLE_FONT = "Noto Sans KR"
BODY_FONT = "Noto Sans KR"
MONO_FONT = "Roboto Mono"  # Google Fonts (JetBrains Mono may not be available)

# Slide dimensions (16:9 default in Slides = 10" × 5.625" = 720 × 405 pt)
PT = 12700  # EMU per pt
IN_ = 914400  # EMU per inch
SLIDE_W = 10 * IN_        # 720 pt
SLIDE_H = int(5.625 * IN_)  # 405 pt

# Padding — Marp uses 72×88 px on 1280×720, ratio ~5.6%×6.9%
# On 720×405 pt Google Slide: 50pt × 23pt (scaled down)
PAD_X = 50 * PT
PAD_Y = 28 * PT


# ===================== Auth =====================

def get_credentials():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())
    return creds


# ===================== Inline markdown parser =====================

@dataclass
class Run:
    """A styled run of text: character range [start, end) with style kind."""
    start: int
    end: int
    kind: str  # 'bold', 'italic', 'code', 'link'
    url: str | None = None


def parse_inline(text: str) -> tuple[str, list[Run]]:
    """Parse **bold**, *italic*, `code`, [text](url). Returns (plain_text, runs)."""
    out: list[str] = []
    runs: list[Run] = []
    i = 0
    n = len(text)

    def current_pos() -> int:
        return sum(len(s) for s in out)

    while i < n:
        c = text[i]

        # Image ![alt](url) — keep alt text
        if c == "!" and i + 1 < n and text[i + 1] == "[":
            m = re.match(r"!\[([^\]]*)\]\([^)]+\)", text[i:])
            if m:
                out.append(m.group(1) or "[image]")
                i += m.end()
                continue

        # Link [text](url)
        if c == "[":
            m = re.match(r"\[([^\]]+)\]\(([^)]+)\)", text[i:])
            if m:
                link_text = m.group(1)
                link_url = m.group(2)
                start = current_pos()
                out.append(link_text)
                runs.append(Run(start, start + len(link_text), "link", link_url))
                i += m.end()
                continue

        # Bold **...**
        if text.startswith("**", i):
            end = text.find("**", i + 2)
            if end != -1:
                inner = text[i + 2 : end]
                start = current_pos()
                out.append(inner)
                runs.append(Run(start, start + len(inner), "bold"))
                i = end + 2
                continue

        # Italic *...*  (single star, not **)
        if c == "*" and (i + 1 >= n or text[i + 1] != "*"):
            # Find closing * (not **)
            j = i + 1
            while j < n:
                if text[j] == "*" and (j + 1 >= n or text[j + 1] != "*"):
                    inner = text[i + 1 : j]
                    if inner and "\n" not in inner:
                        start = current_pos()
                        out.append(inner)
                        runs.append(Run(start, start + len(inner), "italic"))
                        i = j + 1
                        break
                    else:
                        break
                j += 1
            else:
                out.append(c)
                i += 1
                continue
            if i == j + 1:
                continue
            # fallthrough if no match
            out.append(c)
            i += 1
            continue

        # Inline code `...`
        if c == "`":
            end = text.find("`", i + 1)
            if end != -1:
                inner = text[i + 1 : end]
                start = current_pos()
                out.append(inner)
                runs.append(Run(start, start + len(inner), "code"))
                i = end + 1
                continue

        out.append(c)
        i += 1

    return "".join(out), runs


# ===================== Slide-level parser =====================

@dataclass
class Block:
    type: str
    text: str = ""
    items: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    level: int = 0


@dataclass
class Slide:
    title: str | None = None
    subtitle: str | None = None  # for cover
    class_hint: str | None = None
    blocks: list[Block] = field(default_factory=list)
    footnote: str | None = None  # <div class="footnote">...</div>
    url_block: str | None = None  # <div class="url-block">...</div>


def _strip_html(text: str) -> str:
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"</div>", "\n", text)
    text = re.sub(r"<div[^>]*>", "", text)
    text = re.sub(r"</?span[^>]*>", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text


def _extract_footnote(raw: str) -> tuple[str, str | None]:
    """Pop <div class='footnote'>...</div> out of raw; return (remaining, footnote_text|None)."""
    m = re.search(
        r'<div\s+class="footnote"[^>]*>(.*?)</div>',
        raw,
        flags=re.DOTALL,
    )
    if not m:
        return raw, None
    inner = m.group(1)
    # strip <a href>text</a> → text
    inner = re.sub(r'<a\s+href="[^"]*"[^>]*>(.*?)</a>', r"\1", inner)
    inner = re.sub(r"<[^>]+>", "", inner)
    inner = re.sub(r"\s+", " ", inner).strip()
    remaining = raw[: m.start()] + raw[m.end() :]
    return remaining, inner


def _extract_url_block(raw: str) -> tuple[str, str | None]:
    """Pop <div class='url-block'>...</div> out. Returns (remaining, url_text|None)."""
    m = re.search(
        r'<div\s+class="url-block"[^>]*>(.*?)</div>',
        raw,
        flags=re.DOTALL,
    )
    if not m:
        return raw, None
    inner = m.group(1)
    inner = re.sub(r"<[^>]+>", "", inner)
    inner = inner.strip()
    remaining = raw[: m.start()] + raw[m.end() :]
    return remaining, inner


def _detect_class(text: str) -> str | None:
    m = re.search(r"<!--\s*_class:\s*(\w+)\s*-->", text)
    return m.group(1) if m else None


def _strip_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def parse_slide(raw: str) -> Slide:
    class_hint = _detect_class(raw)
    raw = _strip_comments(raw)
    raw, footnote = _extract_footnote(raw)
    raw, url_block = _extract_url_block(raw)
    raw = _strip_html(raw)
    lines = raw.split("\n")

    slide = Slide(class_hint=class_hint, footnote=footnote, url_block=url_block)
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue

        # Heading
        m = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if m:
            level = len(m.group(1))
            text = m.group(2)
            if slide.title is None and level <= 2:
                slide.title = text
            elif slide.class_hint == "cover" and slide.subtitle is None and level == 2:
                slide.subtitle = text
            else:
                slide.blocks.append(Block(type="heading", text=text, level=level))
            i += 1
            continue

        # Table
        if stripped.startswith("|") and stripped.endswith("|"):
            tbl = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                tbl.append(lines[i].strip())
                i += 1
            rows = _parse_table(tbl)
            if rows:
                slide.blocks.append(Block(type="table", rows=rows))
            continue

        # Code block
        if stripped.startswith("```"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1
            slide.blocks.append(Block(type="code", text="\n".join(code_lines)))
            continue

        # Bullet list
        if re.match(r"^[-*+]\s+", stripped):
            items = []
            while i < len(lines) and re.match(r"^[-*+]\s+", lines[i].strip()):
                m = re.match(r"^[-*+]\s+(.+)$", lines[i].strip())
                items.append(m.group(1))
                i += 1
            slide.blocks.append(Block(type="list", items=items))
            continue

        # Ordered list
        if re.match(r"^\d+\.\s+", stripped):
            items = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i].strip()):
                m = re.match(r"^\d+\.\s+(.+)$", lines[i].strip())
                items.append(m.group(1))
                i += 1
            slide.blocks.append(Block(type="ordered_list", items=items))
            continue

        # Blockquote
        if stripped.startswith(">"):
            q_lines = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                q_lines.append(re.sub(r"^>\s?", "", lines[i].strip()))
                i += 1
            slide.blocks.append(Block(type="blockquote", text="\n".join(q_lines)))
            continue

        # Paragraph
        para = []
        while i < len(lines):
            l = lines[i].strip()
            if not l:
                break
            if (
                l.startswith("#")
                or re.match(r"^[-*+]\s+", l)
                or re.match(r"^\d+\.\s+", l)
                or l.startswith("|")
                or l.startswith("```")
                or l.startswith(">")
            ):
                break
            para.append(l)
            i += 1
        if para:
            # Preserve line breaks (Marp breaks:true behaviour)
            slide.blocks.append(Block(type="paragraph", text="\n".join(para)))

    return slide


def _parse_table(lines: list[str]) -> list[list[str]]:
    rows = []
    for line in lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(re.match(r"^:?-+:?$", c) for c in cells if c):
            continue
        rows.append(cells)
    return rows


def parse_marp_markdown(path: Path) -> list[Slide]:
    content = path.read_text()
    content = re.sub(r"^---\s*\n.*?\n---\s*\n", "", content, flags=re.DOTALL)
    raw_slides = re.split(r"\n---\s*\n", content)
    return [parse_slide(r) for r in raw_slides if r.strip()]


# ===================== Slides API helpers =====================

def color_fill(color: dict) -> dict:
    return {"solidFill": {"color": {"rgbColor": color}}}


def rgb_style(color: dict) -> dict:
    return {"opaqueColor": {"rgbColor": color}}


def req_bg(slide_id: str, color: dict) -> dict:
    return {
        "updatePageProperties": {
            "objectId": slide_id,
            "pageProperties": {"pageBackgroundFill": color_fill(color)},
            "fields": "pageBackgroundFill",
        }
    }


def req_shape(slide_id: str, obj_id: str, x: int, y: int, w: int, h: int, shape: str = "TEXT_BOX") -> dict:
    return {
        "createShape": {
            "objectId": obj_id,
            "shapeType": shape,
            "elementProperties": {
                "pageObjectId": slide_id,
                "size": {"width": {"magnitude": w, "unit": "EMU"}, "height": {"magnitude": h, "unit": "EMU"}},
                "transform": {"scaleX": 1, "scaleY": 1, "translateX": x, "translateY": y, "unit": "EMU"},
            },
        }
    }


def req_line(slide_id: str, obj_id: str, x: int, y: int, w: int) -> dict:
    return {
        "createLine": {
            "objectId": obj_id,
            "lineCategory": "STRAIGHT",
            "elementProperties": {
                "pageObjectId": slide_id,
                "size": {"width": {"magnitude": w, "unit": "EMU"}, "height": {"magnitude": 1, "unit": "EMU"}},
                "transform": {"scaleX": 1, "scaleY": 1, "translateX": x, "translateY": y, "unit": "EMU"},
            },
        }
    }


def req_insert_text(obj_id: str, text: str) -> dict:
    return {"insertText": {"objectId": obj_id, "text": text, "insertionIndex": 0}}


def req_text_style_range(obj_id: str, start: int, end: int, style: dict, fields: str) -> dict:
    return {
        "updateTextStyle": {
            "objectId": obj_id,
            "textRange": {"type": "FIXED_RANGE", "startIndex": start, "endIndex": end},
            "style": style,
            "fields": fields,
        }
    }


def req_text_style_all(obj_id: str, style: dict, fields: str) -> dict:
    return {
        "updateTextStyle": {
            "objectId": obj_id,
            "textRange": {"type": "ALL"},
            "style": style,
            "fields": fields,
        }
    }


def req_para_style_range(obj_id: str, start: int, end: int, style: dict, fields: str) -> dict:
    return {
        "updateParagraphStyle": {
            "objectId": obj_id,
            "textRange": {"type": "FIXED_RANGE", "startIndex": start, "endIndex": end},
            "style": style,
            "fields": fields,
        }
    }


def req_line_spacing_all(obj_id: str, percent: int = 150) -> dict:
    """Set line spacing as % (150 = 1.5). Applies to all paragraphs in shape."""
    return {
        "updateParagraphStyle": {
            "objectId": obj_id,
            "textRange": {"type": "ALL"},
            "style": {"lineSpacing": percent, "spaceAbove": {"magnitude": 2, "unit": "PT"}, "spaceBelow": {"magnitude": 2, "unit": "PT"}},
            "fields": "lineSpacing,spaceAbove,spaceBelow",
        }
    }


def req_bullets_range(obj_id: str, start: int, end: int, preset: str = "BULLET_DISC_CIRCLE_SQUARE") -> dict:
    return {
        "createParagraphBullets": {
            "objectId": obj_id,
            "textRange": {"type": "FIXED_RANGE", "startIndex": start, "endIndex": end},
            "bulletPreset": preset,
        }
    }


def req_shape_fill(obj_id: str, color: dict) -> dict:
    return {
        "updateShapeProperties": {
            "objectId": obj_id,
            "shapeProperties": {"shapeBackgroundFill": color_fill(color)},
            "fields": "shapeBackgroundFill",
        }
    }


def req_shape_no_border(obj_id: str) -> dict:
    return {
        "updateShapeProperties": {
            "objectId": obj_id,
            "shapeProperties": {"outline": {"outlineFill": {"solidFill": {"color": {"rgbColor": PAPER}, "alpha": 0}}}},
            "fields": "outline.outlineFill.solidFill.alpha",
        }
    }


def apply_inline_runs(obj_id: str, base_offset: int, runs: list[Run]) -> list[dict]:
    """Return style requests for inline markdown runs (bold/italic/code/link)."""
    out = []
    for r in runs:
        s = base_offset + r.start
        e = base_offset + r.end
        if r.kind == "bold":
            out.append(
                req_text_style_range(
                    obj_id, s, e,
                    {"bold": True, "foregroundColor": rgb_style(ACCENT)},
                    "bold,foregroundColor",
                )
            )
        elif r.kind == "italic":
            out.append(
                req_text_style_range(
                    obj_id, s, e,
                    {"italic": True, "foregroundColor": rgb_style(INK)},
                    "italic,foregroundColor",
                )
            )
        elif r.kind == "code":
            out.append(
                req_text_style_range(
                    obj_id, s, e,
                    {
                        "fontFamily": MONO_FONT,
                        "backgroundColor": rgb_style(PAPER_2),
                        "foregroundColor": rgb_style(INK),
                    },
                    "fontFamily,backgroundColor,foregroundColor",
                )
            )
        elif r.kind == "link":
            out.append(
                req_text_style_range(
                    obj_id, s, e,
                    {"link": {"url": r.url}, "foregroundColor": rgb_style(INK_SUB), "underline": True},
                    "link,foregroundColor,underline",
                )
            )
    return out


# ===================== Slide builders (class-specific) =====================

def build_cover(slide_id: str, slide: Slide) -> list[dict]:
    """Cover: paper bg, 12px orange left border, huge title, subtitle, body."""
    reqs = [req_bg(slide_id, PAPER)]

    # Orange left border (12px wide rectangle, full height)
    border_id = f"{slide_id}_border"
    reqs.append(req_shape(slide_id, border_id, 0, 0, 12 * PT, SLIDE_H, shape="RECTANGLE"))
    reqs.append(req_shape_fill(border_id, ACCENT))
    reqs.append(req_shape_no_border(border_id))

    # Layout: title @35%, subtitle @55%, body @70% — fixed gaps, no overlap
    inner_x = PAD_X + 20 * PT  # extra left padding to clear the stripe
    inner_w = SLIDE_W - inner_x - PAD_X

    # Title (single line — use 48pt so it fits in 1 line)
    if slide.title:
        title_id = f"{slide_id}_title"
        reqs.append(req_shape(slide_id, title_id, inner_x, int(SLIDE_H * 0.28), inner_w, 80 * PT))
        plain, runs = parse_inline(slide.title)
        reqs.append(req_insert_text(title_id, plain))
        reqs.append(
            req_text_style_all(
                title_id,
                {
                    "fontFamily": TITLE_FONT,
                    "fontSize": {"magnitude": 48, "unit": "PT"},
                    "bold": True,
                    "foregroundColor": rgb_style(INK),
                },
                "fontFamily,fontSize,bold,foregroundColor",
            )
        )
        reqs.extend(apply_inline_runs(title_id, 0, runs))

    # Subtitle (H2)
    if slide.subtitle:
        sub_id = f"{slide_id}_sub"
        reqs.append(req_shape(slide_id, sub_id, inner_x, int(SLIDE_H * 0.56), inner_w, 40 * PT))
        plain, runs = parse_inline(slide.subtitle)
        reqs.append(req_insert_text(sub_id, plain))
        reqs.append(
            req_text_style_all(
                sub_id,
                {
                    "fontFamily": TITLE_FONT,
                    "fontSize": {"magnitude": 20, "unit": "PT"},
                    "foregroundColor": rgb_style(INK_SUB),
                },
                "fontFamily,fontSize,foregroundColor",
            )
        )

    # Body (date/author paragraphs)
    text_content = []
    for b in slide.blocks:
        if b.type == "paragraph":
            text_content.append(b.text)
    if text_content:
        body_id = f"{slide_id}_body"
        reqs.append(req_shape(slide_id, body_id, inner_x, int(SLIDE_H * 0.70), inner_w, 80 * PT))
        combined = "\n".join(text_content)
        plain, runs = parse_inline(combined)
        reqs.append(req_insert_text(body_id, plain))
        reqs.append(
            req_text_style_all(
                body_id,
                {
                    "fontFamily": BODY_FONT,
                    "fontSize": {"magnitude": 15, "unit": "PT"},
                    "foregroundColor": rgb_style(INK_SUB),
                },
                "fontFamily,fontSize,foregroundColor",
            )
        )
        reqs.append(req_line_spacing_all(body_id, 140))
        reqs.extend(apply_inline_runs(body_id, 0, runs))

    return reqs


def build_divider(slide_id: str, slide: Slide) -> list[dict]:
    """Divider: black bg, centered huge title (orange if class=divider H2, white H1)."""
    reqs = [req_bg(slide_id, INK)]

    if slide.title:
        title_id = f"{slide_id}_title"
        reqs.append(req_shape(slide_id, title_id, PAD_X, int(SLIDE_H * 0.32), SLIDE_W - PAD_X * 2, 180 * PT))
        plain, runs = parse_inline(slide.title)
        reqs.append(req_insert_text(title_id, plain))
        reqs.append(
            req_text_style_all(
                title_id,
                {
                    "fontFamily": TITLE_FONT,
                    "fontSize": {"magnitude": 72, "unit": "PT"},
                    "bold": True,
                    "foregroundColor": rgb_style(PAPER),
                },
                "fontFamily,fontSize,bold,foregroundColor",
            )
        )
        reqs.append(
            req_para_style_range(
                title_id, 0, len(plain) + 1,
                {"alignment": "CENTER"},
                "alignment",
            )
        )

    # Subtitle-like H2 in body blocks → accent orange
    for b in slide.blocks:
        if b.type == "heading" and b.level == 2:
            sub_id = f"{slide_id}_sub"
            reqs.append(req_shape(slide_id, sub_id, PAD_X, int(SLIDE_H * 0.58), SLIDE_W - PAD_X * 2, 50 * PT))
            plain, runs = parse_inline(b.text)
            reqs.append(req_insert_text(sub_id, plain))
            reqs.append(
                req_text_style_all(
                    sub_id,
                    {
                        "fontFamily": TITLE_FONT,
                        "fontSize": {"magnitude": 28, "unit": "PT"},
                        "foregroundColor": rgb_style(ACCENT),
                    },
                    "fontFamily,fontSize,foregroundColor",
                )
            )
            reqs.append(
                req_para_style_range(sub_id, 0, len(plain) + 1, {"alignment": "CENTER"}, "alignment")
            )
            break

    return reqs


def build_bigpoint(slide_id: str, slide: Slide) -> list[dict]:
    """Bigpoint: paper bg, huge title, large subtitle."""
    reqs = [req_bg(slide_id, PAPER)]

    if slide.title:
        title_id = f"{slide_id}_title"
        reqs.append(req_shape(slide_id, title_id, PAD_X, int(SLIDE_H * 0.25), SLIDE_W - PAD_X * 2, 200 * PT))
        plain, runs = parse_inline(slide.title)
        reqs.append(req_insert_text(title_id, plain))
        reqs.append(
            req_text_style_all(
                title_id,
                {
                    "fontFamily": TITLE_FONT,
                    "fontSize": {"magnitude": 68, "unit": "PT"},
                    "bold": True,
                    "foregroundColor": rgb_style(INK),
                },
                "fontFamily,fontSize,bold,foregroundColor",
            )
        )
        reqs.extend(apply_inline_runs(title_id, 0, runs))

    # Paragraphs below
    paras = [b.text for b in slide.blocks if b.type == "paragraph"]
    if paras:
        body_id = f"{slide_id}_body"
        reqs.append(req_shape(slide_id, body_id, PAD_X, int(SLIDE_H * 0.6), SLIDE_W - PAD_X * 2, 120 * PT))
        combined = "\n".join(paras)
        plain, runs = parse_inline(combined)
        reqs.append(req_insert_text(body_id, plain))
        reqs.append(
            req_text_style_all(
                body_id,
                {
                    "fontFamily": BODY_FONT,
                    "fontSize": {"magnitude": 22, "unit": "PT"},
                    "foregroundColor": rgb_style(INK_SUB),
                },
                "fontFamily,fontSize,foregroundColor",
            )
        )
        reqs.append(req_line_spacing_all(body_id, 150))
        reqs.extend(apply_inline_runs(body_id, 0, runs))

    return reqs


def _content_density(slide: Slide) -> str:
    """Return 'compact' | 'normal' based on bulk of content."""
    items = 0
    paras = 0
    chars = 0
    for b in slide.blocks:
        if b.type in ("list", "ordered_list"):
            items += len(b.items)
            chars += sum(len(i) for i in b.items)
        elif b.type == "paragraph":
            paras += 1
            chars += len(b.text)
        elif b.type == "table":
            items += len(b.rows)
        elif b.type in ("code", "blockquote"):
            chars += len(b.text)
    # Thresholds tuned for 2h-deck slides
    if items >= 7 or chars > 450 or (items >= 5 and paras >= 2):
        return "compact"
    return "normal"


def build_standard(slide_id: str, slide: Slide) -> list[dict]:
    """Standard content slide: paper bg, H2 title with underline, body blocks."""
    reqs = [req_bg(slide_id, PAPER)]

    content_w = SLIDE_W - PAD_X * 2
    cur_y = PAD_Y

    density = _content_density(slide)
    body_size = 15 if density == "compact" else 17
    list_spacing = 125 if density == "compact" else 150
    item_h = 26 if density == "compact" else 30  # pt per list item (incl. spacing)
    para_h = 24 if density == "compact" else 28  # pt per paragraph line

    # Title with border-bottom effect
    if slide.title:
        title_id = f"{slide_id}_title"
        title_h = 42 * PT  # tight fit for 34pt text
        reqs.append(req_shape(slide_id, title_id, PAD_X, cur_y, content_w, title_h))
        plain, runs = parse_inline(slide.title)
        reqs.append(req_insert_text(title_id, plain))
        reqs.append(
            req_text_style_all(
                title_id,
                {
                    "fontFamily": TITLE_FONT,
                    "fontSize": {"magnitude": 34, "unit": "PT"},
                    "bold": True,
                    "foregroundColor": rgb_style(INK),
                },
                "fontFamily,fontSize,bold,foregroundColor",
            )
        )
        reqs.extend(apply_inline_runs(title_id, 0, runs))
        cur_y += title_h + 2 * PT

        # Underline: short fixed-width rectangle (fake border-bottom, inline-block style)
        underline_id = f"{slide_id}_title_bar"
        underline_w = min(int(len(plain) * 18 * PT), content_w)  # approx text width
        reqs.append(req_shape(slide_id, underline_id, PAD_X, cur_y, underline_w, 3 * PT, shape="RECTANGLE"))
        reqs.append(req_shape_fill(underline_id, INK))
        reqs.append(req_shape_no_border(underline_id))
        cur_y += 12 * PT

    # Activity badge
    if slide.class_hint == "activity":
        badge_id = f"{slide_id}_badge"
        reqs.append(req_shape(slide_id, badge_id, SLIDE_W - 140 * PT, PAD_Y, 110 * PT, 28 * PT, shape="RECTANGLE"))
        reqs.append(req_shape_fill(badge_id, INK))
        reqs.append(req_insert_text(badge_id, "⏱ 실습"))
        reqs.append(
            req_text_style_all(
                badge_id,
                {
                    "fontFamily": TITLE_FONT,
                    "fontSize": {"magnitude": 13, "unit": "PT"},
                    "bold": True,
                    "foregroundColor": rgb_style(PAPER),
                },
                "fontFamily,fontSize,bold,foregroundColor",
            )
        )
        reqs.append(
            req_para_style_range(badge_id, 0, 4, {"alignment": "CENTER"}, "alignment")
        )

    # URL block (large centered display)
    if slide.url_block:
        url_id = f"{slide_id}_url"
        url_h = 60 * PT
        reqs.append(req_shape(slide_id, url_id, PAD_X, cur_y, content_w, url_h))
        reqs.append(req_insert_text(url_id, slide.url_block))
        reqs.append(
            req_text_style_all(
                url_id,
                {
                    "fontFamily": TITLE_FONT,
                    "fontSize": {"magnitude": 40, "unit": "PT"},
                    "bold": True,
                    "foregroundColor": rgb_style(INK),
                },
                "fontFamily,fontSize,bold,foregroundColor",
            )
        )
        reqs.append(
            req_para_style_range(
                url_id, 0, len(slide.url_block) + 1,
                {"alignment": "CENTER"}, "alignment",
            )
        )
        cur_y += url_h + 10 * PT

    # Body blocks
    for block in slide.blocks:
        if block.type == "heading":
            h_id = f"{slide_id}_h_{len(reqs)}"
            h_size = {3: 22, 4: 18, 5: 16}.get(block.level, 18)
            h_h = 30 * PT
            reqs.append(req_shape(slide_id, h_id, PAD_X, cur_y, content_w, h_h))
            plain, runs = parse_inline(block.text)
            reqs.append(req_insert_text(h_id, plain))
            color = ACCENT if block.level == 3 else INK
            reqs.append(
                req_text_style_all(
                    h_id,
                    {
                        "fontFamily": TITLE_FONT,
                        "fontSize": {"magnitude": h_size, "unit": "PT"},
                        "bold": True,
                        "foregroundColor": rgb_style(color),
                    },
                    "fontFamily,fontSize,bold,foregroundColor",
                )
            )
            reqs.extend(apply_inline_runs(h_id, 0, runs))
            cur_y += h_h + 4 * PT

        elif block.type == "paragraph":
            p_id = f"{slide_id}_p_{len(reqs)}"
            plain, runs = parse_inline(block.text)
            est_lines = max(1, len(plain) // 70 + plain.count("\n") + 1)
            p_h = min(est_lines * para_h * PT + 10 * PT, SLIDE_H - cur_y - PAD_Y)
            reqs.append(req_shape(slide_id, p_id, PAD_X, cur_y, content_w, p_h))
            reqs.append(req_insert_text(p_id, plain))
            reqs.append(
                req_text_style_all(
                    p_id,
                    {
                        "fontFamily": BODY_FONT,
                        "fontSize": {"magnitude": body_size, "unit": "PT"},
                        "foregroundColor": rgb_style(INK),
                    },
                    "fontFamily,fontSize,foregroundColor",
                )
            )
            reqs.append(req_line_spacing_all(p_id, list_spacing))
            reqs.extend(apply_inline_runs(p_id, 0, runs))
            cur_y += p_h + 6 * PT

        elif block.type in ("list", "ordered_list"):
            l_id = f"{slide_id}_l_{len(reqs)}"
            items_plain: list[tuple[str, list[Run]]] = [parse_inline(item) for item in block.items]
            combined = "\n".join(p for p, _ in items_plain)
            est_h = min(len(block.items) * item_h * PT + 10 * PT, SLIDE_H - cur_y - PAD_Y)
            reqs.append(req_shape(slide_id, l_id, PAD_X, cur_y, content_w, est_h))
            reqs.append(req_insert_text(l_id, combined))
            reqs.append(
                req_text_style_all(
                    l_id,
                    {
                        "fontFamily": BODY_FONT,
                        "fontSize": {"magnitude": body_size, "unit": "PT"},
                        "foregroundColor": rgb_style(INK),
                    },
                    "fontFamily,fontSize,foregroundColor",
                )
            )
            reqs.append(req_line_spacing_all(l_id, list_spacing))
            # Apply inline runs with per-item offset
            offset = 0
            for plain, runs in items_plain:
                reqs.extend(apply_inline_runs(l_id, offset, runs))
                offset += len(plain) + 1  # +1 for newline
            # Native bullets
            preset = "NUMBERED_DIGIT_ALPHA_ROMAN" if block.type == "ordered_list" else "BULLET_DISC_CIRCLE_SQUARE"
            reqs.append(req_bullets_range(l_id, 0, len(combined) + 1, preset))
            cur_y += est_h + 6 * PT

        elif block.type == "code":
            c_id = f"{slide_id}_c_{len(reqs)}"
            lines = block.text.split("\n")
            est_h = min(len(lines) * 16 * PT + 16 * PT, SLIDE_H - cur_y - PAD_Y)
            reqs.append(req_shape(slide_id, c_id, PAD_X, cur_y, content_w, est_h, shape="RECTANGLE"))
            reqs.append(req_shape_fill(c_id, PAPER_2))
            reqs.append(req_insert_text(c_id, block.text))
            reqs.append(
                req_text_style_all(
                    c_id,
                    {
                        "fontFamily": MONO_FONT,
                        "fontSize": {"magnitude": 11, "unit": "PT"},
                        "foregroundColor": rgb_style(INK),
                    },
                    "fontFamily,fontSize,foregroundColor",
                )
            )
            cur_y += est_h + 6 * PT

        elif block.type == "blockquote":
            q_id = f"{slide_id}_q_{len(reqs)}"
            plain, runs = parse_inline(block.text)
            est_lines = max(1, plain.count("\n") + 1 + len(plain) // 70)
            q_h = min(est_lines * 22 * PT + 14 * PT, SLIDE_H - cur_y - PAD_Y)
            # Quote box offset right so left bar is visible outside
            q_left = PAD_X + 5 * PT
            q_w = content_w - 5 * PT
            reqs.append(req_shape(slide_id, q_id, q_left, cur_y, q_w, q_h, shape="RECTANGLE"))
            reqs.append(req_shape_fill(q_id, PAPER_2))
            reqs.append(req_shape_no_border(q_id))
            reqs.append(req_insert_text(q_id, plain))
            reqs.append(
                req_text_style_all(
                    q_id,
                    {
                        "fontFamily": BODY_FONT,
                        "fontSize": {"magnitude": 14, "unit": "PT"},
                        "foregroundColor": rgb_style(INK),
                    },
                    "fontFamily,fontSize,foregroundColor",
                )
            )
            # Force LEFT alignment (default TEXT_BOX may center)
            reqs.append(
                req_para_style_range(q_id, 0, len(plain) + 1, {"alignment": "START"}, "alignment")
            )
            reqs.append(req_line_spacing_all(q_id, 140))
            reqs.extend(apply_inline_runs(q_id, 0, runs))

            # Left border bar (5pt ink, drawn AFTER quote so it renders on top)
            bar_id = f"{slide_id}_qbar_{len(reqs)}"
            reqs.append(req_shape(slide_id, bar_id, PAD_X, cur_y, 5 * PT, q_h, shape="RECTANGLE"))
            reqs.append(req_shape_fill(bar_id, INK))
            reqs.append(req_shape_no_border(bar_id))

            cur_y += q_h + 6 * PT

        elif block.type == "table":
            rows = block.rows
            if not rows:
                continue
            nrows, ncols = len(rows), max(len(r) for r in rows)
            t_id = f"{slide_id}_t_{len(reqs)}"
            t_h = min(nrows * 28 * PT + 10 * PT, SLIDE_H - cur_y - PAD_Y)
            reqs.append(
                {
                    "createTable": {
                        "objectId": t_id,
                        "elementProperties": {
                            "pageObjectId": slide_id,
                            "size": {
                                "width": {"magnitude": content_w, "unit": "EMU"},
                                "height": {"magnitude": t_h, "unit": "EMU"},
                            },
                            "transform": {
                                "scaleX": 1, "scaleY": 1,
                                "translateX": PAD_X, "translateY": cur_y, "unit": "EMU",
                            },
                        },
                        "rows": nrows,
                        "columns": ncols,
                    }
                }
            )
            # Fill cells and style (tables get populated via cellLocation)
            # Note: inserts + styles after createTable. Must wait for table in separate batch,
            # but we'll send it all in one batchUpdate (Slides API handles ordering).
            for r_idx, row in enumerate(rows):
                for c_idx, cell in enumerate(row):
                    if c_idx >= ncols:
                        continue
                    plain, runs = parse_inline(cell or " ")
                    reqs.append(
                        {
                            "insertText": {
                                "objectId": t_id,
                                "cellLocation": {"rowIndex": r_idx, "columnIndex": c_idx},
                                "text": plain,
                                "insertionIndex": 0,
                            }
                        }
                    )
                    is_header = r_idx == 0
                    reqs.append(
                        {
                            "updateTextStyle": {
                                "objectId": t_id,
                                "cellLocation": {"rowIndex": r_idx, "columnIndex": c_idx},
                                "textRange": {"type": "ALL"},
                                "style": {
                                    "fontFamily": BODY_FONT,
                                    "fontSize": {"magnitude": 12, "unit": "PT"},
                                    "bold": is_header,
                                    "foregroundColor": rgb_style(PAPER if is_header else INK),
                                },
                                "fields": "fontFamily,fontSize,bold,foregroundColor",
                            }
                        }
                    )
                    # Apply inline runs within cell
                    for run in runs:
                        r_style = {}
                        r_fields = []
                        if run.kind == "bold":
                            r_style["bold"] = True
                            r_style["foregroundColor"] = rgb_style(ACCENT if not is_header else PAPER)
                            r_fields = ["bold", "foregroundColor"]
                        elif run.kind == "italic":
                            r_style["italic"] = True
                            r_fields = ["italic"]
                        elif run.kind == "code":
                            r_style["fontFamily"] = MONO_FONT
                            r_fields = ["fontFamily"]
                        if r_fields:
                            # header bold → orange (paper-ink: strong { color: var(--accent) })
                            if run.kind == "bold" and is_header:
                                r_style["foregroundColor"] = rgb_style(ACCENT)
                            reqs.append(
                                {
                                    "updateTextStyle": {
                                        "objectId": t_id,
                                        "cellLocation": {"rowIndex": r_idx, "columnIndex": c_idx},
                                        "textRange": {
                                            "type": "FIXED_RANGE",
                                            "startIndex": run.start,
                                            "endIndex": run.end,
                                        },
                                        "style": r_style,
                                        "fields": ",".join(r_fields),
                                    }
                                }
                            )
                    # Header row background
                    if is_header:
                        reqs.append(
                            {
                                "updateTableCellProperties": {
                                    "objectId": t_id,
                                    "tableRange": {
                                        "location": {"rowIndex": 0, "columnIndex": c_idx},
                                        "rowSpan": 1,
                                        "columnSpan": 1,
                                    },
                                    "tableCellProperties": {
                                        "tableCellBackgroundFill": color_fill(INK)
                                    },
                                    "fields": "tableCellBackgroundFill",
                                }
                            }
                        )
            cur_y += t_h + 6 * PT

    return reqs


def _add_footnote(slide_id: str, reqs: list[dict], slide: Slide) -> None:
    """Add small-text footnote at bottom of slide with separator line."""
    if not slide.footnote:
        return
    content_w = SLIDE_W - PAD_X * 2
    fn_y = SLIDE_H - 34 * PT  # 34pt above bottom edge
    # Separator line (top border of footnote)
    sep_id = f"{slide_id}_fn_sep"
    reqs.append(req_shape(slide_id, sep_id, PAD_X, fn_y, content_w, 1 * PT, shape="RECTANGLE"))
    reqs.append(req_shape_fill(sep_id, LINE))
    reqs.append(req_shape_no_border(sep_id))
    # Footnote text
    fn_id = f"{slide_id}_fn"
    reqs.append(req_shape(slide_id, fn_id, PAD_X, fn_y + 3 * PT, content_w, 28 * PT))
    plain, runs = parse_inline(slide.footnote)
    reqs.append(req_insert_text(fn_id, plain))
    reqs.append(
        req_text_style_all(
            fn_id,
            {
                "fontFamily": BODY_FONT,
                "fontSize": {"magnitude": 9, "unit": "PT"},
                "foregroundColor": rgb_style(INK_SUB),
            },
            "fontFamily,fontSize,foregroundColor",
        )
    )


def build_slide_requests(slide_id: str, slide: Slide) -> list[dict]:
    if slide.class_hint == "cover":
        reqs = build_cover(slide_id, slide)
    elif slide.class_hint == "divider":
        reqs = build_divider(slide_id, slide)
    elif slide.class_hint == "bigpoint":
        reqs = build_bigpoint(slide_id, slide)
    else:
        reqs = build_standard(slide_id, slide)
    _add_footnote(slide_id, reqs, slide)
    return reqs


# ===================== Orchestration =====================

def create_presentation(slides_data: list[Slide], title: str, creds) -> str:
    svc = build("slides", "v1", credentials=creds)
    pres = svc.presentations().create(body={"title": title}).execute()
    pres_id = pres["presentationId"]
    default_id = pres["slides"][0]["objectId"]

    # Create all blank slides
    create_reqs = [
        {
            "createSlide": {
                "objectId": f"slide_{i}",
                "slideLayoutReference": {"predefinedLayout": "BLANK"},
                "insertionIndex": i + 1,
            }
        }
        for i in range(len(slides_data))
    ]
    svc.presentations().batchUpdate(presentationId=pres_id, body={"requests": create_reqs}).execute()
    svc.presentations().batchUpdate(
        presentationId=pres_id,
        body={"requests": [{"deleteObject": {"objectId": default_id}}]},
    ).execute()

    # Populate
    for idx, slide in enumerate(slides_data):
        sid = f"slide_{idx}"
        reqs = build_slide_requests(sid, slide)
        CHUNK = 80
        for c in range(0, len(reqs), CHUNK):
            try:
                svc.presentations().batchUpdate(
                    presentationId=pres_id, body={"requests": reqs[c : c + CHUNK]}
                ).execute()
            except Exception as e:
                print(f"  ⚠️ slide {idx} chunk {c} failed: {e}", flush=True)
        print(f"  ✓ Slide {idx + 1}/{len(slides_data)}: {slide.title or f'[{slide.class_hint}]'}", flush=True)

    return pres_id


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("md_file", type=Path)
    ap.add_argument("--title", required=True)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    creds = get_credentials()
    slides = parse_marp_markdown(args.md_file)
    if args.limit:
        slides = slides[: args.limit]
    print(f"Parsed {len(slides)} slides from {args.md_file.name}", flush=True)

    pres_id = create_presentation(slides, args.title, creds)
    print(f"\n✅ Created: https://docs.google.com/presentation/d/{pres_id}/edit", flush=True)


if __name__ == "__main__":
    main()
