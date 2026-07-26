def _pdf_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_pdf(page_texts: list[str | None]) -> bytes:
    page_object_numbers = [
        4 + page_index * 2 for page_index in range(len(page_texts))
    ]
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        (
            "<< /Type /Pages /Count "
            f"{len(page_texts)} /Kids "
            f"[{' '.join(f'{number} 0 R' for number in page_object_numbers)}]"
            " >>"
        ).encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for page_index, page_text in enumerate(page_texts):
        page_number = page_object_numbers[page_index]
        content_number = page_number + 1
        objects.append(
            (
                "<< /Type /Page /Parent 2 0 R "
                "/MediaBox [0 0 612 792] "
                "/Resources << /Font << /F1 3 0 R >> >> "
                f"/Contents {content_number} 0 R >>"
            ).encode()
        )
        if page_text is None:
            stream = b"q Q"
        else:
            stream = (
                "BT /F1 12 Tf 72 720 Td "
                f"({_pdf_string(page_text)}) Tj ET"
            ).encode()
        objects.append(
            b"<< /Length "
            + str(len(stream)).encode()
            + b" >>\nstream\n"
            + stream
            + b"\nendstream"
        )

    document = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_number, body in enumerate(objects, start=1):
        offsets.append(len(document))
        document.extend(f"{object_number} 0 obj\n".encode())
        document.extend(body)
        document.extend(b"\nendobj\n")

    xref_offset = len(document)
    document.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    document.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        document.extend(f"{offset:010d} 00000 n \n".encode())
    document.extend(
        (
            "trailer\n"
            f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            "startxref\n"
            f"{xref_offset}\n"
            "%%EOF\n"
        ).encode()
    )
    return bytes(document)
