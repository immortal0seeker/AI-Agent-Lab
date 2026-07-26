from copy import deepcopy

from app.rag.parsers import ParsedDocument, ParsedPage

_REMOVED_FORMAT_CHARACTERS = {"\ufeff", "\u200b", "\u2060"}


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

    text, line_mapping = _clean_text(document.text)
    headings = metadata.get("headings")
    if isinstance(headings, list):
        for heading in headings:
            if not isinstance(heading, dict):
                continue
            source_line = heading.get("line_number")
            if isinstance(source_line, int) and source_line in line_mapping:
                heading["line_number"] = line_mapping[source_line]
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


def _keep_character(character: str) -> bool:
    if character == "\t":
        return True
    codepoint = ord(character)
    if codepoint < 32 or 127 <= codepoint <= 159:
        return False
    return character not in _REMOVED_FORMAT_CHARACTERS
