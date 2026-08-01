from copy import deepcopy
from dataclasses import dataclass

from app.rag.parsers import ParsedDocument, ParsedPage

_REMOVED_FORMAT_CHARACTERS = {"\ufeff", "\u200b", "\u2060"}


@dataclass(frozen=True)
class _CleanedLine:
    source_line: int
    text: str
    protected: bool


def clean_parsed_document(document: ParsedDocument) -> ParsedDocument:
    metadata = deepcopy(document.metadata)
    if document.pages is not None:
        pages = tuple(
            ParsedPage(
                page_number=page.page_number,
                text=_clean_text(page.text)[0],
            )
            for page in document.pages
        )
        return ParsedDocument(
            document_id=document.document_id,
            text="\n\n".join(page.text for page in pages),
            metadata=metadata,
            pages=pages,
        )

    if metadata.get("format") == "markdown":
        text, line_mapping = _clean_markdown_text(
            document.text,
            metadata.get("code_blocks"),
        )
    else:
        text, line_mapping = _clean_text(document.text)
    headings = metadata.get("headings")
    if isinstance(headings, list):
        for heading in headings:
            if not isinstance(heading, dict):
                continue
            source_line = heading.get("line_number")
            if type(source_line) is int and source_line in line_mapping:
                heading["line_number"] = line_mapping[source_line]
    code_blocks = metadata.get("code_blocks")
    if isinstance(code_blocks, list):
        for code_block in code_blocks:
            if not isinstance(code_block, dict):
                continue
            for field_name in ("start_line", "end_line"):
                source_line = code_block.get(field_name)
                if (
                    type(source_line) is int
                    and source_line in line_mapping
                ):
                    code_block[field_name] = line_mapping[source_line]
    return ParsedDocument(
        document_id=document.document_id,
        text=text,
        metadata=metadata,
    )


def _clean_text(text: str) -> tuple[str, dict[int, int]]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    output: list[str] = []
    line_mapping: dict[int, int] = {}
    for source_line, raw_line in enumerate(normalized.split("\n"), start=1):
        line = "".join(
            character
            for character in raw_line
            if _keep_character(character)
        )
        if not line.strip():
            if output and output[-1] != "":
                output.append("")
            continue
        output.append(line)
        line_mapping[source_line] = len(output)
    while output and output[-1] == "":
        output.pop()
    return "\n".join(output), line_mapping


def _clean_markdown_text(
    text: str,
    raw_code_blocks: object,
) -> tuple[str, dict[int, int]]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    source_lines = normalized.split("\n")
    protected_ranges = _validated_protected_ranges(
        raw_code_blocks,
        line_count=len(source_lines),
    )
    output: list[_CleanedLine] = []
    range_index = 0
    for source_line, raw_line in enumerate(source_lines, start=1):
        while (
            range_index < len(protected_ranges)
            and source_line > protected_ranges[range_index][1]
        ):
            range_index += 1
        protected = (
            range_index < len(protected_ranges)
            and protected_ranges[range_index][0]
            <= source_line
            <= protected_ranges[range_index][1]
        )
        line = "".join(
            character for character in raw_line if _keep_character(character)
        )
        if not line.strip():
            if protected:
                output.append(_CleanedLine(source_line, "", True))
            elif output and output[-1].text != "":
                output.append(_CleanedLine(source_line, "", False))
            continue
        output.append(_CleanedLine(source_line, line, protected))

    while output and output[0].text == "" and not output[0].protected:
        output.pop(0)
    while output and output[-1].text == "" and not output[-1].protected:
        output.pop()

    line_mapping = {
        item.source_line: cleaned_line
        for cleaned_line, item in enumerate(output, start=1)
    }
    return "\n".join(item.text for item in output), line_mapping


def _validated_protected_ranges(
    raw_code_blocks: object,
    *,
    line_count: int,
) -> list[tuple[int, int]]:
    if not isinstance(raw_code_blocks, list):
        return []
    ranges: list[tuple[int, int]] = []
    for code_block in raw_code_blocks:
        if not isinstance(code_block, dict):
            continue
        start_line = code_block.get("start_line")
        end_line = code_block.get("end_line")
        if (
            type(start_line) is not int
            or type(end_line) is not int
            or start_line < 1
            or end_line < start_line
            or end_line > line_count
        ):
            continue
        ranges.append((start_line, end_line))
    return _merge_ranges(ranges)


def _merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start_line, end_line in sorted(ranges):
        if not merged or start_line > merged[-1][1] + 1:
            merged.append((start_line, end_line))
            continue
        previous_start, previous_end = merged[-1]
        merged[-1] = (previous_start, max(previous_end, end_line))
    return merged


def _keep_character(character: str) -> bool:
    if character == "\t":
        return True
    codepoint = ord(character)
    if codepoint < 32 or 127 <= codepoint <= 159:
        return False
    return character not in _REMOVED_FORMAT_CHARACTERS
