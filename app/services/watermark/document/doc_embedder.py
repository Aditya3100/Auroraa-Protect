# app/services/watermark/document/doc_embedder.py

import fitz
from docx import Document
from docx.shared import Pt


Z0 = "\u200B"
Z1 = "\u200C"

REPEAT = 6
MAGIC = "WM1|"


# -------------------------
# Helpers
# -------------------------

def _frame(payload):
    return f"{MAGIC}{len(payload)}|{payload}"


def _to_bits(text):

    bits = []

    for b in text.encode():
        for i in range(8):
            bits.append((b >> (7-i)) & 1)

    return bits


def _expand(bits):

    out = []

    for b in bits:
        out += [b] * REPEAT

    return out


def _inject_unicode(text, bits):

    out = []
    i = 0

    for ch in text:

        out.append(ch)

        if ch.isalnum() and i < len(bits):

            out.append(Z1 if bits[i] else Z0)
            i += 1

    return "".join(out)


# -------------------------
# PDF
# -------------------------

def embed_pdf(infile, outfile, payload, seed=None):

    framed = _frame(payload)
    bits = _expand(_to_bits(framed))

    doc = fitz.open(infile)

    for page in doc:

        text = page.get_text("text")

        if not text.strip():
            continue

        # Unicode layer
        marked = _inject_unicode(text, bits)

        # Layout layer
        y_shift = 0.8 if bits[0] else -0.8

        page.insert_textbox(
            page.rect,
            marked,
            fontsize=11,
            lineheight=11 + y_shift
        )

    doc.save(outfile)


# -------------------------
# DOCX
# -------------------------

def embed_docx(infile, outfile, payload, seed=None):

    framed = _frame(payload)
    bits = _expand(_to_bits(framed))

    doc = Document(infile)

    i = 0

    for p in doc.paragraphs:

        if not p.text.strip():
            continue

        # Unicode
        p.text = _inject_unicode(p.text, bits)

        # Layout
        if i < len(bits):
            p.paragraph_format.line_spacing = 1.1 if bits[i] else 1.0
            i += 1

    doc.save(outfile)
