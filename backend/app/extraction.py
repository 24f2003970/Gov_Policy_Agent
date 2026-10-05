"""Provisional character chunks from exact page text, with half-open Unicode offsets."""
import re

PROFILE = "unicode-char-v1:1200:120"
REVISION = "pymupdf-1.28.2-text-v1"


def paragraphs(text):
    # Blank lines delimit TXT paragraphs; PDF line blocks remain exact, unnormalized.
    return [{"start": match.start(), "end": match.end(),
             "section_label": label(match.group())} for match in re.finditer(r"[^\n]+(?:\n(?!\n)[^\n]+)*", text)]


def label(text):
    first = text.splitlines()[0].strip()
    if len(first) > 200:
        return None
    if re.match(r"^(?:Section|Clause|CHAPTER)\s+[A-Za-z0-9().-]+\b", first):
        return first
    if re.match(r"^\d+(?:\.\d+)*[.)]?\s+\S", first):
        return first
    return None  # No guessed headings/clauses.


def chunks(text):
    spans = paragraphs(text)
    start = 0
    while start < len(text):
        end = min(start + 1200, len(text))
        if end < len(text):
            boundary = text.rfind("\n", start + 600, end)
            if boundary >= 0:
                end = boundary + 1
        containing = next((p for p in spans if p["start"] <= start < p["end"]), None)
        yield {"start_offset": start, "end_offset": end, "text": text[start:end],
               "section_label": containing["section_label"] if containing else None,
               "continued_clause": bool(containing and start > containing["start"]), "profile": PROFILE}
        if end == len(text):
            break
        start = end - 120
