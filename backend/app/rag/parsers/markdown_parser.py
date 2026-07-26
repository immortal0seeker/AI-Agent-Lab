from __future__ import annotations

import re
from pathlib import Path
from uuid import UUID

from .base import DocumentParseError, ParsedDocument

_UTF8_BOM = b"\xef\xbb\xbf"
_FENCE_OPEN = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})(.*)$")
_ATX_HEADING = re.compile(
    r"^[ \t]{0,3}(#{1,6})(?:[ \t]+|$)(.*)$"
)
_SETEXT_HEADING = re.compile(r"^[ \t]{0,3}(=+|-+)[ \t]*$")


def parse_markdown(path: Path, *, document_id: UUID) -> ParsedDocument:
    try:
        content = Path(path).read_bytes()
        encoding = "utf-8-sig" if content.startswith(_UTF8_BOM) else "utf-8"
        text = content.decode(encoding, errors="strict")
    except (OSError, UnicodeError) as exc:
        raise DocumentParseError() from exc

    headings, code_blocks = _extract_structure(text)
    return ParsedDocument(
        document_id=document_id,
        text=text,
        metadata={
            "format": "markdown",
            "encoding": encoding,
            "headings": headings,
            "code_blocks": code_blocks,
        },
    )


def _extract_structure(
    text: str,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    lines = text.splitlines()
    headings: list[dict[str, object]] = []
    code_blocks: list[dict[str, object]] = []
    line_index = 0

    while line_index < len(lines):
        line = lines[line_index]
        fence_match = _FENCE_OPEN.match(line)
        if fence_match is not None:
            fence = fence_match.group(1)
            info = fence_match.group(2).strip()
            language = info.split(maxsplit=1)[0] if info else ""
            closing_pattern = re.compile(
                rf"^[ \t]{{0,3}}{re.escape(fence[0])}"
                rf"{{{len(fence)},}}[ \t]*$"
            )
            start_line = line_index + 1
            content_lines: list[str] = []
            line_index += 1
            while line_index < len(lines):
                if closing_pattern.match(lines[line_index]):
                    end_line = line_index + 1
                    break
                content_lines.append(lines[line_index])
                line_index += 1
            else:
                end_line = len(lines)

            code_blocks.append(
                {
                    "language": language,
                    "content": "\n".join(content_lines),
                    "start_line": start_line,
                    "end_line": end_line,
                }
            )
            line_index += 1
            continue

        atx_match = _ATX_HEADING.match(line)
        if atx_match is not None:
            heading_text = re.sub(
                r"[ \t]+#+[ \t]*$",
                "",
                atx_match.group(2),
            ).strip()
            headings.append(
                {
                    "level": len(atx_match.group(1)),
                    "text": heading_text,
                    "line_number": line_index + 1,
                }
            )
            line_index += 1
            continue

        if line.strip() and line_index + 1 < len(lines):
            setext_match = _SETEXT_HEADING.match(lines[line_index + 1])
            if setext_match is not None:
                headings.append(
                    {
                        "level": 1
                        if setext_match.group(1).startswith("=")
                        else 2,
                        "text": line.strip(),
                        "line_number": line_index + 1,
                    }
                )
                line_index += 2
                continue

        line_index += 1

    return headings, code_blocks
