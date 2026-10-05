"""Untrusted parsing in a killable child. No DB credentials or document text in stdout."""
import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from app.extraction import paragraphs, REVISION


def write_json(path, value):
    temporary = Path(str(path) + ".part")
    temporary.write_text(json.dumps(value, ensure_ascii=True), encoding="utf-8")
    os.replace(temporary, path)


def parse(path, format, max_pages, max_chars, progress=None, validate=False):
    import pymupdf
    pages = []
    total_chars = 0
    if format == "pdf":
        if path.open("rb").read(5) != b"%PDF-":
            raise ValueError("invalid_pdf")
        with pymupdf.open(path) as document:
            if not document.is_pdf or document.is_encrypted or document.needs_pass or document.is_repaired:
                raise ValueError("encrypted_or_malformed_pdf")
            if not 1 <= len(document) <= max_pages:
                raise ValueError("page_limit")
            total = len(document)
            if validate:
                return {"total_pages": total}
            for ordinal, page in enumerate(document, 1):
                text = page.get_text("text", sort=False)
                if "\x00" in text:
                    raise ValueError("invalid_text")
                total_chars += len(text)
                if total_chars > max_chars:
                    raise ValueError("text_limit")
                flags = ["layout_tables_not_guaranteed"]
                if '\ufffd' in text:
                    flags.append('encoding_artifacts_review')
                if len(text.strip()) < 30:
                    flags.append("needs_ocr")
                pages.append({"ordinal": ordinal, "pdf_page_number": ordinal, "source_start": 0,
                              "text": text, "paragraphs": paragraphs(text), "quality_flags": flags,
                              "method": REVISION})
                if progress:
                    write_json(progress, {"processed": ordinal, "total": total})
    else:
        data = path.read_bytes()
        if data.startswith(b"%PDF-"):
            raise ValueError("misleading_extension")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("invalid_utf8") from None
        if any(ord(c) < 32 and c not in "\n\r\t\f" for c in text):
            raise ValueError("invalid_text")
        if not text.strip() or len(text) > max_chars:
            raise ValueError("empty_or_text_limit")
        if validate:
            return {"total_pages": 1}
        # One TXT source section; absolute character spans, never fake PDF page numbers.
        pages = [{"ordinal": 1, "pdf_page_number": None, "source_start": 0, "text": text,
                  "paragraphs": paragraphs(text), "quality_flags": [], "method": "utf8-exact-v1"}]
        if progress:
            write_json(progress, {"processed": 1, "total": 1})
    return {"pages": pages}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("format", choices=["pdf", "txt"])
    parser.add_argument("output", type=Path)
    parser.add_argument("--progress", type=Path)
    parser.add_argument("--max-pages", type=int, default=500)
    parser.add_argument("--max-chars", type=int, default=2_000_000)
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--render-page", type=int)
    args = parser.parse_args()
    try:
        if args.render_page:
            import pymupdf
            with pymupdf.open(args.path) as document:
                if not document.is_pdf or document.is_encrypted or not 1 <= args.render_page <= len(document) <= args.max_pages:
                    raise ValueError("invalid_pdf")
                page = document[args.render_page - 1]
                if page.rect.width <= 0 or page.rect.height <= 0:
                    raise ValueError("invalid_pdf")
                scale = min(1200 / page.rect.width, 1600 / page.rect.height, 2)
                page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False).save(args.output)
            raise SystemExit(0)
        result = parse(args.path, args.format, args.max_pages, args.max_chars, args.progress, args.validate)
    except Exception as error:
        allowed = {"invalid_pdf", "encrypted_or_malformed_pdf", "page_limit", "text_limit", "invalid_text",
                   "misleading_extension", "invalid_utf8", "empty_or_text_limit"}
        code = str(error) if isinstance(error, ValueError) and str(error) in allowed else "parser_failed"
        result = {"error": code}
    write_json(args.output, result)
