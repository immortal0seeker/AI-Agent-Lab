from pathlib import Path
from uuid import UUID

from .base import DocumentParseError, ParsedDocument

_UTF8_BOM = b"\xef\xbb\xbf"
_UTF16_LE_BOM = b"\xff\xfe"
_UTF16_BE_BOM = b"\xfe\xff"
_UTF32_BOMS = (b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff")


def parse_txt(path: Path, *, document_id: UUID) -> ParsedDocument:
    try:
        content = Path(path).read_bytes()
        if content.startswith(_UTF32_BOMS):
            raise DocumentParseError()
        if content.startswith(_UTF8_BOM):
            encoding = "utf-8-sig"
            text = content.decode(encoding, errors="strict")
        elif content.startswith(_UTF16_LE_BOM):
            encoding = "utf-16-le"
            text = content[len(_UTF16_LE_BOM) :].decode(
                encoding,
                errors="strict",
            )
        elif content.startswith(_UTF16_BE_BOM):
            encoding = "utf-16-be"
            text = content[len(_UTF16_BE_BOM) :].decode(
                encoding,
                errors="strict",
            )
        else:
            encoding = "utf-8"
            text = content.decode(encoding, errors="strict")
    except (OSError, UnicodeError) as exc:
        raise DocumentParseError() from exc

    return ParsedDocument(
        document_id=document_id,
        text=text,
        metadata={
            "format": "txt",
            "encoding": encoding,
        },
    )
