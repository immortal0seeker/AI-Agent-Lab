from bisect import bisect_right
from collections.abc import Iterator
from dataclasses import dataclass
from math import ceil

from app.rag.parsers import ParsedDocument
from app.rag.processing_limits import (
    DEFAULT_DOCUMENT_PROCESSING_LIMITS,
    DocumentProcessingLimitError,
    DocumentProcessingLimits,
)


class DocumentContentEmptyError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Document contains no usable text.")


@dataclass(frozen=True)
class DocumentChunkDraft:
    chunk_index: int
    content: str
    token_count: int
    char_count: int
    heading: str | None
    page_number: int | None
    metadata: dict[str, object]


@dataclass(frozen=True)
class _HeadingMarker:
    offset: int
    text: str
    level: int


def chunk_document(
    document: ParsedDocument,
    *,
    chunk_size: int,
    chunk_overlap: int,
    limits: DocumentProcessingLimits = DEFAULT_DOCUMENT_PROCESSING_LIMITS,
) -> tuple[DocumentChunkDraft, ...]:
    _validate_window(chunk_size, chunk_overlap)
    source_format = document.metadata.get("format")
    format_name = source_format if isinstance(source_format, str) else "unknown"
    drafts: list[DocumentChunkDraft] = []

    if document.pages is not None:
        if not any(page.text.strip() for page in document.pages):
            raise DocumentContentEmptyError()
        for page in document.pages:
            if not page.text.strip():
                continue
            for start, end in _chunk_ranges(
                page.text,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            ):
                if len(drafts) >= limits.max_chunks:
                    raise DocumentProcessingLimitError()
                drafts.append(
                    _build_draft(
                        chunk_index=len(drafts),
                        content=page.text[start:end],
                        source_format=format_name,
                        start=start,
                        end=end,
                        heading=None,
                        page_number=page.page_number,
                    )
                )
        return tuple(drafts)

    if not document.text.strip():
        raise DocumentContentEmptyError()
    headings = _heading_markers(document)
    heading_offsets = [heading.offset for heading in headings]
    for start, end in _chunk_ranges(
        document.text,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    ):
        heading = _heading_at_start(
            headings,
            heading_offsets=heading_offsets,
            start=start,
        )
        if len(drafts) >= limits.max_chunks:
            raise DocumentProcessingLimitError()
        drafts.append(
            _build_draft(
                chunk_index=len(drafts),
                content=document.text[start:end],
                source_format=format_name,
                start=start,
                end=end,
                heading=heading,
                page_number=None,
            )
        )
    return tuple(drafts)


def _validate_window(chunk_size: int, chunk_overlap: int) -> None:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be non-negative")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")


def _chunk_ranges(
    text: str,
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> Iterator[tuple[int, int]]:
    start = 0
    while start < len(text):
        hard_end = min(start + chunk_size, len(text))
        end = hard_end
        if hard_end < len(text):
            minimum_boundary = start + max(1, (hard_end - start) // 2)
            paragraph = text.rfind("\n\n", minimum_boundary, hard_end)
            if paragraph >= 0:
                end = paragraph + 2
            else:
                newline = text.rfind("\n", minimum_boundary, hard_end)
                if newline >= 0:
                    end = newline + 1
        if end <= start:
            end = hard_end
        yield start, end
        if end >= len(text):
            break
        next_start = end - chunk_overlap
        start = max(start + 1, next_start)


def _heading_markers(document: ParsedDocument) -> tuple[_HeadingMarker, ...]:
    headings = document.metadata.get("headings")
    if not isinstance(headings, list):
        return ()
    line_offsets = [0]
    line_offsets.extend(
        index + 1
        for index, character in enumerate(document.text)
        if character == "\n"
    )
    markers: list[_HeadingMarker] = []
    for heading in headings:
        if not isinstance(heading, dict):
            continue
        line_number = heading.get("line_number")
        text = heading.get("text")
        level = heading.get("level")
        if (
            not isinstance(line_number, int)
            or not isinstance(text, str)
            or not isinstance(level, int)
            or line_number <= 0
            or line_number > len(line_offsets)
        ):
            continue
        markers.append(
            _HeadingMarker(
                offset=line_offsets[line_number - 1],
                text=text,
                level=level,
            )
        )
    return tuple(sorted(markers, key=lambda marker: marker.offset))


def _heading_at_start(
    headings: tuple[_HeadingMarker, ...],
    *,
    heading_offsets: list[int],
    start: int,
) -> _HeadingMarker | None:
    index = bisect_right(heading_offsets, start) - 1
    if index < 0:
        return None
    return headings[index]


def _build_draft(
    *,
    chunk_index: int,
    content: str,
    source_format: str,
    start: int,
    end: int,
    heading: _HeadingMarker | None,
    page_number: int | None,
) -> DocumentChunkDraft:
    metadata: dict[str, object] = {
        "source_format": source_format,
        "start_char": start,
        "end_char": end,
    }
    if heading is not None:
        metadata["heading_level"] = heading.level
    return DocumentChunkDraft(
        chunk_index=chunk_index,
        content=content,
        token_count=max(1, ceil(len(content.encode("utf-8")) / 4)),
        char_count=len(content),
        heading=None if heading is None else heading.text[:512],
        page_number=page_number,
        metadata=metadata,
    )
